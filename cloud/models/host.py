import commands
import libvirt
import logging
import socket
import urllib
import json
from subprocess import Popen, PIPE
from django.db import models
from django.core.cache import cache
from django.conf import settings
from libvirt import libvirtError
from xml.etree.ElementTree import fromstring
from cloud.models.virtual_machine import VirtualMachine, LIBVIRT_VM_STATES
from cloud.models.virtual_interface import VirtualInterface
from cloud.models.device import Device

# Get an instance of a logger
logger = logging.getLogger(__name__)

DRIVERS = (
        (u'remote', u'Default (remote)'),
        (u'qemu', u'QEMU/KVM'),
        (u'lxc', u'LXC'),
        (u'xen', u'XEN'),
        (u'vbox', u'VirtualBox'),
        (u'vmware', u'VMWare'),
)

TRANSPORTS = (
        (u'tls', u'SSL/TLS'),
        (u'ssh', u'SSH'),
        (u'unix', u'Unix'),
        (u'ext', u'External'),
        (u'tcp', u'TCP (Unencrypted)'),
        (u'local', u'Local Connection'),
)

ARCHITECTURES = (
        (u'x86', u'x86'),
        (u'x86_64', u'x86_64'),
)


class Host(Device):
    # libvirt connections (class attribute)
    libvirt_connections = {}

    # libvirt connection URI
    # drv[+transport]://[username@][hostname][:port]/[path][?extraparameters]
    driver = models.CharField(
        max_length=10,
        choices=DRIVERS,
        default='qemu',
        db_index=True
    )
    transport = models.CharField(
        max_length=10,
        choices=TRANSPORTS,
        default='tls',
        db_index=True
    )
    username = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=100, blank=True, null=True)
    hostname = models.CharField(max_length=200, default='localhost')
    port = models.PositiveIntegerField(blank=True, null=True)
    path = models.CharField(max_length=200, blank=True, null=True)
    extraparameters = models.CharField(max_length=200, blank=True, null=True)

    # Open vSwitch connection parameter
    ovsdb = models.CharField(max_length=200, default='unix:/var/run/openvswitch/db.sock')

    # Helpers for SASL authentication (adapted from virtinst)
    def _password_cb(self, creds):
        retindex = 4
    
        for cred in creds:
            credtype, prompt, ignore, ignore, ignore = cred
            prompt += ": "
    
            res = cred[retindex]
            if credtype == libvirt.VIR_CRED_AUTHNAME:
                res = self.username
            elif credtype == libvirt.VIR_CRED_PASSPHRASE:
                res = self.password
            else:
                raise self.HostException("Unknown auth type in creds callback: %d" % credtype)
    
            cred[retindex] = res

        return 0

    def _auth_cb(self, creds, (passwordcb, passwordcreds)):
        for cred in creds:
            if cred[0] not in passwordcreds:
                raise self.HostException("Unknown cred type '%s', expected only "
                                         "%s" % (cred[0], passwordcreds))
        return passwordcb(creds)

    def open_auth(self, uri):
        auth_options = [libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE]

        conn = libvirt.openAuth(uri, [auth_options, self._auth_cb, (self._password_cb, auth_options)], 0)

        return conn

    def libvirt_connect(self, force_tcp=False):
        # Allows only one connection for each different host
        if force_tcp is False and self.__class__.libvirt_connections.has_key(self.id) and isinstance(self.__class__.libvirt_connections[self.id], libvirt.virConnect):
            #logger.debug("Connections found: " + str(self.__class__.libvirt_connections))
            return self.__class__.libvirt_connections[self.id]

        driver = self.driver
        path = ""
        if self.transport == "local":
            transport = ""
            path = "/system"
            hostname = username = port = ""

        else:
            if self.transport == 'tls' and force_tcp:
                transport = "+tcp"
            else:
                transport = "+" + self.transport

            # Hostname, username and port are only required if
            # connection is NOT local
            if self.hostname == "":
                hostname = ""
            else:
                hostname = self.hostname

            if self.port == None:
                port = ""
            else:
                port = ":" + str(self.port)

        if not self.path.startswith("/"):
            if self.path == "":
                path = ""
            else:
                path = "/" + str(self.path)

        if self.extraparameters == "":
            extraparameters = ""
        else:
            extraparameters = "?" + str(self.extraparameters)

        # Format: driver[+transport]://[username@][hostname][:port]/[path][?extraparameters]
        host_path = driver + transport + "://" + hostname + port + path + extraparameters

        try:
            if force_tcp:
                return libvirt.open(host_path)

            # If SASL authentication is needed
            if self.username and self.password:
                self.__class__.libvirt_connections[self.id] = self.open_auth(host_path)
            else:
                self.__class__.libvirt_connections[self.id] = libvirt.open(host_path)
            #logger.debug("New connection: " + str(self.__class__.libvirt_connections))
            return self.__class__.libvirt_connections[self.id]
        except libvirtError as e:
            logger.error('Failed to open connection to the hypervisor: ' + host_path + ' ' + str(e))
            raise self.HostException('Failed to open connection to the hypervisor: ' + host_path + ' ' + str(e))

    def current_state(self):
        try:
            self.libvirt_connect()
            return "Active"
        except:
            return "Off-line"

    # Reads current libvirt status and updates local database
    def sync(self):
        lv_conn = self.libvirt_connect()

        # Gather all domains
        all_domains = []

        try:
            def_domains = lv_conn.listDefinedDomains()
            active_domains = lv_conn.listDomainsID()
        except libvirtError as e:
            raise self.HostException('Failed to read domains from hypervisor: ' + str(lv_conn) + ' ' + str(e))

        for dom_id in active_domains:
            # Get domain info from libvirt
            try:
                dom = lv_conn.lookupByID(dom_id)
                all_domains.append({
                    "name": dom.name(),
                    "info": dom.info()
                })
            except libvirtError as e:
                raise self.HostException('Failed to read domains from hypervisor: ' + str(lv_conn) + ' ' + str(e))

        for dom_name in def_domains:
            # Get domain info from libvirt
            try:
                dom = lv_conn.lookupByName(dom_name)
                all_domains.append({
                    "name": dom_name,
                    "info": dom.info()
                })
            except libvirtError as e:
                raise self.HostException('Failed to read domain info from hypervisor: ' + str(lv_conn) + ' ' + str(e))

        for dom in all_domains:
            # Try to find the defined VM in the local database
            vms = self.virtualmachine_set.filter(name=dom["name"])
            if len(vms) == 0:
                # Not found, create new
                logger.debug("VM " + str(dom) + " not found in database, creating new one")
                vm = VirtualMachine()
                vm.name = dom["name"]
                vm.memory = dom["info"][2]
                vm.vcpu = dom["info"][3]
                vm.host = self
                vm.save()

                # TODO: Fill in the disk_path of VM

                # Create also interfaces
                vm_element = fromstring(vm.get_xml_desc())
                if_elements = vm_element.findall("devices/interface")
                i = 0
                for if_element in if_elements:
                    interface = VirtualInterface()
                    interface.if_type = None

                    if 'type' in if_element.attrib:
                        interface.if_type = if_element.attrib["type"]

                    # There should be at least a type defined
                    if interface.if_type is None:
                        logger.warning("Could not create interface from element " + str(vars(if_element)))
                        break

                    mac_element = if_element.find("mac")
                    if mac_element is not None:
                        interface.mac_address = mac_element.attrib["address"]

                    alias_element = if_element.find("alias")
                    if alias_element is not None:
                        interface.alias = alias_element.attrib["name"]
                    else:
                        interface.alias = "net" + str(i)

                    # Attach interface to VM
                    interface.attached_to = vm

                    # Optional parameters
                    source_element = if_element.find("source")
                    if source_element is not None:
                        interface.source = source_element.attrib

                    target_element = if_element.find("target")
                    if target_element is not None:
                        interface.target = target_element.attrib

                    interface.save()

                    i += 1

                # TODO: Create disks also (when disk objects are available)

            else:
                #Take the first VM from the list
                vm = vms[0]
                # Update info anyway
                vm.memory = dom["info"][2]
                vm.vcpu = dom["info"][3]
                vm.save()
                # TODO: Update interface and disk information

            # More than one VM with the same name
            if len(vms) > 1:
                logger.warning("More than one VM named " + str(dom["name"]) + " for host " + str(self.id))


        # Deleted non existing vms (temporarily disabled)
        #vms = self.virtualmachine_set.all()
        #for vm in vms:
        #    found = False
        #    for dom in all_domains:
        #        if dom["name"] == vm.name:
        #            found = True
        #            break;
        #    if not found:
        #        vm.delete()

    # Reads memory usage information from libvirt and returns the following structure
    # {'cached': 999L, 'total': 999L, 'buffers': 999L, 'free': 999L}
    def get_memory_stats(self):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return False

        stats = lv_conn.getMemoryStats(libvirt.VIR_NODE_MEMORY_STATS_ALL_CELLS, 0)
        return stats

    # Reads CPU usage information from libvirt and returns the following structure
    # {'kernel': 999L, 'idle': 999L, 'user': 999L, 'iowait': 999L}
    def get_cpu_stats(self):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return False

        return lv_conn.getCPUStats(libvirt.VIR_NODE_CPU_STATS_ALL_CPUS, 0)

    def get_libvirt_version(self):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return False

        daemon_version = lv_conn.getLibVersion()

        major = daemon_version / 1000000;
        daemon_version %= 1000000;
        minor = daemon_version / 1000;
        rel = daemon_version % 1000;

        return str(major) + '.' + str(minor) + '.' + str(rel)

    def get_hypervisor_version(self):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return False

        try:
            hv_version = lv_conn.getVersion()
            major = hv_version / 1000000;
            hv_version %= 1000000;
            minor = hv_version / 1000;
            rel = hv_version % 1000;
            return str(major) + '.' + str(minor) + '.' + str(rel)
        except libvirtError as e:
            logger.warning('Failed to get hypervisor version: ' + str(self) + ' ' + str(e))
            return 'Failed to get hypervisor version'

    # Returns hypervisor type (QEMU, XEN, etc.)
    def get_hypervisor_type(self):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return False

        return lv_conn.getType()

    # System info
    # Output:
    # - bios: bios information (vendor, version, date, release)
    # - system: hardware information (manufacturer, product, version, serial, uuid, sku, family)
    # - architecture: string indicating the CPU model
    # - memory: memory size in kilobytes
    # - cpus: the number of active CPUs
    # - mhz: expected CPU frequency
    # - nodes: the number of NUMA cell, 1 for unusual NUMA topologies or uniform memory access; check capabilities XML for the actual NUMA topology
    # - sockets: number of CPU sockets per node if nodes > 1, total number of CPU sockets otherwise
    # - cores: number of cores per socket
    # - threads: number of threads per core
    # - libvirt_version: version of daemon running in the connection
    # - hypervisor_version: version and type of hypervisor running in the connection
    def get_info(self):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return False

        sysinfo_element = fromstring(self.get_xml_info())
        bios_element = sysinfo_element.find("bios")
        bios_info = {}
        if bios_element != None:
            entries = bios_element.findall("entry")
            for entry in entries:
                if entry.attrib.has_key("name"):
                    bios_info[entry.attrib["name"]] = entry.text

        sys_element = sysinfo_element.find("system")
        sys_info = {}
        if sys_element != None:
            entries = sys_element.findall("entry")
            for entry in entries:
                if entry.attrib.has_key("name"):
                    sys_info[entry.attrib["name"]] = entry.text

        info = lv_conn.getInfo()
        return {
            'bios': bios_info,
            'system': sys_info,
            'architecture': info[0],
            'memory': info[1] / 16, # Ajust to make resource allocation work on virtualized datacenter
            'cpus': info[2] / 16, # Ajust to make resource allocation work on virtualized datacenter
            'mhz': info[3],
            'nodes': info[4],
            'sockets': info[5],
            'cores': info[6],
            'threads': info[7],
            'libvirt_version': self.get_libvirt_version(),
            'hypervisor_version': self.get_hypervisor_type() + ": " + self.get_hypervisor_version()
        }

    # CPU specific information
    # Output is list of processors with the following characteristics:
    # - socket_destination, type, family, manufacturer, signature, version,
    #   external_clock, max_speed, status
    def get_cpu_info(self):
        xml_info = self.get_xml_info()
        if not xml_info:
            return False

        sysinfo_element = fromstring(xml_info)

        processors = sysinfo_element.findall("processor")

        procs = []
        for proc in processors:
            entries = proc.findall("entry")
            info = {}
            for entry in entries:
                if 'name' in entry.attrib:
                    info[entry.attrib["name"]] = entry.text

            procs.append(info)

        return procs

    # Memory specific information
    # Output is list of memory banks with the following characteristics:
    # - size, form_factor, locator, bank_locator, type, type_detail, speed,
    #   manufacturer, serial_number
    def get_memory_info(self):
        xml_info = self.get_xml_info()
        if not xml_info:
            return False

        sysinfo_element = fromstring(xml_info)
        memories = sysinfo_element.findall("memory_device")

        mems = []
        for mem in memories:
            entries = mem.findall("entry")
            info = {}
            for entry in entries:
                if 'name' in entry.attrib:
                    info[entry.attrib["name"]] = entry.text

            mems.append(info)

        return mems

    # CPU allocation information
    # Will return not the real usage, but the number of cpus
    # allocated for virtual machines
    def get_cpu_allocation(self):
        vms = VirtualMachine.objects.filter(host=self)
        stats = {
            'total': 0,
            'active': 0
        }
        for vm in vms:
            stats['total'] += vm.vcpu
            stats['active'] += vm.vcpu
            #TODO: Count active vcpu from active domains (it is raising a warning)
            #vm_state = vm.current_state()
            #if vm_state == 'running':
            #    stats['active'] += vm.vcpu

        return stats

    # Memory allocation information
    # Will return not the real usage, but the sum of all memory
    # allocated for virtual machines
    def get_memory_allocation(self):
        vms = VirtualMachine.objects.filter(host=self)
        stats = {
            'total': 0,
            'active': 0
        }
        for vm in vms:
            stats['total'] += vm.memory
            stats['active'] += vm.memory
            #TODO: Count active memory from active domains
            #vm_state = vm.current_state()
            #if vm_state == 'running':
            #    stats['active'] += vm.memory

        return stats

    # Detailed system description (XML)
    def get_xml_info(self, force=False):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return False

        # Cache XMLDesc for one day (use force to read it through)
        XMLDesc = cache.get('Host' + str(self.id) + '-XMLDesc')
        if XMLDesc is None or force:
            XMLDesc = lv_conn.getSysinfo(0)
            cache.set('Host' + str(self.id) + '-XMLDesc', XMLDesc, 86400)
        return XMLDesc

    # Total number of active VMs
    def get_num_of_active_vms(self):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return 0

        return lv_conn.numOfDomains()

    # Total number of inactive VMs
    def get_num_of_inactive_vms(self):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return 0

        return lv_conn.numOfDefinedDomains()

    # Total number of VMs (active or inactive)
    def get_num_of_vms(self):
        in_vms = self.get_num_of_inactive_vms()
        ac_vms = self.get_num_of_active_vms()

        return in_vms + ac_vms

    # Returns a list of states and number of VMs currently in each of them
    def get_state_of_vms(self):
        try:
            lv_conn = self.libvirt_connect()
        except:
            return False

        # All possible states
        all_states = {}
        for state in LIBVIRT_VM_STATES:
            all_states[LIBVIRT_VM_STATES[state]] = 0

        def_domains = lv_conn.listDefinedDomains()
        active_domains = lv_conn.listDomainsID()

        for dom_id in active_domains:
            # Get domain info from libvirt
            dom = lv_conn.lookupByID(dom_id)
            info = dom.info()
            if LIBVIRT_VM_STATES.has_key(info[0]):
                state = LIBVIRT_VM_STATES[info[0]]
            else:
                state = "unknown"

            if not all_states.has_key(state):
                all_states[state] = 0

            all_states[state] += 1

        for dom_name in def_domains:
            # Get domain info from libvirt
            dom = lv_conn.lookupByName(dom_name)
            info = dom.info()
            if LIBVIRT_VM_STATES.has_key(info[0]):
                state = LIBVIRT_VM_STATES[info[0]]
            else:
                state = "unknown"

            if not all_states.has_key(state):
                all_states[state] = 0

            all_states[state] += 1

        return all_states

    def get_uri(self):
        try:
            lv_conn = self.libvirt_connect()
            return lv_conn.getURI()
        except:
            return ""

    def ssh_status(self):
        if not hasattr(self, '_ssh_status') or self.ssh_status is None:
            self._ssh_status = self.check_ssh_status()
        return self._ssh_status

    def check_ssh_status(self):
        out = commands.getstatusoutput('ssh -o StrictHostKeyChecking=no root@' + self.hostname + ' "/sbin/ifconfig"')
        if out[0] != 0:
            message = "Host is not accepting ssh connections (see logs for details). Please install ssh key with 'ssh-copy-id -i /var/www/.ssh/id_rsa.pub root@" + self.hostname + "'"
            logger.warning(message + ": " + out[1])
        else:
            message = "OK"

        return message

    def openvswitch_status(self):
        if not hasattr(self, '_openvswitch_status'):
            self._openvswitch_status = self.check_openvswitch_status()
        return self._openvswitch_status

    def check_openvswitch_status(self):
        bridge = self.get_openvswitch_bridge()
        dpid = 'a0b0b4' + str(self.id).zfill(10)
        ctrl = settings.SDN_CONTROLLER
        out = commands.getstatusoutput('ovs-vsctl --db=' + self.ovsdb + ' --timeout=3 br-exists "' + bridge + '"')
        if out[0] != 0:
            logger.warning('Open vSwitch bridge not found (' + bridge + ') at ' + self.ovsdb + ', will try to create one. ' + out[1])
            # Will try to create a bridge
            out = commands.getstatusoutput('ovs-vsctl --db=' + self.ovsdb + ' ' +
                                           '--timeout=3 add-br "' + bridge + '" ' +
                                           '-- set Bridge "' + bridge + '" ' +
                                           'other_config:datapath-id=' + dpid)
            if out[0] != 0:
                return 'Could not find bridge (' + bridge + ') at ' + self.ovsdb + ': ' + out[1]
            # Setup controller
            out = commands.getstatusoutput('ovs-vsctl --db=' + self.ovsdb + ' --timeout=3 set-controller ' + bridge + ' ' + ctrl['transport'] + ':' + ctrl['ip'] + ':' + str(ctrl['port']))
            if out[0] != 0:
                return 'Could not set controller ' + ctrl['transport'] + ':' + ctrl['ip'] + ':' + ctrl['port'] + ' (' + bridge + ') at ' + self.ovsdb + ': ' + out[1]

        return 'OK'

    def add_openvswitch_port(self, port):
        bridge = self.get_openvswitch_bridge()

        # Add interface to the default bridge
        cmd = ['ovs-vsctl', '--db=' + self.ovsdb, '--timeout=3', '--', '--may-exist', 'add-port', bridge, port]
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        p_out = p.communicate()
        if p.returncode != 0:
            raise self.HostException('Could not add port (' + port + ') to bridge (' + bridge + '): ' + p_out[1])

    def del_openvswitch_port(self, port):
        bridge = self.get_openvswitch_bridge()

        # Add interface to the default bridge
        cmd = ['ovs-vsctl', '--db=' + self.ovsdb, '--timeout=3', '--', '--if-exists', 'del-port', bridge, port]
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        p_out = p.communicate()
        if p.returncode != 0:
            raise self.HostException('Could not delete port (' + port + ') to bridge (' + bridge + '): ' + p_out[1])

    def get_openvswitch_bridge(self):
        return 'hostbr' + str(self.id)

    def __unicode__(self):
        return self.get_driver_display() + u" at " + self.hostname

    # Returns the path in the network to another host
    # Currently use the controller (Floodlight 0.90) to do so
    def path_to(self, host):
        src_dpid = 'a0b0b4' + str(self.id).zfill(10)
        dst_dpid = 'a0b0b4' + str(host.id).zfill(10)
        # Use different ports in case source and destination hosts are the same
        url = "http://%s:8080/wm/topology/route/%s/1/%s/2/json" % (settings.SDN_CONTROLLER['ip'], src_dpid, dst_dpid)
        try:
            # Fetch path
            route_response = urllib.urlopen(url)
            if route_response.code == 200: # Success
                route_data = json.loads(route_response.read())
                return route_data
            else:
                logger.warning('Could not find route between %s -> %s (Code: %d)' % (src_dpid, dst_dpid, route_response.code))
        except IOError as e:
            logger.warning('Could not connect to the controller: %s' % str(e))

        return None

    class HostException(Device.DeviceException):
        pass


import commands
import os
import libvirt
import logging
import shutil
import time
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring, tostring
from libvirt import libvirtError, VIR_DOMAIN_AFFECT_CURRENT
from django.db import models
from django.core.cache import cache
from django.template.loader import render_to_string
from xml.etree.ElementTree import fromstring
from cloud.models.image import Image
from cloud.models.virtual_device import VirtualDevice

# Get an instance of a logger
logger = logging.getLogger(__name__)

LIBVIRT_VM_STATES = {
    libvirt.VIR_DOMAIN_NOSTATE: 'no state',
    libvirt.VIR_DOMAIN_RUNNING: 'running',
    libvirt.VIR_DOMAIN_BLOCKED: 'blocked on resource',
    libvirt.VIR_DOMAIN_PAUSED: 'paused by user',
    libvirt.VIR_DOMAIN_SHUTDOWN: 'being shut down',
    libvirt.VIR_DOMAIN_SHUTOFF: 'shut off',
    libvirt.VIR_DOMAIN_CRASHED: 'crashed',
}

DRIVERS = (
        (u'remote', u'Default (remote)'),
        (u'qemu', u'QEMU/KVM'),
        (u'xen', u'XEN'),
        (u'vbox', u'VirtualBox'),
        (u'vmware', u'VMWare'),
)


class VirtualMachine(VirtualDevice):
    # libvirt domain object
    libvirt_domain = None

    host = models.ForeignKey(
        'Host',
        verbose_name="Connected to",
        blank=True,
        null=True
    )
    image = models.ForeignKey(
        Image,
        verbose_name="Base image",
        blank=True,
        null=True
    )

    driver = models.CharField(
        max_length=10,
        choices=DRIVERS,
        default='remote',
        db_index=True
    )
    memory = models.PositiveIntegerField()
    vcpu = models.PositiveIntegerField()

    feature_acpi = models.BooleanField(default=False)
    feature_apic = models.BooleanField(default=False)
    feature_pae = models.BooleanField(default=False)

    clock = models.CharField(max_length=10)

    disk_path = models.CharField(max_length=200, blank=True, null=True)

    def get_libvirt_info(self):
        # Try to selects the VM
        try:
            libvirt_dom = self.get_libvirt_domain()
        except:
            # If the domain is not available only returns false
            return False

        try:
            # info [state, maxMem, memory, nrVirtCpu, cpuTime]
            lv_info = libvirt_dom.info()
            return lv_info
        except libvirtError as e:
            logger.error('Could not read VM info: %s %s' % (self.name, str(e)))
            return False

    def current_state(self, force=False):

        if self.host is None:
            return "not deployed"

        #TODO: Cache disbled temporarily
        force = True
        # Cache state for one hour (use force to read it through)
        curr_state = cache.get('VM' + str(self.id) + '-State')
        if curr_state is None or force:
            lv_info = self.get_libvirt_info()
            if type(lv_info) == list:
                curr_state = LIBVIRT_VM_STATES.get(lv_info[0])
                cache.set('VM' + str(self.id) + '-State', curr_state, 3600)
                return curr_state
        else:
            return "Could not read state"

    def get_xml_desc(self, force=False):
        # Try to selects the VM
        try:
            libvirt_dom = self.get_libvirt_domain()
        except:
            # If the domain is not available only returns false
            return False

        # Cache XMLDesc in self.XMLDesc (use force to read it through)
        if not hasattr(self, 'XMLDesc') or force:
            self.XMLDesc = libvirt_dom.XMLDesc(0)
        return self.XMLDesc

    # Gets CPU statistics for domain
    def get_cpu_stats(self):
        # Try to selects the VM
        try:
            libvirt_dom = self.get_libvirt_domain()
        except:
            # If the domain is not available only returns false
            return False

        if self.current_state() == "running":
            return libvirt_dom.getCPUStats(True, 0)
        else:
            # VM is not running so no CPU information can be retrieved
            raise self.VirtualMachineException(
                'Could not read CPU stats for VM %s: VM is not running.' %
                self.name
            )

    # Some interface details are available in the XML description of domain
    # Output is list of interfaces with additional libvirt information
    # (e.g., interface.model, interface.source, interface.target,
    # interface.alias)
    def get_interface_info(self):

        if_out = self.virtualinterface_set.all()

        # Get description of interfaces from XML
        xml_desc = self.get_xml_desc()
        if xml_desc is False:
            # VM is not deployed so no interface information on libvirt
            return if_out
        else:
            vm_element = fromstring(xml_desc)

        if_elements = vm_element.findall("devices/interface")

        # Populate additional information
        for interface in if_out:
            found = False
            for if_element in if_elements:
                if_mac = if_model = if_source = if_target = if_alias = None

                mac_element = if_element.find("mac")
                if mac_element is not None:
                    if_mac = mac_element.attrib["address"]

                alias_element = if_element.find("alias")
                if alias_element is not None:
                    if_alias = alias_element.attrib["name"]

                # There should be only one interface matching the MAC
                # address or the alias
                if interface.mac_address == if_mac or interface.alias == if_alias:
                    found = True

                    model_element = if_element.find("model")
                    if model_element is not None:
                        if_model = model_element.attrib["type"]
                    interface.model = if_model

                    source_element = if_element.find("source")
                    if source_element is not None:
                        if_source = source_element.attrib
                    interface.source = if_source

                    target_element = if_element.find("target")
                    if target_element is not None:
                        if_target = target_element.attrib
                    interface.target = if_target

                    break

            if not found:
                interface.target = interface.source = interface.model = None

        return if_out

    def get_disk_info(self):
        # Disk details are only available in the XML description of domain
        # Output format (array of disk.id, disk.type, disk.driver,
        # disk.source, disk.target, disk.alias)

        hd_out = []

        # Get description of interfaces from XML
        xml_desc = self.get_xml_desc()
        if xml_desc is False:
            # VM is not deployed so no interface information on libvirt
            return hd_out
        else:
            vm_element = fromstring(xml_desc)

        disks = vm_element.findall("devices/disk")

        i = 0
        for disk in disks:
            hd_type = hd_driver = hd_source = hd_target = hd_alias = None

            if 'type' in disk.attrib:
                hd_type = disk.attrib["type"]

            driver_element = disk.find("driver")
            if driver_element is not None:
                hd_driver = driver_element.attrib

            source_element = disk.find("source")
            if source_element is not None:
                hd_source = source_element.attrib

            target_element = disk.find("target")
            if target_element is not None:
                hd_target = target_element.attrib

            alias_element = disk.find("alias")
            if alias_element is not None:
                hd_alias = alias_element.attrib["name"]

            hd_out.append({
                "id": i,
                "type": hd_type,
                "driver": hd_driver,
                "source": hd_source,
                "target": hd_target,
                "alias": hd_alias
            })
            i += 1

        return hd_out

    def get_main_interface_device(self):
        if_info = self.get_interface_info()
        if type(if_info) == models.query.QuerySet and len(if_info) > 0:
            if (hasattr(if_info[0], 'target')
                and if_info[0].target is not None
                and 'dev' in if_info[0].target
            ):
                return if_info[0].target['dev']
        return 'vnet0'  # Default is vnet0

    def get_main_disk_device(self):
        disk_info = self.get_disk_info()
        if type(disk_info) == list and len(disk_info) > 0:
            return disk_info[0]['target']['dev']
        return 'hda'  # Default is hda

    def get_main_disk_size(self):
        disk_info = self.get_disk_info()
        if type(disk_info) == list and len(disk_info) > 0:
            main_disk = disk_info[0]
            info = self.libvirt_domain.blockInfo(main_disk['target']['dev'], 0)
            return info[0]
        return 0

    def get_vnc_info(self):
        # VNC access information are only available in the XML description
        # of domain. Output format (dictionary with hostname 'host' and
        # port number 'port')

        # Get video info from XML
        xml_desc = self.get_xml_desc()
        if xml_desc is False:
            # VM is not deployed so no interface information on libvirt
            raise self.VirtualMachineException(
                'Could not get XML info for VM %s' % self.name
            )
        else:
            vm_element = fromstring(xml_desc)

        video = vm_element.find("devices/graphics")

        if video is not None:
            if ('type' in video.attrib
                and video.attrib['type'] == "vnc"
                and 'port' in video.attrib
                and video.attrib["port"] != "-1"
            ):
                return {
                    'host': self.host.hostname,
                    'port': video.attrib["port"]
                }
            else:
                raise self.VirtualMachineException(
                    'Could VNC is not correctly set for %s' % self.name
                )
        else:
            raise self.VirtualMachineException(
                'Could not find graphics element in XML info for VM %s' %
                self.name
            )

    def start(self):
        # Selects the VM
        libvirt_dom = self.get_libvirt_domain()

        try:
            libvirt_dom.create()
        except libvirtError as e:
            logger.error('Could not start VM: %s %s' % (self.name, str(e)))
            raise self.VirtualMachineException(
                'Could not start VM: %s %s' % (self.name, str(e))
            )

        # Clear cached state
        cache.delete('VM' + str(self.id) + '-State')
        return True

    def stop(self):
        # Selects the VM
        libvirt_dom = self.get_libvirt_domain()

        try:
            libvirt_dom.destroy()
        except libvirtError as e:
            logger.error('Could not stop VM: %s %s' % (self.name, str(e)))
            raise self.VirtualMachineException(
                'Could not stop VM: %s %s' % (self.name, str(e))
            )

        # Clear cached state
        cache.delete('VM' + str(self.id) + '-State')
        return True

    def shutdown(self):
        # Selects the VM
        libvirt_dom = self.get_libvirt_domain()

        try:
            libvirt_dom.shutdown()
        except libvirtError as e:
            logger.error('Could not shutdown VM: %s %s' % (self.name, str(e)))
            raise self.VirtualMachineException(
                'Could not shutdown VM: %s %s' % (self.name, str(e))
            )

        # Clear cached state
        cache.delete('VM' + str(self.id) + '-State')
        return True

    def resume(self):
        # Selects the VM
        libvirt_dom = self.get_libvirt_domain()

        try:
            libvirt_dom.resume()
        except libvirtError as e:
            logger.error('Could not resume VM: %s %s' % (self.name, str(e)))
            raise self.VirtualMachineException(
                'Could not resume VM: %s %s' % (self.name, str(e))
            )

        # Clear cached state
        cache.delete('VM' + str(self.id) + '-State')
        return True

    def suspend(self):
        # Selects the VM
        libvirt_dom = self.get_libvirt_domain()

        try:
            libvirt_dom.suspend()
        except libvirtError as e:
            logger.error('Could not suspend VM: %s %s' % (self.name, str(e)))
            raise self.VirtualMachineException(
                'Could not suspend VM: %s %s' % (self.name, str(e))
            )

        # Clear cached state
        cache.delete('VM' + str(self.id) + '-State')
        return True

    # Defines new VM based on an XML description
    def define(self, xml):
        # Connect to libvirt host
        lv_conn = self.get_libvirt_connection()

        # Selects the VM
        libvirt_dom = None
        try:
            libvirt_dom = lv_conn.defineXML(xml)
        except libvirtError as e:
            logger.error('Could not define VM: %s %s' % (self.name, str(e)))
            raise self.VirtualMachineException(
                'Could not define VM: %s %s' % (self.name, str(e))
            )

        # Returns the defined domain
        return libvirt_dom

    def undefine(self):
        # Selects the VM
        libvirt_dom = self.get_libvirt_domain()

        try:
            libvirt_dom.undefine()
        except libvirtError as e:
            logger.error('Could not undefine VM: %s %s' % (self.name, str(e)))
            raise self.VirtualMachineException(
                'Could not undefine VM: %s %s' % (self.name, str(e))
            )

        # Clear cached state
        cache.delete('VM' + str(self.id) + '-State')
        return True

    def migrate(self, dest):
        # Selects the VM
        # Migration is not allowed over TLS connection
        libvirt_dom = self.get_libvirt_domain(force_tcp=True)

        try:
            # Migration is not allowed over TLS connection
            dest_conn = dest.libvirt_connect(force_tcp=True)
        except libvirtError as e:
            logger.error(
                'Could not connect to destination host when migrating VM'
            )
            raise self.VirtualMachineException(str(e))

        # migrate(self, dconn, flags, dname, uri, bandwidth):
        try:
            # Will migrate the virtual machine while in running, persist it
            # in destination host and undefine it in the source
            flags = (libvirt.VIR_MIGRATE_LIVE |
                libvirt.VIR_MIGRATE_PERSIST_DEST |
                libvirt.VIR_MIGRATE_UNDEFINE_SOURCE
            )
            #dest_uri = dest.get_uri()
            dest_uri = "tcp://" + dest.hostname
            libvirt_dom.migrate(dest_conn, flags, self.name, dest_uri, 0)
        except libvirtError as e:
            raise self.VirtualMachineException(
                'Could not migrate VM: %s (%s -> %s)' %
                (str(e), self.host.get_uri(), dest_uri)
            )
        # Update host information
        self.host = dest
        self.save()
        # Clear cached state
        cache.delete('VM' + str(self.id) + '-State')
        return True

    # Deploy generic operation encompasses creating the image and defining
    # the VM within libvirt
    def deploy(self):
        try:
            # Details of deployment times
            t0 = time.time()
            
            # Will copy the image to the destination host
            self.disk_path = self.image.deploy(self)

            # Time spent copying image
            copy_time = time.time() - t0

            t0 = time.time()

            # Define domain using the XML default description
            # Open XML template for creating a VM
            xml = render_to_string("xml/default_vm.xml", {'vm': self})

            # Defines the VM in libvirt
            self.define(xml)
            # Update VM information
            self.save()
            # Time spent defining and saving
            define_time = time.time() - t0

        except Exception as e:
            raise self.VirtualMachineException(
                'Could not deploy VM: ' + str(e)
            )

        return {"copy_time": copy_time, "define_time": define_time}

    # Undo the generic deployment operation within libvirt
    def undeploy(self):
        try:
            if self.host is not None:
                if self.current_state() in [
                    'running', 'blocked on resource',
                    'paused by user', 'being shut down']:
                    self.stop()
                self.undefine()
                logger.debug('Virtual machine undefined: ' + self.name)
            if self.disk_path is not None and self.disk_path != "":
                out = commands.getstatusoutput(
                    'ssh root@' + self.host.hostname + ' ' +
                    '"rm -f ' + self.disk_path + '"'
                )
                if out[0] != 0:
                    raise self.VirtualMachineException(
                        "Could not remove image: " + out[1]
                    )
                logger.debug(
                    'Disk image removed: ' + self.disk_path +
                    ' from ' + self.host.hostname
                )
        except Exception as e:
            raise self.VirtualMachineException(
                'Could not undeploy VM completely: ' + str(e)
            )

        # Clear cached state
        cache.delete('VM' + str(self.id) + '-State')
        return True

    def get_libvirt_connection(self, force_tcp=False):
        # If the VM is not bound to a host
        if self.host is None:
            raise self.VirtualMachineException(
                "VM is not attached to any host"
            )
        else:
            # Tries to connect to libvirt (might raise an exception)
            return self.host.libvirt_connect(force_tcp=force_tcp)

    def get_libvirt_domain(self, force_tcp=False):

        if isinstance(self.libvirt_domain, libvirt.virDomain):
            return self.libvirt_domain

        # Connect to libvirt host (might raise an exception)
        lv_conn = self.get_libvirt_connection(force_tcp=force_tcp)

        # Selects the VM
        try:
            self.libvirt_domain = lv_conn.lookupByName(self.name)
        except libvirtError as e:
            #logger.error('VM ' + self.name + ' not found: ' + str(e))
            raise self.VirtualMachineException(
                'VM ' + self.name + ' not found: ' + str(e)
            )

        return self.libvirt_domain

    # If a VM belongs to a slice it should have the slice name as suffix
    def save(self, *args, **kwargs):
        if self.belongs_to_slice is not None:
            slice_name = self.belongs_to_slice.name
            # If VM name is shorter than the slice name, it means there
            # is no suffix or of the suffix is not found in the name
            if (len(self.name) <= len(slice_name)
                or self.name[-len(slice_name):] != slice_name
            ):
                self.name += "-" + slice_name

        # Use normal save from model
        super(VirtualMachine, self).save(*args, **kwargs)

    def install_interface(self, interface):
        # Selects the VM
        libvirt_dom = self.get_libvirt_domain()

        # Define domain using the XML default description
        # Open XML template for creating a VM
        xml = render_to_string(
            "xml/default_interface.xml", {'interface': interface}
        )

        try:
            libvirt_dom.attachDeviceFlags(xml, VIR_DOMAIN_AFFECT_CURRENT)
        except libvirtError as e:
            raise self.VirtualMachineException(
                'Could not attach interface to %s %s' % (self.name, str(e))
            )

        return True

    def __unicode__(self):
        return self.name

    class VirtualMachineException(VirtualDevice.VirtualDeviceException):
        pass

    # Makes django recognize model in split modules
    class Meta:
        app_label = 'cloud'


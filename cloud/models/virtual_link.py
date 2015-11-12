import commands
import httplib
import json
import logging
import os
import socket
from django.conf import settings
from django.db import models
from cloud.models.virtual_interface import VirtualInterface
from cloud.models.virtual_machine import VirtualMachine
from cloud.models.virtual_router import VirtualRouter
from cloud.models.base_model import BaseModel

# Get an instance of a logger
logger = logging.getLogger(__name__)

LINK_STATES = (
        (u'created', u'Created'),
        (u'waiting', u'Waiting'),
        (u'establish', u'Established'),
        (u'inactive', u'Inactive'),
        (u'failed', u'Failed'),
)

class VirtualLink(BaseModel):
    belongs_to_slice = models.ForeignKey(
        'Slice', # Import as string to avoid circular import problems
        blank=True,
        null=True
    )
    if_start = models.ForeignKey(
        VirtualInterface,
        verbose_name="Link start",
        related_name='virtuallink_set_start'
    )
    if_end = models.ForeignKey(
        VirtualInterface,
        verbose_name="Link end",
        related_name='virtuallink_set_end'
    )
    state = models.CharField(max_length=10, choices=LINK_STATES, default='created', db_index=True)
    path = models.TextField(blank=True, null=True)

    def current_state(self):
        # Check first internal state
        if self.state == 'created' or self.state == 'waiting':
            return self.get_state_display()

        # Router to Router link
        if hasattr(self.if_start.attached_to, "virtualrouter") and hasattr(self.if_end.attached_to, "virtualrouter"):
            # TODO: return current_state_ovspatch()
            pass
        # VM to VM link
        elif hasattr(self.if_start.attached_to, "virtualmachine") and hasattr(self.if_end.attached_to, "virtualmachine"):
            return self.current_state_of()
        # VM to Router (or vice-versa) link
        else:
            # TODO: return current_state_ovs()
            pass

        return self.get_state_display()

    def establish(self):
        result = False

        # Finding attachment devices
        if hasattr(self.if_start.attached_to, "virtualrouter"):
            dev_start = self.if_start.attached_to.virtualrouter
        elif hasattr(self.if_start.attached_to, "virtualmachine"):
            dev_start = self.if_start.attached_to.virtualmachine
        else:
            raise self.VirtualLinkException('Interface not attached to a valid virtual device')
        if hasattr(self.if_end.attached_to, "virtualrouter"):
            dev_end = self.if_end.attached_to.virtualrouter
        elif hasattr(self.if_end.attached_to, "virtualmachine"):
            dev_end = self.if_end.attached_to.virtualmachine
        else:
            raise self.VirtualLinkException('Interface not attached to a valid virtual device')

        # Router to Router link
        if isinstance(dev_start, VirtualRouter) and isinstance(dev_end, VirtualRouter):
            # If both routers are at the same host establish with ovspatch
            if dev_start.host == dev_end.host:
                result = self.establish_ovspatch()
            else:
                # TODO: Implement this, maybe a gre tunnel can make it
                raise self.VirtualLinkException('Cannot connect two routers in different hosts')
            
        # VM to VM link
        elif isinstance(dev_start, VirtualMachine) and isinstance(dev_end, VirtualMachine):
            result = self.establish_of()
        # VM to Router (or vice-versa) link
        else:
            # If both devices are at the same host establish with ovs
            if dev_start.host == dev_end.host:
                result = self.establish_ovs()
            else:
                # TODO: Implement this, maybe a gre tunnel can make it
                raise self.VirtualLinkException('Cannot connect two virtual devices in different hosts')

        if result:
            self.state = 'establish'
            self.save()

        return result

    def unestablish(self):
        result = False

        # Router to Router link
        if hasattr(self.if_start.attached_to, "virtualrouter") and hasattr(self.if_end.attached_to, "virtualrouter"):
            # TODO: Old Way with iplink
            #return self.unestablish_iplink()
            result = self.unestablish_ovspatch()

        # VM to VM link
        elif hasattr(self.if_start.attached_to, "virtualmachine") and hasattr(self.if_end.attached_to, "virtualmachine"):
            result = self.unestablish_of()
        # VM to Router (or vice-versa) link
        else:
            result = self.unestablish_ovs()

        if result:
            self.state = 'created'
            self.save()

        return True

    # Self migrate links to follow their endpoints
    def migrate(self):
        # TODO: find way to migrate links more intelligently, for now just unestablish them 
        # at one locations and restablish at another
        self.unestablish()
        self.establish()

    # Check status of virtual link on OpenFlow Controller
    def current_state_of(self):
        return self.get_state_display()

    # Create the virtual link on OpenFlow Controller
    def establish_of(self):
        # Link is already established or is set to be
        current_state = self.current_state()
        if current_state == 'Established' or current_state == 'Waiting':
            return True

        eth1 = self.if_start.target
        eth2 = self.if_end.target
        if eth1 == "" or eth2 == "":
            raise self.VirtualLinkException("Invalid pair of interfaces (" + eth1 + "-" + eth2 + ")")

        mac1 = self.if_start.mac_address
        mac2 = self.if_end.mac_address
        vm1 = self.if_start.attached_to.virtualmachine
        h1 = vm1.host
        vm2 = self.if_end.attached_to.virtualmachine
        h2 = vm2.host
        br1 = h1.get_openvswitch_bridge()
        br2 = h2.get_openvswitch_bridge()
        if h1 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(vm1) + ")")
        if h2 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(vm2) + ")")

        # Add interfaces to host bridges
        h1.add_openvswitch_port(eth1)
        h2.add_openvswitch_port(eth2)

        # Update local state to waiting
        self.state = 'waiting'
        self.save()

        # TODO: don't use curl, because we need to handle HTTP error codes
        command = 'curl -s http://%s:8080/wm/core/controller/switches/json' % settings.SDN_CONTROLLER['ip']
        result = os.popen(command).read()
        parsed_result = json.loads(result)
        logger.debug(command)
        #logger.debug(result)

        # Search for source and destination switches and ports
        src_switch = src_port = dst_switch = dst_port = None
        for sw in parsed_result:
            for pt in sw['ports']:
                if pt['name'] == eth1:
                    src_port = pt['portNumber']
                if pt['name'] == br1:
                    src_switch = sw['dpid']
                if pt['name'] == eth2:
                    dst_port = pt['portNumber']
                if pt['name'] == br2:
                    dst_switch = sw['dpid']


        if src_port is None or src_switch is None or dst_port is None or dst_switch is None:
            # Update local state to waiting
            self.state = 'failed'
            self.save()
            raise self.VirtualLinkException("Could not establish find switch/port in the network")

        # Everything found, will create circuit
        logger.debug("Creating circuit: from %s port %s -> %s port %s" % (src_switch, src_port, dst_switch, dst_port))
        command = "curl -s http://%s:8080/wm/topology/route/%s/%s/%s/%s/json" % (settings.SDN_CONTROLLER['ip'], src_switch, src_port, dst_switch, dst_port)
        result = os.popen(command).read()
        parsed_result = json.loads(result)
        logger.debug(command)
        #logger.debug(result)

        # Set link path to be recorded
        self.path = result

        # Result is a list of coupled switch in/out ports, every two ports (items on the list) represent a hop
        for i in range(len(parsed_result)):
            if i % 2 == 0:
                dpid = parsed_result[i]['switch']
                port1 = parsed_result[i]['port']
            else:
                port2 = parsed_result[i]['port']

                # IMPORTANT NOTE: current Floodlight StaticFlowEntryPusher (0.90)
                # assumes all flow entries to have unique name across all switches

                # Forward flow
                command = 'curl -s -d \'{"switch": "%s", "name":"%slink%d.f", "src-mac":"%s", "cookie":"0", "priority":"32768", "ingress-port":"%d","active":"true", "actions":"output=%d"}\' http://%s:8080/wm/staticflowentrypusher/json' % (dpid, dpid.replace(':', ''), self.id, mac1, port1, port2, settings.SDN_CONTROLLER['ip'])
                result = os.popen(command).read()
                logger.debug(command)
                #logger.debug(result)

                # Backward flow
                command = 'curl -s -d \'{"switch": "%s", "name":"%slink%d.r", "src-mac":"%s", "cookie":"0", "priority":"32768", "ingress-port":"%d","active":"true", "actions":"output=%d"}\' http://%s:8080/wm/staticflowentrypusher/json' % (dpid, dpid.replace(':', ''), self.id, mac2, port2, port1, settings.SDN_CONTROLLER['ip'])
                result = os.popen(command).read()
                logger.debug(command)
                #logger.debug(result)

        logger.info('Link established with length: %d' % (len(parsed_result)/2))

        # Update local state to established
        self.state = 'establish'
        self.save()

        return True

    # Deletes a virtual link on OpenFlow Controller
    def unestablish_of(self):
        # Was not established
        current_state = self.current_state()
        if current_state == 'Created':
            return True

        eth1 = self.if_start.target
        eth2 = self.if_end.target
        if eth1 == "" or eth2 == "":
            raise self.VirtualLinkException("Invalid pair of interfaces (" + eth1 + "-" + eth2 + ")")

        vm1 = self.if_start.attached_to.virtualmachine
        vm2 = self.if_end.attached_to.virtualmachine
        h1 = vm1.host
        h2 = vm2.host
        br1 = h1.get_openvswitch_bridge()
        br2 = h2.get_openvswitch_bridge()
        if h1 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(vm1) + ")")
        if h2 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(vm2) + ")")

        # Remove interfaces from host bridges
        h1.del_openvswitch_port(eth1)
        h2.del_openvswitch_port(eth2)

        # No path recorded
        if self.path is None:
            self.state = 'failed'
            self.save()
            logger.warning('Path for link %s not recorded' % str(self))
            return True

        # Recover path originally established to remove every entry
        parsed_result = json.loads(self.path)
        if type(parsed_result) is not list:
            self.state = 'failed'
            self.save()
            logger.warning('Invalid path for link %s' % str(self))
            return True

        # Result is a list of coupled switch in/out ports, every two ports (items on the list) represent a hop
        for i in range(len(parsed_result)):
            if not (type(parsed_result[i]) is dict and parsed_result[i].has_key('switch') and parsed_result[i].has_key('port')):
                self.state = 'failed'
                self.save()
                logger.warning('Invalid path for link %s' % str(self))
                return True

            if i % 2 == 0:
                dpid = parsed_result[i]['switch']
                port1 = parsed_result[i]['port']
            else:
                port2 = parsed_result[i]['port']

            # Forward flow
            command = 'curl -X DELETE -d \'{"name":"%slink%d.f"}\' http://%s:8080/wm/staticflowentrypusher/json' % ( dpid.replace(':', ''), self.id, settings.SDN_CONTROLLER['ip'] )
            result = os.popen(command).read()
            logger.debug(command)
            #logger.debug(result)
    
            # Backward flow
            command = 'curl -X DELETE -d \'{"name":"%slink%d.r"}\' http://%s:8080/wm/staticflowentrypusher/json' % ( dpid.replace(':', ''), self.id, settings.SDN_CONTROLLER['ip'] )
            result = os.popen(command).read()
            logger.debug(command)
            #logger.debug(result)
    
            self.state = 'inactive'
            self.save()

        return True

    def establish_ovspatch(self):
        bridge1 = self.if_start.attached_to.virtualrouter.dev_name
        bridge2 = self.if_end.attached_to.virtualrouter.dev_name
        port1 = bridge1 + '_to_' + bridge2
        port2 = bridge2 + '_to_' + bridge1
        h1 = self.if_start.attached_to.virtualrouter.host
        h2 = self.if_end.attached_to.virtualrouter.host
        if h1 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(bridge1) + ")")
        if h2 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(bridge2) + ")")

        # Add patch port in bridge 1
        cmd = 'ovs-vsctl --db=' + h1.ovsdb + ' --timeout=3 -- add-port ' + bridge1 + ' ' + port1 + ' -- set interface ' + port1 + ' type=patch options:peer=' + port2
        out = commands.getstatusoutput(cmd)
        if out[0] != 0:
            logger.warning(cmd)
            raise self.VirtualLinkException("Could not add patch (" + port1 + ") to bridges (" + bridge1 + "-" + bridge2 + "): " + out[1])

        # Add patch port in bridge 2
        cmd = 'ovs-vsctl --db=' + h2.ovsdb + ' --timeout=3 -- add-port ' + bridge2 + ' ' + port2 + ' -- set interface ' + port2 + ' type=patch options:peer=' + port1
        out = commands.getstatusoutput(cmd)
        if out[0] != 0:
            logger.warning(cmd)
            raise self.VirtualLinkException("Could not add patch (" + port2 + ") to bridges (" + bridge1 + "-" + bridge2 + "): " + out[1])

        return True

    def unestablish_ovspatch(self):
        bridge1 = self.if_start.attached_to.virtualrouter.dev_name
        bridge2 = self.if_end.attached_to.virtualrouter.dev_name
        port1 = bridge1 + '_to_' + bridge2
        port2 = bridge2 + '_to_' + bridge1
        h1 = self.if_start.attached_to.virtualrouter.host
        h2 = self.if_end.attached_to.virtualrouter.host
        if h1 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(bridge1) + ")")
        if h2 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(bridge2) + ")")

        # Remove port on source bridge
        cmd = 'ovs-vsctl --db=' + h1.ovsdb + ' --timeout=3 -- --if-exists del-port ' + bridge1 + ' ' + port1
        out = commands.getstatusoutput(cmd)
        if out[0] != 0:
            logger.warning(cmd)
            raise self.VirtualLinkException("Could not delete patch (" + port1 + ") to bridges (" + bridge1 + "-" + bridge2 + "): " + out[1])
        # Remove port on destination bridge
        cmd = 'ovs-vsctl --db=' + h2.ovsdb + ' --timeout=3 -- --if-exists del-port ' + bridge2 + ' ' + port2
        out = commands.getstatusoutput(cmd)
        if out[0] != 0:
            logger.warning(cmd)
            raise self.VirtualLinkException("Could not delete patch (" + port2 + ") to bridges (" + bridge1 + "-" + bridge2 + "): " + out[1])

        return True

    def establish_ovs(self):

        bridge = eth = ""

        if hasattr(self.if_start.attached_to, 'virtualrouter'):
            bridge = self.if_start.attached_to.virtualrouter.dev_name
            bridge_host = self.if_start.attached_to.virtualrouter.host
        elif hasattr(self.if_start.attached_to, 'virtualmachine'):
            eth = self.if_start.target

        if hasattr(self.if_end.attached_to, 'virtualrouter'):
            bridge = self.if_end.attached_to.virtualrouter.dev_name
            bridge_host = self.if_end.attached_to.virtualrouter.host
        elif hasattr(self.if_end.attached_to, 'virtualmachine'):
            eth = self.if_end.target

        if bridge == "" or eth == "":
            raise self.VirtualLinkException("Invalid pair of interfaces (" + eth + "-" + bridge + ")")

        if bridge_host is None:
            raise self.VirtualLinkException("Target virtual router not deployed (" + str(bridge) + ")")

        # First remove interface from previous ovs (if it was somewhere else)
        out = commands.getstatusoutput('ovs-vsctl --db=' + bridge_host.ovsdb + ' --timeout=3 port-to-br ' + eth)
        if out[0] == 0:
            # Interface was found at another switch
            out = commands.getstatusoutput('ovs-vsctl --db=' + bridge_host.ovsdb + ' --timeout=3 del-port "' + out[1] + '" ' + eth)

        out = commands.getstatusoutput('ovs-vsctl --db=' + bridge_host.ovsdb + ' --timeout=3 add-port "' + bridge + '" ' + eth)
        if out[0] != 0:
            raise self.VirtualLinkException("Could not add port (" + eth + ") to bridge (" + bridge + "): " + out[1])

        return True

    def unestablish_ovs(self):

        bridge = eth = ""

        if hasattr(self.if_start.attached_to, 'virtualrouter'):
            bridge = self.if_start.attached_to.virtualrouter.dev_name
            bridge_host = self.if_start.attached_to.virtualrouter.host
        elif hasattr(self.if_start.attached_to, 'virtualmachine'):
            eth = self.if_start.target

        if hasattr(self.if_end.attached_to, 'virtualrouter'):
            bridge = self.if_end.attached_to.virtualrouter.dev_name
            bridge_host = self.if_end.attached_to.virtualrouter.host
        elif hasattr(self.if_end.attached_to, 'virtualmachine'):
            eth = self.if_end.target

        if bridge == "" or eth == "":
            raise self.VirtualLinkException("Invalid pair of interfaces (" + eth + "-" + bridge + ")")

        if bridge_host is None:
            raise self.VirtualLinkException("Target virtual router not deployed (" + str(bridge) + ")")

        out = commands.getstatusoutput('ovs-vsctl --db=' + bridge_host.ovsdb + ' --timeout=3 del-port "' + bridge + '" ' + eth)
        if out[0] != 0:
            logger.warning("Could not add port (" + eth + ") to bridge (" + bridge + "): " + out[1])
            raise self.VirtualLinkException("Could not delete port (" + eth + ") to bridge (" + bridge + "): " + out[1])

        return True

    def __unicode__(self):
        return "VirtualLink #%d" % self.id

    class VirtualLinkException(BaseModel.ModelException):
        pass


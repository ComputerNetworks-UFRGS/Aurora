import commands
import httplib
import json
import logging
import os
import socket
from django.conf import settings
from django.db import models
from cloud.models.virtual_interface import VirtualInterface
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

        # Router to Router link
        if hasattr(self.if_start.attached_to, "virtualrouter") and hasattr(self.if_end.attached_to, "virtualrouter"):
            # TODO: Old Way with iplink
            #return self.establish_iplink()
            result = self.establish_ovspatch()
        # VM to VM link
        elif hasattr(self.if_start.attached_to, "virtualmachine") and hasattr(self.if_end.attached_to, "virtualmachine"):
            result = self.establish_of()
        # VM to Router (or vice-versa) link
        else:
            result = self.establish_ovs()

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

    # Check status of virtual link on OpenFlow Controller
    def current_state_of(self):
        # Forward flow
        command = 'curl -s http://%s:8080/wm/staticflowentrypusher/list/all/json' % (settings.SDN_CONTROLLER['ip'])
        result = os.popen(command).read()
        parsed_result = json.loads(result)
        logger.debug(command)
        logger.debug(result)

        for sw in parsed_result:
            if parsed_result[sw].has_key('link%s.f' % self.id) and parsed_result[sw].has_key('link%s.r' % self.id):
                # Might have failed before, it is working now
                if self.state != 'establish':
                    self.state = 'establish'
                    self.save()
                return self.get_state_display()

        # Link was not found in network
        self.state = 'failed'
        self.save()
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
        if h1 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(vm1) + ")")
        if h2 is None:
            raise self.VirtualLinkException("Target virtual device not deployed (" + str(vm2) + ")")

        br1 = "hostbr" + str(h1.id)
        br2 = "hostbr" + str(h2.id)

        # Add the interfaces to the default bridge
        h1_ip = socket.gethostbyname(h1.hostname)
        out = commands.getstatusoutput('ovs-vsctl --db=tcp:' + h1_ip + ':8888 --timeout=3 -- --may-exist add-port "' + br1 + '" ' + eth1)
        if out[0] != 0:
            raise self.VirtualLinkException('Could not add port (' + eth1 + ') to bridge (' + br1 + '): ' + out[1])

        h2_ip = socket.gethostbyname(h2.hostname)
        out = commands.getstatusoutput('ovs-vsctl --db=tcp:' + h2_ip + ':8888 --timeout=3 -- --may-exist add-port "' + br2 + '" ' + eth2)
        if out[0] != 0:
            raise self.VirtualLinkException('Could not add port (' + eth2 + ') to bridge (' + br2 + '): ' + out[1])

        # Update local state to waiting
        self.state = 'waiting'
        self.save()
        # TODO: temporary implementation with Floodlight
        command = 'curl -s http://%s:8080/wm/core/controller/switches/json' % settings.SDN_CONTROLLER['ip']
        result = os.popen(command).read()
        parsed_result = json.loads(result)
        logger.debug(command)
        logger.debug(result)

        # Search for source and destination switches and ports
        for sw in parsed_result:
            src_switch = src_port = dst_switch = dst_port = None
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
        logger.debug(result)

        # Route format
        # [
        #     {
        #         "port": inport,
        #         "switch": dpid1
        #     },
        #     {
        #         "port": outport,
        #         "switch": dpid1
        #     },
        #     ...
        #     {
        #         "port": inport,
        #         "switch": dpidN
        #     },
        #     {
        #         "port": outport,
        #         "switch": dpidN
        #     }
        # ]

        for i in range(len(parsed_result)):
            if i % 2 == 0:
                dpid1 = parsed_result[i]['switch']
                port1 = parsed_result[i]['port']
            else:
                dpid2 = parsed_result[i]['switch']
                port2 = parsed_result[i]['port']

                # IMPORTANT NOTE: current Floodlight StaticflowEntryPusher
                # assumes all flow entries to have unique name across all switches

                # Forward flow
                command = 'curl -s -d \'{"switch": "%s", "name":"link%s.f", "src-mac":"%s", "cookie":"0", "priority":"32768", "ingress-port":"%s","active":"true", "actions":"output=%s"}\' http://%s:8080/wm/staticflowentrypusher/json' % (dpid1, self.id, mac1, port1, port2, settings.SDN_CONTROLLER['ip'])
                result = os.popen(command).read()
                logger.debug(command)
                logger.debug(result)

                # Backward flow
                command = 'curl -s -d \'{"switch": "%s", "name":"link%s.r", "src-mac":"%s", "cookie":"0", "priority":"32768", "ingress-port":"%s","active":"true", "actions":"output=%s"}\' http://%s:8080/wm/staticflowentrypusher/json' % (dpid1, self.id, mac2, port2, port1, settings.SDN_CONTROLLER['ip'])
                result = os.popen(command).read()
                logger.debug(command)
                logger.debug(result)

        return True

    # Deletes a virtual link on OpenFlow Controller
    def unestablish_of(self):
        # Was not established
        current_state = self.current_state()
        if current_state == 'Created':
            return True

        # Forward flow
        command = 'curl -X DELETE -d \'{"name":"link%s.f"}\' http://%s:8080/wm/staticflowentrypusher/json' % (self.id, settings.SDN_CONTROLLER['ip'])
        result = os.popen(command).read()
        logger.debug(command)
        logger.debug(result)

        # Backward flow
        command = 'curl -X DELETE -d \'{"name":"link%s.r"}\' http://%s:8080/wm/staticflowentrypusher/json' % (self.id, settings.SDN_CONTROLLER['ip'])
        result = os.popen(command).read()
        logger.debug(command)
        logger.debug(result)

        #    logger.warning("Could not establish link:" + out[1])
        #    # Update local state to waiting
        #    self.state = 'failed'
        #    self.save()
        #    raise self.VirtualLinkException("Could not establish link: " + out[1])

        self.state = 'inactive'
        self.save()
        return True

    def establish_ovspatch(self):
        bridge1 = self.if_start.attached_to.virtualrouter.dev_name
        bridge2 = self.if_end.attached_to.virtualrouter.dev_name
        port1 = bridge1 + '_to_' + bridge2
        port2 = bridge2 + '_to_' + bridge1

        # Add patch port in bridge 1
        cmd = 'ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 -- add-port ' + bridge1 + ' ' + port1 + ' -- set interface ' + port1 + ' type=patch options:peer=' + port2
        out = commands.getstatusoutput(cmd)
        if out[0] != 0:
            logger.warning(cmd)
            raise self.VirtualLinkException("Could not add patch (" + port1 + ") to bridges (" + bridge1 + "-" + bridge2 + "): " + out[1])

        # Add patch port in bridge 2
        cmd = 'ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 -- add-port ' + bridge2 + ' ' + port2 + ' -- set interface ' + port2 + ' type=patch options:peer=' + port1
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

        # Remove port on source bridge
        cmd = 'ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 -- --if-exists del-port ' + bridge1 + ' ' + port1
        out = commands.getstatusoutput(cmd)
        if out[0] != 0:
            logger.warning(cmd)
            raise self.VirtualLinkException("Could not delete patch (" + port1 + ") to bridges (" + bridge1 + "-" + bridge2 + "): " + out[1])
        # Remove port on destination bridge
        cmd = 'ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 -- --if-exists del-port ' + bridge2 + ' ' + port2
        out = commands.getstatusoutput(cmd)
        if out[0] != 0:
            logger.warning(cmd)
            raise self.VirtualLinkException("Could not delete patch (" + port2 + ") to bridges (" + bridge1 + "-" + bridge2 + "): " + out[1])

        return True

    def establish_ovs(self):

        bridge = eth = ""

        if hasattr(self.if_start.attached_to, 'virtualrouter'):
            bridge = self.if_start.attached_to.virtualrouter.dev_name
        elif hasattr(self.if_start.attached_to, 'virtualmachine'):
            eth = self.if_start.target

        if hasattr(self.if_end.attached_to, 'virtualrouter'):
            bridge = self.if_end.attached_to.virtualrouter.dev_name
        elif hasattr(self.if_end.attached_to, 'virtualmachine'):
            eth = self.if_end.target

        if bridge == "" or eth == "":
            logger.warning("Invalid pair of interfaces (" + eth + "-" + bridge + ")")
            raise self.VirtualLinkException("Invalid pair of interfaces (" + eth + "-" + bridge + ")")

        # First remove interface from previous ovs (if it was somewhere else)
        out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 port-to-br ' + eth)
        if out[0] == 0:
            # Interface was found at another switch
            out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 del-port "' + out[1] + '" ' + eth)

        out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 add-port "' + bridge + '" ' + eth)
        if out[0] != 0:
            logger.warning("Could not add port (" + eth + ") to bridge (" + bridge + "): " + out[1])
            raise self.VirtualLinkException("Could not add port (" + eth + ") to bridge (" + bridge + "): " + out[1])

        return True

    def unestablish_ovs(self):

        bridge = eth = ""

        if hasattr(self.if_start.attached_to, 'virtualrouter'):
            bridge = self.if_start.attached_to.virtualrouter.dev_name
        elif hasattr(self.if_start.attached_to, 'virtualmachine'):
            eth = self.if_start.target

        if hasattr(self.if_end.attached_to, 'virtualrouter'):
            bridge = self.if_end.attached_to.virtualrouter.dev_name
        elif hasattr(self.if_end.attached_to, 'virtualmachine'):
            eth = self.if_end.target

        if bridge == "" or eth == "":
            logger.warning("Invalid pair of interfaces (" + eth + "-" + bridge + ")")
            raise self.VirtualLinkException("Invalid pair of interfaces (" + eth + "-" + bridge + ")")

        out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 del-port "' + bridge + '" ' + eth)
        if out[0] != 0:
            logger.warning("Could not add port (" + eth + ") to bridge (" + bridge + "): " + out[1])
            raise self.VirtualLinkException("Could not delete port (" + eth + ") to bridge (" + bridge + "): " + out[1])

        return True

    def establish_iplink(self):
        eth1 = self.if_start.target
        eth2 = self.if_end.target

        bridge1 = self.if_start.attached_to.virtualrouter.dev_name
        bridge2 = self.if_end.attached_to.virtualrouter.dev_name
        # TODO: Get correct hostname here
        out = commands.getstatusoutput('ssh root@localhost "ip link add name ' + eth1 + ' type veth peer name ' + eth2 + '; ifconfig ' + eth1 + ' up ; ifconfig ' + eth2 + ' up"')
        if out[0] != 0:
            logger.warning("Could not add link pair (" + eth1 + ") peer (" + eth2 + "): " + out[1])
            raise self.VirtualLinkException("Could not add link pair (" + eth1 + ") peer (" + eth2 + "): " + out[1])

        out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 add-port "' + bridge1 + '" ' + eth1)
        if out[0] != 0:
            logger.warning("Could not add port (" + eth1 + ") to bridge (" + bridge1 + "): " + out[1])
            raise self.VirtualLinkException("Could not add port (" + eth1 + ") to bridge (" + bridge1 + "): " + out[1])

        out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 add-port "' + bridge2 + '" ' + eth2)
        if out[0] != 0:
            logger.warning("Could not add port (" + eth2 + ") to bridge (" + bridge2 + "): " + out[1])
            raise self.VirtualLinkException("Could not add port (" + eth2 + ") to bridge (" + bridge2 + "): " + out[1])

        return True

    def unestablish_iplink(self):
        eth1 = self.if_start.target
        eth2 = self.if_end.target

        bridge1 = self.if_start.attached_to.virtualrouter.dev_name
        bridge2 = self.if_end.attached_to.virtualrouter.dev_name

        out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 del-port "' + bridge1 + '" ' + eth1)
        if out[0] != 0:
            logger.warning("Could not delete port (" + eth1 + ") to bridge (" + bridge1 + "): " + out[1])
            raise self.VirtualLinkException("Could not delete port (" + eth1 + ") to bridge (" + bridge1 + "): " + out[1])

        out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 del-port "' + bridge2 + '" ' + eth2)
        if out[0] != 0:
            logger.warning("Could not delete port (" + eth2 + ") to bridge (" + bridge2 + "): " + out[1])
            raise self.VirtualLinkException("Could not delete port (" + eth2 + ") to bridge (" + bridge2 + "): " + out[1])

        # ip link will delete the pair of interfaces even if we delete only eth1
        # TODO: Get correct hostname here
        out = commands.getstatusoutput('ssh root@localhost "ip link delete ' + eth1 + '"')
        if out[0] != 0:
            logger.warning("Could not delete link pair (" + eth1 + ") peer (" + eth2 + "): " + out[1])
            raise self.VirtualLinkException("Could not delete link pair (" + eth1 + ") peer (" + eth2 + "): " + out[1])

        return True

    def __unicode__(self):
        return "VirtualLink #%d" % self.id

    class VirtualLinkException(BaseModel.ModelException):
        pass


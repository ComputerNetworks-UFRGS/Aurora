import logging
import commands
import json, httplib
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
        # TODO: Machete master
        return self.get_state_display()

        # Check first internal state
        if self.state == 'created' or self.state == 'waiting':
            return self.get_state_display()

        # Check state with Openflow Controller OLD IMPLEMENTATION WITH NOX
        #try:
        #    headers = {"Content-type": "application/json"}
        #    # openflow controller is currently running on localhost
        #    conn = httplib.HTTPConnection("localhost", 8000)
        #    conn.request("GET", "/cloud/link/state/" + str(self.id), "", headers)
        #    response = conn.getresponse()
        #    # response by default is a json formatted string containing all information about a link
        #    json_data = response.read()
        #    conn.close()
        #    logger.debug("Response: %s %s - Data: %s" % (response.status, response.reason, json_data))
        #    link_data = json.loads(json_data)
        #    if response.status == 200:
        #        if link_data.has_key("state"):
        #            return link_data["state"]
        #        else:
        #            return "Weird response"
        #    elif response.status == 404:
        #        return "Virtual Link not found"
        #    else:
        #        return "Weird status"

        #except Exception as e:
        #    logger.warning("Problems communicating with the OpenFlow Controller: %s" % str(e))
        #    return "Problems communicating with the OpenFlow Controller: %s" % str(e)

    def establish(self):

        # Router to Router link
        if hasattr(self.if_start.attached_to, "virtualrouter") and hasattr(self.if_end.attached_to, "virtualrouter"):
            return self.establish_iplink()
        # VM to VM link
        elif hasattr(self.if_start.attached_to, "virtualmachine") and hasattr(self.if_end.attached_to, "virtualmachine"):
            return self.establish_of()
        # VM to Router (or vice-versa) link
        else:
            return self.establish_ovs()

    # Create the virtual link on OpenFlow Controller
    def establish_of(self):
        # Link is already established or is set to be
        current_state = self.current_state()
        if current_state == 'Established' or current_state == 'Waiting':
            return True

        bridge = "virbr2"
        eth1 = self.if_start.target
        eth2 = self.if_end.target

        if eth1 == "" or eth2 == "":
            logger.warning("Invalid pair of interfaces (" + eth1 + "-" + eth2 + ")")
            raise self.VirtualLinkException("Invalid pair of interfaces (" + eth1 + "-" + eth2 + ")")

        # Add the interface to the default bridge
        # TODO: Use the remote host openvswitch connection
        out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 -- --may-exist add-port "' + bridge + '" ' + eth1)
        if out[0] != 0:
            logger.warning("Could not add port (" + eth1 + ") to bridge (" + bridge + "): " + out[1])
            raise self.VirtualLinkException("Could not add port (" + eth1 + ") to bridge (" + bridge + "): " + out[1])
        out = commands.getstatusoutput('ovs-vsctl --db=tcp:127.0.0.1:8888 --timeout=3 -- --may-exist add-port "' + bridge + '" ' + eth2)
        if out[0] != 0:
            logger.warning("Could not add port (" + eth2 + ") to bridge (" + bridge + "): " + out[1])
            raise self.VirtualLinkException("Could not add port (" + eth2 + ") to bridge (" + bridge + "): " + out[1])

        # Update local state to waiting
        self.state = 'waiting'
        self.save()
        # TODO: temporary implementation with Floodlight
        if_start = self.if_start.target
        if_end = self.if_end.target
        bridge = "virbr2"
        out = commands.getstatusoutput('/home/aurora/Aurora/cloud/helpers/circuitpusher.py --controller 127.0.0.1:8080 --add --name link' + str(self.id) + ' --type phy --src ' + if_start + ':' + bridge + ' --dst ' + if_end + ':' + bridge)
        if out[0] != 0:
            logger.warning("Could not establish link:" + out[1])
            # Update local state to waiting
            self.state = 'failed'
            self.save()
            raise self.VirtualLinkException("Could not establish link: " + out[1])

        self.state = 'establish'
        self.save()
        return True

    def unestablish(self):
        # Router to Router link
        if hasattr(self.if_start.attached_to, "virtualrouter") and hasattr(self.if_end.attached_to, "virtualrouter"):
            return self.unestablish_iplink()
        # VM to VM link
        elif hasattr(self.if_start.attached_to, "virtualmachine") and hasattr(self.if_end.attached_to, "virtualmachine"):
            return self.unestablish_of()
        # VM to Router (or vice-versa) link
        else:
            return self.unestablish_ovs()

    # Deletes a virtual link on OpenFlow Controller
    def unestablish_of(self):
        # Was not established
        current_state = self.current_state()
        if current_state == 'Created':
            return True

        # TODO: temporary implementation with Floodlight
        out = commands.getstatusoutput('/home/aurora/Aurora/cloud/helpers/circuitpusher.py --controller 127.0.0.1:8080 --delete --name link' + str(self.id))
        if out[0] != 0:
            logger.warning("Could not establish link:" + out[1])
            # Update local state to waiting
            self.state = 'failed'
            self.save()
            raise self.VirtualLinkException("Could not establish link: " + out[1])

        self.state = 'inactive'
        self.save()
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
        out = commands.getstatusoutput('ssh root@acdc.inf.ufrgs.br "ip link add name ' + eth1 + ' type veth peer name ' + eth2 + '; ifconfig ' + eth1 + ' up ; ifconfig ' + eth2 + ' up"')
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
        out = commands.getstatusoutput('ssh root@acdc.inf.ufrgs.br "ip link delete ' + eth1 + '"')
        if out[0] != 0:
            logger.warning("Could not delete link pair (" + eth1 + ") peer (" + eth2 + "): " + out[1])
            raise self.VirtualLinkException("Could not delete link pair (" + eth1 + ") peer (" + eth2 + "): " + out[1])

        return True


    class VirtualLinkException(BaseModel.ModelException):
        pass


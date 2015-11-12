import logging
import commands
from django.db import models
from cloud.models.host import Host
from cloud.models.base_model import BaseModel

# Get an instance of a logger
logger = logging.getLogger(__name__)

INTERFACE_TYPES = (
        (u'ethernet', u'Ethernet'),
)

INTERFACE_DUPLEX_TYPE = (
        (u'full', u'Full Duplex'),
        (u'half', u'Half Duplex'),
)

class Interface(BaseModel):
    alias = models.CharField(max_length=20)
    attached_to = models.ForeignKey(
        Host,
        verbose_name="Attached to"
    )
    if_type = models.CharField(max_length=10, choices=INTERFACE_TYPES, default='ethernet', db_index=True)
    uplink_speed = models.PositiveIntegerField()
    downlink_speed = models.PositiveIntegerField()
    duplex = models.CharField(max_length=10, choices=INTERFACE_DUPLEX_TYPE, default='full', db_index=True)

    def interface_status(self):
        if not hasattr(self, '_interface_status'):
            self._interface_status = self.check_interface_status()
        return self._interface_status

    def check_interface_status(self):
        bridge = "hostbr" + str(self.attached_to.id)
        ovs_status = self.attached_to.openvswitch_status()
        if ovs_status != 'OK':
            return ovs_status
        else:
            # First remove interface from previous ovs (if it was somewhere else)
            out = commands.getstatusoutput('ovs-vsctl --db=' + self.attached_to.ovsdb + ' --timeout=3 port-to-br "' + self.alias + '"')
            if out[0] == 0:
                # Interface was found at another switch
                out = commands.getstatusoutput('ovs-vsctl --db=' + self.attached_to.ovsdb + ' --timeout=3 del-port "' + out[1] + '" "' + self.alias + '"')
            # Will try to add interface to the bridge (may-exist)
            out = commands.getstatusoutput('ovs-vsctl --db=' + self.attached_to.ovsdb + ' --timeout=3 -- --may-exist add-port "' + bridge + '" "' + self.alias + '"')
            if out[0] != 0:
                return 'Could not add interface (' + self.alias + ') to bridge (' + bridge + ') at ' + self.attached_to.ovsdb + ': ' + out[1]

        return 'OK'

    def __unicode__(self):
        return self.alias

    class InterfaceException(BaseModel.ModelException):
        pass


from django.db import models
from manager.models.device import Device
from manager.helpers.ping import Ping

SWITCH_TYPE = (
        (u'ethernet', u'Ethernet Switch'),
        (u'openflow', u'Openflow Switch'),
)

class Switch(Device):
    hostname = models.CharField(max_length=200)
    sw_type = models.CharField(max_length=10, choices=SWITCH_TYPE, default='ethernet', db_index=True)

    def total_ports(self):
        return self.port_set.count()

    def current_state(self):
        try:
            delay = Ping(self.hostname).run()
            return "Active (" + str(round(delay*1000, 2)) + " ms)"
        except Exception as e:
            return "Off-line (" + str(e) + ")"

    class SwitchException(Device.DeviceException):
        pass

from django.db import models
from cloud.models.device import Device

ROUTER_TYPE = (
        (u'router', u'IP Router'),
)

class Router(Device):
    hostname = models.CharField(max_length=200)
    rt_type = models.CharField(max_length=10, choices=ROUTER_TYPE, default='router', db_index=True)

    def __unicode__(self):
        return self.hostname

    class RouterException(Device.DeviceException):
        pass

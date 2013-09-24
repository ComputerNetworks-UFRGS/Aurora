import logging
from django.db import models
from manager.models.base_model import BaseModel
from manager.models.switch import Switch

# Get an instance of a logger
logger = logging.getLogger(__name__)

PORT_DUPLEX_TYPE = (
    (u'full', u'Full Duplex'),
    (u'half', u'Half Duplex'),
)

# Represents physical ports/interfaces of switches
class Port(BaseModel):
    switch = models.ForeignKey(
        Switch,
        verbose_name="Attached to",
    )
    alias = models.CharField(max_length=20)
    uplink_speed = models.PositiveIntegerField()
    downlink_speed = models.PositiveIntegerField()
    duplex = models.CharField(max_length=10, choices=PORT_DUPLEX_TYPE, default='full', db_index=True)

    connected_interfaces = models.ManyToManyField("Interface", verbose_name="Connected interfaces")
    connected_ports = models.ManyToManyField("Port", verbose_name="Connected ports")

    def count_connected_devices(self):
        return self.connected_interfaces.count() + self.connected_ports.count()  + self.port_set.count()

    def list_connected_devices(self):
        return ", ".join([str(x) for x in self.connected_devices()])

    def connected_devices(self):
        output = []
        for interface in self.connected_interfaces.all():
            output.append(interface.attached_to)
        for port in self.connected_ports.all():
            output.append(port.switch)
        for port in self.port_set.all():
            output.append(port.switch)
        return output

    def __unicode__(self):
        return self.alias

    class PortException(BaseModel.ModelException):
        pass


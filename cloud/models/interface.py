import logging
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

    def __unicode__(self):
        return self.alias

    class InterfaceException(BaseModel.ModelException):
        pass


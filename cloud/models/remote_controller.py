import logging
from django.db import models
from cloud.models.base_model import BaseModel

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Supported connection types
CONNECTION_TYPES = (
        (u'tcp', u'TCP'),
        (u'udp', u'UDP'),
        (u'ptcp', u'PTCP'),
)

CONTROLLER_TYPE = (
        (u'master', u'Master'),
        (u'slave', u'Slave'),
)

class RemoteController(BaseModel):

    belongs_to_slice = models.ForeignKey(
        'Slice', # Import as string to avoid circular import problems
        blank=True,
        null=True
    )
    ip = models.CharField(max_length=100)
    port = models.CharField(max_length=6)
    connection = models.CharField(max_length=10, choices=CONNECTION_TYPES, default='tcp', db_index=True)
    controller_type = models.CharField(max_length=10, choices=CONTROLLER_TYPE, default='master', db_index=True)

    controls_vrouters = models.ManyToManyField("VirtualRouter", verbose_name="Controls virtual routers")

    def current_state(self):
        return "Could not read state"

    def __unicode__(self):
        return self.connection + ":" + self.ip + ":" + self.port

    class RemoteControllerException(BaseModel.ModelException):
        pass

    # Makes django recognize model in split modules
    class Meta:
        app_label = 'cloud'


import logging
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring, tostring
from django.db import models
from cloud.models.base_model import BaseModel

# Get an instance of a logger
logger = logging.getLogger(__name__)

class VirtualDevice(BaseModel):

    belongs_to_slice = models.ForeignKey(
        'Slice', # Import as string to avoid circular import problems
        blank=True,
        null=True
    )

    name = models.CharField(max_length=200)

    def is_virtual_machine(self):
        return hasattr(self, "virtualmachine")

    def __unicode__(self):
        return self.name

    class VirtualDeviceException(BaseModel.ModelException):
        pass

    # Makes django recognize model in split modules
    class Meta:
        app_label = 'cloud'


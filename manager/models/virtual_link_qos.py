import logging
from django.db import models
from manager.models.base_model import BaseModel

# Get an instance of a logger
logger = logging.getLogger(__name__)

class VirtualLinkQos(BaseModel):
    belongs_to_virtual_link = models.OneToOneField('VirtualLink')
    bandwidth_up_maximum = models.IntegerField()
    bandwidth_up_committed = models.IntegerField()
    bandwidth_down_maximum = models.IntegerField()
    bandwidth_down_committed = models.IntegerField()
    latency = models.IntegerField()

    class VirtualLinkQosException(BaseModel.ModelException):
        pass


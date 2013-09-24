import logging
from django.db import models
from manager.models.base_model import BaseModel

# Get an instance of a logger
logger = logging.getLogger(__name__)

class Device(BaseModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    def is_host(self):
        return hasattr(self, "host")

    def is_switch(self):
        return hasattr(self, "switch")

    def is_router(self):
        return hasattr(self, "router")

    def __unicode__(self):
        return self.name

    class DeviceException(BaseModel.ModelException):
        pass

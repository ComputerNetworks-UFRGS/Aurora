import logging
from django.db import models
from manager.models.base_model import BaseModel

# Get an instance of a logger
logger = logging.getLogger(__name__)

class Template(BaseModel):
    name = models.CharField(max_length=200)
    memory = models.PositiveIntegerField()
    vcpu = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return self.name

    class TemplateException(BaseModel.ModelException):
        pass

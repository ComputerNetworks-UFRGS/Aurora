import logging
from django.db import models
from cloud.models.base_model import BaseModel

PROGRAM_STATES = (
        (u'enabled', u'Enabled'),
        (u'disabled', u'Disabled'),
)

class Program(BaseModel):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='programs')
    state = models.CharField(
        max_length=10,
        choices=PROGRAM_STATES,
        default='enabled', db_index=True
    )

    def is_deployment(self):
        return hasattr(self, "deploymentprogram")

    def is_optimization(self):
        return hasattr(self, "optimizationprogram")

    def get_size(self):
        return self.file.file.size

    def __unicode__(self):
        return self.name

    class ProgramException(BaseModel.ModelException):
        # Alter logger to use this file name instead
        logger = logging.getLogger(__name__)

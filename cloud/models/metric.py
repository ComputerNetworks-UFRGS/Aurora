import logging
from django.db import models
from cloud.models.base_model import BaseModel

RETURN_DATA_TYPE = (
        (u'counter', u'Counter'),
        (u'number', u'Number'),
        (u'text', u'Text'),
        (u'object', u'Object'),
)
METRIC_STATES = (
        (u'enabled', u'Enabled'),
        (u'disabled', u'Disabled'),
)
METRIC_SCOPES = (
    (u'slice', u'Slice specific'),
    (u'infra', u'Infrastructure'),
)

class Metric(BaseModel):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='metrics')
    returns = models.CharField(
        max_length=10,
        choices=RETURN_DATA_TYPE,
        default='number', db_index=True
    )
    state = models.CharField(
        max_length=10,
        choices=METRIC_STATES,
        default='enabled', db_index=True
    )
    scope = models.CharField(
        max_length=10,
        choices=METRIC_SCOPES,
        default='infra', db_index=True
    )

    def get_size(self):
        return self.file.file.size

    def __unicode__(self):
        return self.name

    class MetricException(BaseModel.ModelException):
        # Alter logger to use this file name instead
        logger = logging.getLogger(__name__)

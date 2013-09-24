import logging
from django.db import models
from manager.models.base_model import BaseModel

EVENT_STATES = (
        (u'enabled', u'Enabled'),
        (u'disabled', u'Disabled'),
)
RELATIONAL_OPERATION = (
        (u'eq', u'(=) Equals'),
        (u'gt', u'(>) Greater Than'),
        (u'eqgt', u' (>=) Equals or Greater Than'),
        (u'lt', u'(<) Less Than'),
        (u'eqlt', u'(<=) Equals or Less Than'),
        (u'diff', u'(!=) Different'),
)


class Event(BaseModel):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    state = models.CharField(
        max_length=10,
        choices=EVENT_STATES,
        default='enabled', db_index=True
    )
    belongs_to_slice = models.ForeignKey(
        'Slice',  # Import as string to avoid circular import problems
        blank=True,
        null=True
    )
    metric = models.ForeignKey(
        'Metric',  # Import as string to avoid circular import problems
    )
    relational_operation = models.CharField(
        max_length=10,
        choices=RELATIONAL_OPERATION,
        default='eq', db_index=True
    )
    value = models.CharField(max_length=200, unique=True)
    program = models.ForeignKey(
        # Import as string to avoid circular import problems
        'OptimizationProgram',
    )

    def __unicode__(self):
        return self.name

    class EventException(BaseModel.ModelException):
        # Alter logger to use this file name instead
        logger = logging.getLogger(__name__)

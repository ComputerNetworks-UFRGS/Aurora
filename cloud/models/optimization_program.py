import logging
from django.db import models
from cloud.models.program import Program

OPTMIZATION_SCOPES = (
    (u'slice', u'Slice specific'),
    (u'global', u'Global'),
)

class OptimizationProgram(Program):
    scope = models.CharField(max_length=10, choices=OPTMIZATION_SCOPES, default='global', db_index=True)

    class OptimizationProgramException(Program.ProgramException):
        # Alter logger to use this file name instead
        logger = logging.getLogger(__name__)

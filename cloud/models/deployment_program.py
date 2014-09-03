import logging
from django.db import models
from cloud.models.program import Program

class DeploymentProgram(Program):

    class DeploymentProgramException(Program.ProgramException):
        # Alter logger to use this file name instead
        logger = logging.getLogger(__name__)

import logging
from django.db import models
from manager.models.program import Program

class DeploymentProgram(Program):

    class DeploymentProgramException(Program.ProgramException):
        # Alter logger to use this file name instead
        logger = logging.getLogger(__name__)

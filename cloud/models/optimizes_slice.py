import logging
from django.db import models
from cloud.models.base_model import BaseModel
from cloud.models.optimization_program import OptimizationProgram
from cloud.models.slice import Slice

class OptimizesSlice(BaseModel):

    priority = models.IntegerField()

    slice = models.ForeignKey("Slice")
    program = models.ForeignKey("OptimizationProgram")

    class OptimizesSliceException(BaseModel.ModelException):
        # Alter logger to use this file name instead
       logger = logging.getLogger(__name__)


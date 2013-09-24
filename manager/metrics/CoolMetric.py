# This is only a test file
import logging
import random
from manager.metrics.metric import Metric

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the Metric class to inherit basic functionalities
class CoolMetric(Metric):

    # Implementation of deployment method
    def collect(self):
        #logger.debug("Metric colleting invoked")
        return 0
        #return random.random()

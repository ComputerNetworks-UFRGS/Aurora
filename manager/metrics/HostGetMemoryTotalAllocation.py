# This is only a test file
import logging
from manager.metrics.metric import Metric
from manager.models.host import Host

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the Metric class to inherit basic functionalities
class HostGetMemoryTotalAllocation(Metric):

    # Implementation of deployment method
    def collect(self, host_name=None):
        try:
            h = Host.objects.get(hostname=host_name)
            return h.get_memory_allocation()['total'] / 1024
        except Host.DoesNotExist:
            raise self.MetricException('No Host with name %s' % host_name)
        except Host.HostException as e:
            raise self.MetricException('Error: %s' % str(e))

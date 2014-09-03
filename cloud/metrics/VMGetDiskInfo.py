# This is only a test file
import logging
import random
from cloud.metrics.metric import Metric
from cloud.models.virtual_machine import VirtualMachine

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the Metric class to inherit basic functionalities
class VMGetDiskInfo(Metric):

    # Implementation of deployment method
    def collect(self, vm_name=None):
        try:
            vm = VirtualMachine.objects.get(name=vm_name)
        except VirtualMachine.DoesNotExist:
            raise self.MetricException('No VM with name %s' % vm_name)
        return vm.get_disk_info()

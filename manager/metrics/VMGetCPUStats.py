# This is only a test file
import logging
import random
from manager.metrics.metric import Metric
from manager.models.virtual_machine import VirtualMachine

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the Metric class to inherit basic functionalities
class VMGetCPUStats(Metric):

    # Implementation of deployment method
    def collect(self, vm_name=None):
        try:
            vm = VirtualMachine.objects.get(name=vm_name)
            return vm.get_cpu_stats()
        except VirtualMachine.DoesNotExist:
            raise self.MetricException('No VM with name %s' % vm_name)
        except VirtualMachine.VirtualMachineException as e:
            raise self.MetricException('Error: %s' % str(e))

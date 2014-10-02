# This is only a test file
import logging
import random
from cloud.metrics.metric import Metric
from cloud.models.virtual_machine import VirtualMachine

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the Metric class to inherit basic functionalities
class VMGetCPUStatsPercentage(Metric):

    # Implementation of deployment method
    def collect(self, vm_name=None):
        try:
            vm = VirtualMachine.objects.get(name=vm_name)
            stats = vm.get_cpu_stats()
            stats[0]['system_time'] = float(stats[0]['system_time'])/stats[0]['cpu_time']
            stats[0]['user_time'] = float(stats[0]['user_time'])/stats[0]['cpu_time']
            stats[0]['cpu_time'] = 1.0
            return stats
        except VirtualMachine.DoesNotExist:
            raise self.MetricException('No VM with name %s' % vm_name)
        except VirtualMachine.VirtualMachineException as e:
            raise self.MetricException('Error: %s' % str(e))
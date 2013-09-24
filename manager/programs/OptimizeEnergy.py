# This is only a test file
import logging
from manager.programs.optimization_program import OptimizationProgram
import time
from manager.models.host import Host
from random import randint
from manager.models.base_model import BaseModel
from manager.models.virtual_machine import VirtualMachine
from manager.models.virtual_router import VirtualRouter

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the OptimizationProgram class to inherit basic functionalities
class OptimizeEnergy(OptimizationProgram):
    # Implementation of optimization method
    def optimize(self):
        logger.debug("OptimizeEnergy program invoked")

        # Get all available hosts
        hs = Host.objects.all()

        #logger.debug("hs %s" % str(hs))
        if len(hs) < 1:
            raise self.OptimizationException('No hosts available')

        # List of VMs
        vms = VirtualMachine.objects.all()

        # Reorganize VMs
        for vm in vms:  
            # Skip not deployed VMs
            if vm.current_state() != "running":
                continue

            #logger.debug("Checking VM: %s" % vm.name)
            # Choose host with the lowest residual capacity
            h = self.pick_lowest_residual_capacity_host(hs,vm.memory)

            # Migrate VM if needed
            if h != None and h != vm.host:
                logger.debug("Migrate VM %s (%s -> %s)" % (vm.name, vm.host.name, h.name))
                try:
                    vm.migrate(h)
                except BaseModel.ModelException as e:
                    raise self.OptimizationException('Unable to migrate VM ' + str(vm) + ': ' + str(e))
            #else: 
            #    logger.debug("Do not migrate VM") 

        return True

    def pick_lowest_residual_capacity_host(self, host_list, requested_mem):
        lowest_residual_capacity = float('inf')
        requested_mem = requested_mem/1024
        # Init new candidate
        new_candidate = None
        for candidate in host_list:
            capacity = candidate.get_info()
            mem_allocation = candidate.get_memory_allocation()
            #cpu_allocation = candidate.get_cpu_allocation()
            free_mem_capacity = capacity['memory'] - (mem_allocation['total'] / 1024) - requested_mem
            #logger.debug("Candidate %s: total %d - %d - %d = %d | Lowest: %s (%s)" % (candidate, capacity['memory'], (mem_allocation['total'] / 1024), requested_mem, free_mem_capacity, str(lowest_residual_capacity), str(free_mem_capacity < lowest_residual_capacity and free_mem_capacity >= requested_mem)))
            if free_mem_capacity < lowest_residual_capacity and free_mem_capacity >= requested_mem:
                lowest_residual_capacity = free_mem_capacity
                new_candidate = candidate
	
        return new_candidate


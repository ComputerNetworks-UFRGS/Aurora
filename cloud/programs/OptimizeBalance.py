import logging
import time
from cloud.programs.optimization_program import OptimizationProgram
from cloud.models.host import Host
from cloud.models.base_model import BaseModel
from cloud.models.virtual_machine import VirtualMachine

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the OptimizationProgram class to inherit basic functionalities
class OptimizeBalance(OptimizationProgram):

    # Implementation of optimization method
    def optimize(self):
        logger.info("## Program OptimizeBalance started")

        # Get all available hosts
        hs = Host.objects.all()

        #logger.debug("hs %s" % str(hs))
        if len(hs) < 1:
            raise self.OptimizationException('No hosts available')

        # List of VMs
        vms = VirtualMachine.objects.all()

        # Reorganize VMs
        migrations = 0
        for vm in vms:
            # Skip not deployed VMs
            if vm.current_state() != "running":
                continue
 
            #logger.debug("Checking VM: %s" % vm.name)
            # Choose host with the highest residual capacity
            h = self.pick_highest_residual_capacity_host(hs, vm)

            # Migrate VM if needed
            if h != None and h != vm.host:
                logger.info("Migrate VM %s (%s -> %s)" % (vm.name, vm.host.name, h.name))
                try:
                    vm.migrate(h)
                    migrations += 1
                except BaseModel.ModelException as e:
                    raise self.OptimizationException('Unable to migrate VM ' + str(vm) + ': ' + str(e))
            else:
                logger.debug("Do not migrate VM %s" % str(vm))
                
        logger.info("Total number of migrations: %d" % migrations)

        return True

    def pick_highest_residual_capacity_host(self, host_list, vm):
        requested_mem = vm.memory

        # Divide the total memory of a host because this is an emulated datacenter
        mem_capacity = vm.host.get_memory_stats()['total'] / 32 # len(host_list) Hard-coded so that the total memory of a host doesnt change
        mem_allocation = vm.host.get_memory_allocation()['total']
        # Initial highest residual capacity is the capacity of the origin host (considering that VM will be migrated)
        highest_residual_capacity = mem_capacity - mem_allocation + requested_mem

        # Init new candidate
        new_candidate = None
        for candidate in host_list:
            # Divide the total memory of a host because this is an emulated datacenter
            mem_capacity = candidate.get_memory_stats()['total'] / 32 # len(host_list) Hard-coded so that the total memory of a host doesnt change
            mem_allocation = candidate.get_memory_allocation()['total']
            free_mem_capacity = mem_capacity - mem_allocation - requested_mem
            test1 = free_mem_capacity >= highest_residual_capacity
            test2 = free_mem_capacity >= 0
            logger.debug("Candidate %s: %d(total) - %d(alloc) - %d(req) = %d(resid) | Highest: %d (%s)" % (str(candidate), mem_capacity, mem_allocation, requested_mem, free_mem_capacity, highest_residual_capacity, str(test1) + ' and ' + str(test2)))
            if free_mem_capacity >= highest_residual_capacity and free_mem_capacity >= requested_mem:
                highest_residual_capacity = free_mem_capacity
                new_candidate = candidate

        return new_candidate

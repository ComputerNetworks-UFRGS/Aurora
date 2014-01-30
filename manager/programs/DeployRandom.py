import time
import logging
from manager.programs.deployment_program import DeploymentProgram
from manager.models.host import Host
from random import randint
from manager.models.base_model import BaseModel
from manager.models.virtual_machine import VirtualMachine
from manager.models.virtual_router import VirtualRouter

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the DeploymentProgram class to inherit basic functionalities
class DeployRandom(DeploymentProgram):

    # Implementation of deployment method
    def deploy(self, slice_obj):

        # Record partial deployment times
        t0 = time.time()
        # Gets all available hosts
        hs = Host.objects.all()
        if len(hs) < 1:
            raise self.DeploymentException('No hosts available for deployment')

        # List of VMs to deploy
        vms = VirtualMachine.objects.filter(belongs_to_slice=slice_obj)

        # List of Links to deploy
        links = slice_obj.virtuallink_set.all()

        # Information gathering time
        gather_info_time = time.time() - t0
        logger.debug("Information gathering time: %s s" % str(round(gather_info_time, 2)))

        total_copy_time = 0
        total_define_time = 0

        # Create VMs
        for vm in vms:
            # Deploy on random host with enough resources
            h = self.pick_good_host(hs, vm.memory)

            vm.host = h

            # Deploy each VM individually
            try:
                stats = vm.deploy()
                total_copy_time += stats["copy_time"]
                total_define_time += stats["define_time"]

            except BaseModel.ModelException as e:
                raise self.DeploymentException('Unable to deploy VM ' + str(vm) + ': ' + str(e))

            # Save VM to update host information
            vm.save()

        logger.debug("Total image copy time: %s s" % str(round(total_copy_time, 2)))
        logger.debug("Total VM define time: %s s" % str(round(total_define_time, 2)))

        # Start VMs
        t0 = time.time()
        for vm in vms:
            # If deployed, then start
            try:
                vm.start()
            except BaseModel.ModelException as e:
                raise self.DeploymentException('Unable to start VM ' + str(vm) + ': ' + str(e))

        total_start_time = time.time() - t0
        logger.debug("Total VM start time: %s s" % str(round(total_start_time, 2)))

        total_define_time = 0

        # Whait so the controller recognizes the VMs (workarround)
        time.sleep(5)

        # Create Links
        t0 = time.time()
        max_retries = 20
        retry = 0
        for link in links:
            logger.debug("Establishing link: %s" % str(link))
            while retry <= max_retries:
                try:
                    logger.debug("Establish Try: %d" % retry)
                    link.establish()
                    retry = 0
                    break
                except link.VirtualLinkException as e:
                    logger.debug("Establish exception: %d" % retry)
                    retry += 1
                    time.sleep(5)
                    if retry == max_retries:
                        raise self.DeploymentException('Unable establish links: ' + str(e))

        total_establish_time = time.time() - t0

        logger.debug("Total link establishment time: %s s" % str(round(total_establish_time, 2)))

        return True

    # Returns a nice random host from the list
    def pick_good_host(self, host_list, requested_mem):
        requested_mem = requested_mem/1024
        find_resource = True
        tries = 0
        while find_resource and tries < 10:
            tries += 1
            pos = randint(0, len(host_list)-1)
            candidate = host_list[pos]
            capacity = candidate.get_info()
            mem_allocation = candidate.get_memory_allocation()
            #cpu_allocation = candidate.get_cpu_allocation()
            free_mem_capacity = capacity['memory'] - (mem_allocation['total'] / 1024) - requested_mem
            if free_mem_capacity > 0:
                find_resource = False
        
        return candidate


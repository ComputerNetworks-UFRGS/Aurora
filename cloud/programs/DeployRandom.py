import time
import logging

from random import shuffle

from cloud.programs.deployment_program import DeploymentProgram
from cloud.models.host import Host
from cloud.models.base_model import BaseModel
from cloud.models.virtual_machine import VirtualMachine
from cloud.models.virtual_link import VirtualLink
from cloud.models.virtual_router import VirtualRouter

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the DeploymentProgram class to inherit basic functionalities
class DeployRandom(DeploymentProgram):

    # Implementation of deployment method
    def deploy(self, slice_obj):
        logger.info("### Program DeployRandom started deploying: %s" % slice_obj.name)

        # Record partial deployment times
        t0 = time.time()
        # Gets all available hosts
        hs = Host.objects.all()
        if len(hs) < 1:
            raise self.DeploymentException('No hosts available for deployment')

        # List of VMs to deploy
        vms = VirtualMachine.objects.filter(belongs_to_slice=slice_obj)

        # List of Links to deploy
        links = VirtualLink.objects.filter(belongs_to_slice=slice_obj)

        # List of Routers to deploy
        # TODO: This program does not deploy Virtual Routers, do it later
        routers = VirtualRouter.objects.filter(belongs_to_slice=slice_obj)

        # Information gathering time
        gather_info_time = time.time() - t0
        logger.info("Information gathering time: %.3f" % gather_info_time)

        total_copy_time = 0
        total_define_time = 0
        total_reason_time = 0

        # Create VMs
        for vm in vms:
            # Deploy on random host with enough resources
            t0 = time.time()
            h = self.pick_good_host(hs, vm.memory)
            reason_time = time.time() - t0
            total_reason_time += reason_time
            logger.info("Reasoning time: %.3f" % reason_time)

            if h is None:
                raise self.DeploymentException('No hosts with the resources available for deployment')

            vm.host = h

            # Deploy each VM
            try:
                stats = vm.deploy()
                total_copy_time += stats["copy_time"]
                total_define_time += stats["define_time"]
                logger.info("Image copy time: %.3f" % stats["copy_time"])
                logger.info("VM define time: %.3f" % stats["define_time"])

            except BaseModel.ModelException as e:
                raise self.DeploymentException('Unable to deploy VM ' + str(vm) + ': ' + str(e))

            # Save VM to update host information
            vm.save()

        # Start VMs
        t0 = time.time()
        for vm in vms:
            try:
                t1 = time.time()
                vm.start()
                start_time = time.time() - t1
                logger.info("VM start time: %.3f" % start_time)
            except BaseModel.ModelException as e:
                raise self.DeploymentException('Unable to start VM ' + str(vm) + ': ' + str(e))

        total_start_time = time.time() - t0

        logger.info("Total image copy time: %.3f" % total_copy_time)
        logger.info("Total VM define time: %.3f" % total_define_time)
        logger.info("Total VM start time: %.3f" % total_start_time)
        logger.info("Total reasoning time: %.3f" % total_reason_time)

        total_define_time = 0

        # Whait so the controller recognizes the VMs (workarround)
        time.sleep(5)

        # Create Links
        t0 = time.time()
        for link in links:
            t1 = time.time()
            link.establish()
            establish_time = time.time() - t1
            logger.info("Link establishment time: %.3f" % establish_time)

        total_establish_time = time.time() - t0

        logger.info("Total link establishment time: %.3f" % total_establish_time)

        return True

    # Returns a nice random host from the list
    def pick_good_host(self, host_list, requested_mem):
        requested_mem = requested_mem
        r_list = range(len(host_list)) # Generate a random list of numbers
        shuffle(r_list)
        for i in r_list:
            candidate = host_list[i]
            # Memory
            mem_capacity = candidate.get_memory_stats()['total'] / len(host_list) # Divide the total memory of a host because this is an emulated datacenter
            mem_allocation = candidate.get_memory_allocation()['total']
            # CPU
            # cpu_capacity = candidate.get_info()['cores'] / len(host_list)
            # cpu_allocation = candidate.get_cpu_allocation()
            free_mem_capacity = mem_capacity - mem_allocation - requested_mem
            if free_mem_capacity > 0:
                logger.debug("Found candidate %s with %d residual capacity" % ( str(candidate), free_mem_capacity ))
                return candidate

        # No candidate found
        return None

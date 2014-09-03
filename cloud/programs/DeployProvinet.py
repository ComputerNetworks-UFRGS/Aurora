import time
import logging
from cloud.programs.deployment_program import DeploymentProgram
from cloud.models.host import Host
from random import randint
from cloud.models.base_model import BaseModel
from cloud.models.virtual_machine import VirtualMachine
from cloud.models.virtual_router import VirtualRouter

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the DeploymentProgram class to inherit basic functionalities
class DeployProvinet(DeploymentProgram):

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

        # List of VRs to deploy
        vrs = VirtualRouter.objects.filter(belongs_to_slice=slice_obj)

        # List of Links to deploy
        links = slice_obj.virtuallink_set.all()

        # Information gathering time
        gather_info_time = time.time() - t0
        logger.debug("Information gathering time: %s s" % str(round(gather_info_time, 2)))

        total_copy_time = 0
        total_define_time = 0

        # Everything is deployed into a single host
        h = self.pick_good_host(hs)

        # Create VMs
        for vm in vms:
            # Deploy always in the same host
            vm.host = h

            # Deploy each VM individually
            try:
                stats = vm.deploy()
                total_copy_time += stats["copy_time"]
                total_define_time += stats["define_time"]

            except BaseModel.ModelException as e:
                raise self.DeploymentException('Unable to deploy VM ' + str(vm) + ': ' + str(e))

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

        # Create VRs
        for vr in vrs:
            # Deploy always in the same host
            vr.host = h

            # Deploy each VM individually
            try:
                stats = vr.deploy()
                total_define_time += stats["define_time"]

            except BaseModel.ModelException as e:
                raise self.DeploymentException('Unable to deploy Virtual Router ' + str(vr) + ': ' + str(e))

            # Save Virtual Router to update host information
            vr.save()

        logger.debug("Total Virtual Router define time: %s s" % str(round(total_define_time, 2)))

        # Create Links
        t0 = time.time()
        try:
            for link in links:
                link.establish()
        except link.VirtualLinkException as e:
            raise self.DeploymentException('Unable establish links: ' + str(e))

        total_establish_time = time.time() - t0

        logger.debug("Total link establishment time: %s s" % str(round(total_establish_time, 2)))

        return True

    # Returns a nice random host from the list
    def pick_good_host(self, host_list):
        pos = randint(0, len(host_list)-1)
        return host_list[pos]
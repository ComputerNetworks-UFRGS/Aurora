# Simple balanced deployment program
import time
import logging

from random import randint

from cloud.programs.deployment_program import DeploymentProgram
from cloud.models.host import Host
from cloud.models.switch import Switch
from cloud.models.base_model import BaseModel
from cloud.models.virtual_link import VirtualLink
from cloud.models.virtual_machine import VirtualMachine
from cloud.models.virtual_router import VirtualRouter

# Configure logging for the module name
logger = logging.getLogger(__name__)

class DeployBalanced(DeploymentProgram):

    # Implementation of deployment method
    def deploy(self, slice_obj):
        logger.info("### Program DeployBalanced Started deploying: %s" % slice_obj.name)

        # Record partial deployment times
        t0 = time.time()
        t_initial = t0
        # Gets all available hosts for VM deployment
        hs = Host.objects.all()
        if len(hs) < 1:
            raise self.DeploymentException('No hosts available for deployment')

        # List of VMs to deploy
        vms = VirtualMachine.objects.filter(belongs_to_slice=slice_obj)
        if len(vms) < 1:
            raise self.DeploymentException('No virtual machines in the slice')

        # List of Links to deploy
        links = VirtualLink.objects.filter(belongs_to_slice=slice_obj)

        # List of Routers to deploy
        # TODO: This program does not deploy Virtual Routers, do it later
        routers = VirtualRouter.objects.filter(belongs_to_slice=slice_obj)

        # If virtual links will be deployed we need to prepare pairs
        if len(links) > 0:
            # Prepare deployment pairs of VMs. This assumes all VMs are connected by links.
            deployment_pairs = []
            for link in links:
                # Copy the VM objects from the VM list to avoid duplication
                pair = [None, None]
                for vm in vms:
                    if vm.name == link.if_start.attached_to.name:
                        pair[0] = vm
                    elif vm.name == link.if_end.attached_to.name:
                        pair[1] = vm

                deployment_pairs.append(pair)

            # Calculates here the distance to all hosts
            host_hops = {}
            for h in hs:
                host_hops[h.name] = self.calculate_distances(h, hs)
                logger.debug("Hop count for %s is: %s " % (h.name, str(host_hops[h.name])))

        else:
            # Deployment will be done in pairs anyway
            deployment_pairs = []
            i = 0
            for vm in vms:
                deployment_pairs[i/2][i%2] = vm
                i+=1

            # If the number of VMs is odd fill the last pair with the first VM again
            if len(vms)%2 != 0:
                deployment_pairs[len(deployment_pairs)-1][1] = vms[0]

            # Distances are not important if there are no links to deploy
            host_hops = None

        # Information gathering time
        gather_info_time = time.time() - t0
        logger.info("Information gathering time: %.3f" % gather_info_time)

        # Reasoning part: decides where to place pairs of VMs based on the links between them
        # Reasoning Time
        t0 = time.time()
        for pair in deployment_pairs:
            t1 = time.time()
            logger.debug("Pair information <vm1: %s, vm2: %s> " % (pair[0], pair[1]))
            logger.debug("Pair information <host1: %s, host2: %s> " % (pair[0].host, pair[1].host))

            # If both VMs are deployed already, ignore this pair
            if pair[0].host is not None and pair[1].host is not None:
                continue

            # Calculates the allocation and sets a host to VMs depending on whether one of them has already a been placed
            if pair[1].host == None:
                logger.debug("Deploying pair <pivot: %s, free: %s> " % (pair[0], pair[1]))
                self.calculate_allocation_pair(pair[0], pair[1], hs, host_hops)
                logger.debug("Now VMs <pivot: %s, free: %s> are allocated to hosts <%s, %s>" % (pair[0], pair[1], pair[0].host, pair[1].host))
            else:
                logger.debug("Deploying pair inverted <pivot: %s, free: %s> " % (pair[1], pair[0]))
                self.calculate_allocation_pair(pair[1], pair[0], hs, host_hops)
                logger.debug("Now VMs <pivot: %s, free: %s> are allocated to hosts <%s, %s>" % (pair[1], pair[0], pair[1].host, pair[0].host))

            reason_time = time.time() - t1
            logger.info("Reasoning time: %.3f" % reason_time)

        total_reason_time = time.time() - t0

        total_copy_time = 0
        total_define_time = 0
        total_start_time = 0
        # Create VMs
        for vm in vms:
            # Deploy each VM individually
            try:
                stats = vm.deploy()
                total_copy_time += stats["copy_time"]
                total_define_time += stats["define_time"]
                logger.info("Image copy time: %.3f" % stats["copy_time"])
                logger.info("VM define time: %.3f" % stats["define_time"])

            except BaseModel.ModelException as e:
                raise self.DeploymentException('Unable to deploy VM ' + str(vm) + ': ' + str(e))

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

        # Create Links
        t0 = time.time()
        for link in links:
            t1 = time.time()
            link.establish()
            establish_time = time.time() - t1
            logger.info("Link establishment time: %.3f" % establish_time)

        total_establish_time = time.time() - t0

        logger.info("Total link establishment time: %.3f" % total_establish_time)
        
        total_time = time.time() - t_initial
        logger.info("Total slice deployment time: %.3f" % total_time)
        return True

    # Calculates the allocation of a pair of VMs
    def calculate_allocation_pair(self, vm_pivot, vm_free, hosts, host_hops):
        # If the pivot is not set, we first place it somewhere
        if vm_pivot.host == None:
            logger.debug("Allocating VM %s as pivot" % vm_pivot)
            self.allocate_vm(vm_pivot, hosts)

        logger.debug("Allocating VM %s considering the pivot %s" % (vm_free, vm_pivot))
        self.allocate_vm(vm_free, hosts, host_hops, vm_pivot)

    # Allocates a VMs to a Host. If pivot is true it will not consider network.
    def allocate_vm(self, vm, hosts, host_hops=None, pivot=None):

        # Hosts that can hold this VMs
        candidate_hosts = []
        for host in hosts:
            # Host must be active
            cs = host.current_state()
            if cs != "Active":
                continue

            # Checks current allocation of memory and CPU
            mem_allocation = host.get_memory_allocation()['total']
            cpu_allocation = host.get_cpu_allocation()['total']
            
            # Divide the total capacity of a host because this is an emulated datacenter
            mem_total = host.get_memory_stats()['total'] / len(hosts) 
            cpu_total = host.get_info()['cores'] / len(hosts) * 8 # Overprovision a bit ;)

            # Host must have enough memory
            mem_free = mem_total - mem_allocation 
            if mem_free < vm.memory:
                continue

            # Host must have enough cpus
            cpu_free = cpu_total - cpu_allocation
            if cpu_free < vm.vcpu:
                continue

            #TODO: Check for disk space
            candidate_host = {
                "object": host,
                "coefficient": self.resource_allocation_coefficient(cpu_free, cpu_total, mem_free, mem_total)
            }

            # Consider the network location also if this is not the pivot. Update coefficient.
            if pivot != None:
                if host_hops[pivot.host.name].has_key(candidate_host["object"].name):
                    # Hops are always greater or equals to one
                    hops = host_hops[pivot.host.name][candidate_host["object"].name]
                else:
                    # Set a very high hop count so this host will probably not be a good candidate
                    hops = 42
                    logger.warning("Host %s is not reachable from %s. This should not happen!" % (candidate_host["object"].name, pivot.host.name))
                candidate_host["coefficient"] = candidate_host["coefficient"] / hops

            candidate_hosts.append(candidate_host)

        # There should be at least one host that can provide the resources for this VM
        if len(candidate_hosts) == 0:
            raise self.DeploymentException('No host has the resources needed for VM: ' + vm.name)

        logger.debug("Candidate hosts are: %s" % str(candidate_hosts))

        # Find the host(s) with the best coefficient
        best_coefficient = 0
        for h in candidate_hosts:
            if h["coefficient"] > best_coefficient:
                best_coefficient = h["coefficient"]

        selected_hosts = []
        for h in candidate_hosts:
            if h["coefficient"] == best_coefficient:
                selected_hosts.append(h)

        logger.debug("Selected hosts are: %s" % str(selected_hosts))

        # There might still be more than one candidate in the case they have the same amount of free resources and same hop count
        if len(selected_hosts) > 1:
            final_host = self.pick_good_host(selected_hosts)
        else:
            final_host = selected_hosts[0]

        logger.debug("Host %s was selected for %s" % (final_host["object"], vm))

        # Save VM to update host information
        vm.host = final_host["object"]
        vm.save()

    # Calculates a fuzzy resource allocation coefficient. The smaller the coefficient less resources are left
    def resource_allocation_coefficient(self, free_cpu, total_cpu, free_memory, total_memory):
        return (float(free_cpu) / total_cpu) * (float(free_memory) / total_memory)

    # Returns a nice random host from the list
    def pick_good_host(self, host_list):
        pos = randint(0, len(host_list)-1)
        return host_list[pos]

    def calculate_distances(self, host, hosts):
        # Find this host in the topology
        output = {}
        for h in hosts:
            if h == host: # Own host, distance equals 1
                distance = 1
            else:
                path = host.path_to(h)
                if path is None:
                    distance = 42 # Invalid distance
                else:
                    distance = len(path) / 2 # Path describes in and out ports for every hop

            output[h.name] = distance

        return output

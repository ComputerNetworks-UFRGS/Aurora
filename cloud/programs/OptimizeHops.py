# Minimize distance between linked virtual machines
import time
import logging
from random import randint
from cloud.programs.optimization_program import OptimizationProgram
from cloud.models.host import Host
from cloud.models.switch import Switch
from cloud.models.base_model import BaseModel
from cloud.models.virtual_link import VirtualLink
from cloud.models.virtual_machine import VirtualMachine

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the OptimizationProgram class to inherit basic functionalities
class OptimizeHops(OptimizationProgram):
    
    # Implementation of optimization method
    def optimize(self):
        logger.info("## Program OptimizeHops started")
        
        # Get all available hosts
        hs = Host.objects.all()
        
        #logger.debug("hs %s" % str(hs))
        if len(hs) < 1:
            raise self.OptimizationException('No hosts available')
        
        # List of Links 
        links = VirtualLink.objects.all()

        # If there are virtual links try to optimize them
        if len(links) > 0:
            # Calculates here the distance to all hosts
            host_hops = {}
            for h in hs:
                host_hops[h.name] = self.calculate_distances(h, hs)
                logger.debug("Hop count for %s is: %s " % (h.name, str(host_hops[h.name])))

            # Prepare optimization pairs of VMs. This assumes all VMs are connected by links.
            optimization_pairs = []
            for link in links:
                # Copy the VM objects from the VM list to avoid duplication
                pair = {}
                # Checks if link connect two VMs
                if link.if_start.attached_to.is_virtual_machine() and link.if_end.attached_to.is_virtual_machine():
                    pair['start'] = link.if_start.attached_to.virtualmachine
                    pair['end'] = link.if_end.attached_to.virtualmachine
                    pair['distance'] = host_hops[pair['start'].host.name][pair['end'].host.name] # Assume fully connected infrastructure
                    # Only tries to optimize when the pair is not already on the same host
                    if pair['distance'] > 1:
                        optimization_pairs.append(pair)

            # Sort pairs by distance to start with farthest ones
            optimization_pairs = sorted(optimization_pairs, key=lambda k: k['distance'])
            optimization_pairs.reverse()

            logger.debug("Optimization pairs (%d): %s" % (len(optimization_pairs), str(optimization_pairs)))
        else:
            logger.debug("No links to optimize")
            return True

        # Reasoning part: decides where to place pairs of VMs based on the links between them
        migrated = []
        pivots = []
        migrations = 0
        for pair in optimization_pairs:

            # Refresh objects with database values (in case VMs were already migrated in other links)
            pair['start'] = VirtualMachine.objects.get(id=pair['start'].id)
            pair['end'] = VirtualMachine.objects.get(id=pair['end'].id)
            pair['distance'] = host_hops[pair['start'].host.name][pair['end'].host.name] # Assume fully connected infrastructure

            # Skip VMs not running
            if pair['start'].current_state() != "running" or pair['end'].current_state() != "running":
                continue

            # The pivot is the VM with more links (minimize migrations)
            connected_pair0 = 0
            for interface in pair['start'].virtualinterface_set.all():
                connected_pair0 += len(interface.connected_virtual_devices())

            connected_pair1 = 0
            for interface in pair['end'].virtualinterface_set.all():
                connected_pair1 += len(interface.connected_virtual_devices())

            # TODO: Randomize pivot in case number of connections is the same
            if connected_pair0 > connected_pair1:
                pivot = pair['start']
                free = pair['end']
            else:
                pivot = pair['end']
                free = pair['start']

            # Don't migrate a VM twice nor migrate previous pivots
            if free.name in migrated or free.name in pivots:
                logger.debug("Skiping <pivot: %s (%s), free: %s (%s), distance: %d> " % (pivot, pivot.host.hostname, free, free.host.hostname, pair['distance']))
                continue

            logger.debug("Optimizing <pivot: %s (%s), free: %s (%s), distance: %d> " % (pivot, pivot.host.hostname, free, free.host.hostname, pair['distance']))
            hosts = self.find_host_list(pivot, free, hs, host_hops)

            # Try to find a host from the list that will make the sum of link distances smaller
            original_distances = 0
            original_longest_link = 0
            for interface in free.virtualinterface_set.all():
                for device in interface.connected_virtual_devices():
                    if device.is_virtual_machine():
                        # Assume fully connected infrastructure
                        link_length = host_hops[free.host.name][device.virtualmachine.host.name]
                        if link_length > original_longest_link:
                            original_longest_link = link_length
                        original_distances += host_hops[free.host.name][device.virtualmachine.host.name]
                    else:
                        original_distances = -1 # Something weird is connected here... better not migrate

            # Connected to something that is not a VM (this should not happen)
            if original_distances < 0:
                logger.warning("Cannot handle <pivot: %s (%s), free: %s (%s), distance: %d> (Not a VM)" % (pivot, pivot.host.hostname, free, free.host.hostname, pair['distance']))
                continue

            # Find a host from the candidate list that can improve the original distance
            best_distances = original_distances
            best_host = free.host
            best_longest_link = original_longest_link
            for h in hosts:
                distances = 0
                longest_link = 0
                for interface in free.virtualinterface_set.all():
                    for device in interface.connected_virtual_devices():
                        if device.is_virtual_machine():
                            # Assume fully connected infrastructure
                            link_length = host_hops[h.name][device.virtualmachine.host.name]
                            if link_length > longest_link:
                                longest_link = link_length
                            distances += host_hops[h.name][device.virtualmachine.host.name]

                if distances < best_distances or (distances == best_distances and longest_link < best_longest_link):
                    best_distances = distances
                    best_longest_link = longest_link
                    best_host = h

            # Decision to migrate takes into account:
            # (i) first the overall sum of distances, and 
            # (ii) then the length of the longest link
            if best_distances < original_distances or (best_distances == original_distances and best_longest_link < original_longest_link):
                logger.info("Migrate VM %s (%s -> %s) - Distances: (Orig %d:%d, Best: %d:%d)" % (free.name, free.host.name, best_host.name, original_distances, original_longest_link, best_distances, best_longest_link))
                try:
                    free.migrate(best_host)
                    migrated.append(free.name)
                    pivots.append(pivot.name)
                    migrations += 1
                except BaseModel.ModelException as e:
                    raise self.OptimizationException('Unable to migrate VM ' + str(vm) + ': ' + str(e))
            else:
                logger.debug("Decided not to migrate VM %s at %s - Distances: (Orig %d:%d, Best: %d:%d)" % (free.name, free.host.name, original_distances, original_longest_link, best_distances, best_longest_link))
        logger.info("Total number of migrations: %d" % migrations)
        return True
    
    # Calculates the allocation of a pair of VMs
    def find_host_list(self, vm_pivot, vm_free, hosts, host_hops):
        # Hosts that can hold this VMs
        candidate_hosts = []
        for host in hosts:
            # Host must be active
            cs = host.current_state()
            if cs != "Active":
                continue
            # The original host of VM free should not be on the list
            if host.name == vm_free.host.name:
                continue
            # Checks current allocation of memory and CPU 
            mem_allocation = host.get_memory_allocation()['total']
            mem_total = host.get_memory_stats()['total'] / 32 # len(host_list) Hard-coded so that the total memory of a host doesnt change
            
            # Host must have enough memory
            mem_free = mem_total - mem_allocation
            if mem_free < vm_free.memory:
                continue
            
            candidate_host = {
                'object': host,
                'distance': host_hops[vm_pivot.host.name][host.name],
                'mem_free': mem_free
            }
            
            candidate_hosts.append(candidate_host)

        # There should be at least one host that can provide the resources for this VM
        if len(candidate_hosts) == 0:
            logger.debug('No host has the resources needed for VM: ' + vm_free.name)
            return []

        # Reorder candidates by distance
        candidate_hosts = sorted(candidate_hosts, key=lambda k: k['distance'])

        logger.debug("Candidate hosts are: %s" % str(candidate_hosts))

        # The final list returned contains only the host objects
        final_list = []
        for candidate in candidate_hosts:
            final_list.append(candidate['object'])
        return final_list

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

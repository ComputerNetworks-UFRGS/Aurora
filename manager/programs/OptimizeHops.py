# Minimize distance between linked virtual machines
import time
import logging
from manager.programs.optimization_program import OptimizationProgram
from manager.models.host import Host
from manager.models.switch import Switch
from manager.models.base_model import BaseModel
from manager.models.virtual_link import VirtualLink
from manager.models.virtual_machine import VirtualMachine
from random import randint

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Extends the OptimizationProgram class to inherit basic functionalities
class OptimizeHops(OptimizationProgram):
    
    # Implementation of optimization method
    def optimize(self):
        
        # Get all available hosts
        hs = Host.objects.all()
        
        #logger.debug("hs %s" % str(hs))
        if len(hs) < 1:
            raise self.OptimizationException('No hosts available')
        
        # List of Links 
        links = VirtualLink.objects.all()

        # If there are virtual links try to optimize them
        if len(links) > 0:
            # Gets all switches
            sw = Switch.objects.all()
            if len(sw) < 1:
                raise self.OptimizationException('No switches available for optimization')
            
            # Figure out the topology based on what is connected to every switch port
            topology = {}
            for s in sw:
                topology[s.name] = []
                for p in s.port_set.all():
                    topology[s.name] += p.connected_devices()
                    
            # Calculates here the distance to all hosts
            host_hops = {}
            for h in hs:
                host_hops[h.name] = self.calculate_distances(h, topology)
                #logger.debug("Hop count for %s is: %s " % (h.name, str(host_hops[h.name])))

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
                    if pair['distance'] > 0:
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
        for pair in optimization_pairs:

            # Refresh objects with database values (in case VMs were already migrated in other links)
            pair['start'] = VirtualMachine.objects.get(id=pair['start'].id)
            pair['end'] = VirtualMachine.objects.get(id=pair['end'].id)
            pair['distance'] = host_hops[pair['start'].host.name][pair['end'].host.name] # Assume fully connected infrastructure

            # Skip VMs not running or too close already
            if pair['start'].current_state() != "running" or pair['end'].current_state() != "running" or pair['distance'] < 1:
                continue

            # The pivot is the VM with less links (minimize migrations)
            connected_pair0 = 0
            for interface in pair['start'].virtualinterface_set.all():
                connected_pair0 += len(interface.connected_virtual_devices())

            connected_pair1 = 0
            for interface in pair['end'].virtualinterface_set.all():
                connected_pair1 += len(interface.connected_virtual_devices())

            if connected_pair0 > connected_pair1:
                pivot = pair['start']
                free = pair['end']
            else:
                pivot = pair['end']
                free = pair['start']

            # Dont migrate a VM twice nor migrate previous pivots
            if free.name in migrated or free.name in pivots:
                logger.debug("Skiping <pivot: %s (%s), free: %s (%s), distance: %d> " % (pivot, pivot.host.hostname, free, free.host.hostname, pair['distance']))
                continue

            logger.debug("Optimizing <pivot: %s (%s), free: %s (%s), distance: %d> " % (pivot, pivot.host.hostname, free, free.host.hostname, pair['distance']))
            hosts = self.find_host_list(pivot, free, hs, topology, host_hops)

            # The first host on the list that will not make distances of the free VM worst will be selected
            for h in hosts:
                worst_distance = 0
                # Skip migration if this will make this VM farther from other connected links
                for interface in free.virtualinterface_set.all():
                    for device in interface.connected_virtual_devices():
                        if device.is_virtual_machine() and device.virtualmachine.name != pivot.name:
                            new_distance = host_hops[h.name][device.virtualmachine.host.name] # Assume fully connected infrastructure
                            if new_distance > worst_distance:
                                worst_distance = new_distance

                if worst_distance >= pair['distance']:
                    logger.debug("Decided not to migrated VM %s (%s -> %s): worst distance %d" % (free.name, free.host.name, h.name, worst_distance))
                else:
                    logger.debug("Migrate VM %s (%s -> %s)" % (free.name, free.host.name, h.name))
                    try:
                        free.migrate(h)
                        migrated.append(free.name)
                        pivots.append(pivot.name)
                        break # Migrated, so stop searching for hosts
                    except BaseModel.ModelException as e:
                        raise self.OptimizationException('Unable to migrate VM ' + str(vm) + ': ' + str(e))
        return True
    
    # Calculates the allocation of a pair of VMs
    def find_host_list(self, vm_pivot, vm_free, hosts, topology, host_hops):
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
            info = host.get_info()
            mem_allocation = host.get_memory_allocation()
            mem_total = info['memory'] # in MB
            
            # Host must have enough memory
            mem_free = mem_total - (mem_allocation['total'] / 1024)
            if mem_free < vm_free.memory / 1024:
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

        # Find the host(s) with the best coefficient
        #best_distance = 42
        #best_memory = 0
        #best_host = None
        #for h in candidate_hosts:
        #    if h['distance'] < best_distance or (h['distance'] == best_distance and h['mem_free'] > best_memory):
        #        best_distance = h['distance']
        #        best_memory = h['mem_free']
        #        best_host = h['object']
        #
        ## Save VM to update host information
        #return best_host

    def calculate_distances(self, host, topology):
        # Find this host in the topology
        for sw in topology:
            for dev in topology[sw]:
                if isinstance(dev, Host) and host.name == dev.name:
                    connected_to_sw = sw
        
        # Calculate a list of other hosts and number of hops to them
        output = self.hop_count(connected_to_sw, topology, 1, [])
        # Hop count for itself is always zero
        output[host.name] = 0
        
        return output
        
    def hop_count(self, sw, topology, level, visited):
        # Accumulated output list of hops 
        output = {}

        # Avoid loops
        if sw in visited:
            return output # Empty output
        visited.append(sw)
        
        # Adds all hosts to the hop list
        for dev in topology[sw]:
            if isinstance(dev, Host):
                output[dev.name] = level
            elif isinstance(dev, Switch):
                output.update(self.hop_count(dev.name, topology, level+1, visited))
                
        return output
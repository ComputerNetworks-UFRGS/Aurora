# Run this script from the django shell:
#
# python manage.py shell
# from scripts.experiment_comnet2013 import Experiment
# e = Experiment()
# e.run()

import time
import math
import logging
from django.contrib.auth.models import User
from manager.models.slice import Slice
from manager.models.host import Host
from manager.models.switch import Switch
from manager.models.image import Image
from manager.models.virtual_machine import VirtualMachine
from manager.models.virtual_link import VirtualLink
from manager.models.virtual_interface import VirtualInterface
from manager.programs.DeployRandom import DeployRandom
from manager.programs.OptimizeBalance import OptimizeBalance
from manager.programs.OptimizeEnergy import OptimizeEnergy
from manager.programs.OptimizeHops import OptimizeHops

# Configure logging for the module name
logger = logging.getLogger(__name__)

class Experiment():
    iterations = 1
    vxdl_15 = "manager/templates/xml/vxdl_owrt_tree_15.xml"
    vxdl_7 = "manager/templates/xml/vxdl_owrt_tree_7.xml"
    vxdl_4 = "manager/templates/xml/vxdl_owrt_loop_4.xml"
    # Amount of slices to deploy initially
    init_setup = [vxdl_4, vxdl_4, vxdl_7, vxdl_7, vxdl_15, vxdl_15]
    program = None

    # Program is the string name of the program
    def run(self, program):
        
        logger.info("##### EXPERIMENT STARTING #####")
        begin_time = time.time()

        print "Running experiment for %i times" % self.iterations

        if program == "OptimizeBalance":
            self.program = OptimizeBalance()
        elif program == "OptimizeEnergy":
            self.program = OptimizeEnergy()
        elif program == "OptimizeHops":
            self.program = OptimizeHops()
        else:
            raise Exception("Invalid program: %s" % program)
            
        for i in range(self.iterations):
            
            # Undeploy all slices
            self.remove_slices()

            # Deploy initial load of slices
            self.create_initial_slices()
            
            # Run first optimization
            self.optimize()
            
            # Removes one slice
            s = Slice.objects.all()[0]
            self.remove_slice(s)
        
            # Run second optimization
            self.optimize()
            
            # Add VMs to slice
            s = Slice.objects.all()[0]
            vm = VirtualMachine.objects.filter(belongs_to_slice=s)[0]
            img = Image.objects.get(name="OpenWrt")
            newVM1 = self.add_vm("newVM1", 256*1024, 1, img, s)
            newVM2 = self.add_vm("newVM2", 256*1024, 1, img, s)
            self.add_link(vm, newVM1)
            self.add_link(vm, newVM2)

            # Run third optimization
            self.optimize()

            # Remove VMs
            vms = VirtualMachine.objects.all()
            
            vm = vms[5]
            self.remove_vm(vm)
            vm = vms[10]
            self.remove_vm(vm)
            vm = vms[15]
            self.remove_vm(vm)
            vm = vms[20]
            self.remove_vm(vm)
            
            # Run third optimization
            self.optimize()

            # Migrate VMs in host 10 to host another one with enough resources
            h10 = Host.objects.get(hostname="h10")
            print "Disabling host %s" % h10.name
            mem_allocation = h10.get_memory_allocation()["total"] / 1024
            hosts = Host.objects.all()
            for h in hosts:
                capacity = h.get_info()
                allocation = h.get_memory_allocation()
                free_mem_capacity = capacity['memory'] - (allocation['total'] / 1024)
                if free_mem_capacity > mem_allocation: 
                    vms = VirtualMachine.objects.filter(host=h10)
                    print "Migrate %d VMs to %s" % (len(vms), h.name)
                    for vm in vms:
                        vm.migrate(h)
                    break

            # Disable h10
            interface = h10.interface_set.all()[0]
            port = interface.port_set.all()[0]
            h10.delete()
            
            # Run fourth optimization
            self.optimize()

            # Recreate h10
            print "Enabling host %s again" % h10.name
            h10.save()
            interface.save()
            port.connected_interfaces.add(interface)

            # Run fifth optimization
            self.optimize()

        experiment_time = time.time() - begin_time
        logger.info("##### EXPERIMENT ENDED IN %s SECONDS #####" % str(round(experiment_time, 2)))

    def statistics(self):
        # Capacity statistics
        highest_residual_capacity = 0
        lowest_residual_capacity = float('inf')
        overall_capacity = 0
        overall_square = 0
        hosts = Host.objects.order_by("id")
        sample = []
        for candidate in hosts:
            capacity = candidate.get_info()
            mem_allocation = candidate.get_memory_allocation()
            free_mem_capacity = capacity['memory'] - (mem_allocation['total'] / 1024)

            overall_capacity += free_mem_capacity
            overall_square += free_mem_capacity*free_mem_capacity

            if free_mem_capacity > highest_residual_capacity:
                highest_residual_capacity = free_mem_capacity

            if free_mem_capacity < lowest_residual_capacity:
                lowest_residual_capacity = free_mem_capacity

            sample.append(int(free_mem_capacity))

        sample_size = len(hosts)
        mean = float(overall_capacity)/sample_size
        variance = (overall_square - float(overall_capacity*overall_capacity) / sample_size) / sample_size

        print "########## Allocation statistics:"
        print "Free memory sample: %s" % str(sample)
        print "Free memory: max %d, min %d, mean %s, variance %s, std dev %s" % (highest_residual_capacity, lowest_residual_capacity, str(mean), str(variance), str(math.sqrt(variance)))
        
        # Link distance statistics
        highest_distance = 0
        lowest_distance = float('inf')
        overall_distance = 0
        overall_square = 0
        sample = []
        links = VirtualLink.objects.order_by("id")
        host_hops = self.calculate_distances()
        for link in links:
            if link.if_start.attached_to.is_virtual_machine() and link.if_end.attached_to.is_virtual_machine():
                start = link.if_start.attached_to.virtualmachine
                end = link.if_end.attached_to.virtualmachine
                distance = host_hops[start.host.name][end.host.name] # Assume fully connected infrastructure
                overall_distance += distance
                overall_square += distance*distance

            if distance > highest_distance:
                highest_distance = distance

            if distance < lowest_distance:
                lowest_distance = distance

            sample.append(int(distance))

        print "########## Hop statistics:"
        sample_size = len(links)
        mean = float(overall_distance)/sample_size
        variance = (overall_square - float(overall_distance*overall_distance) / sample_size) / sample_size
        print "Distance sample: %s" % str(sample)
        print "Distance: max %d, min %d, mean %s, variance %s, std dev %s" % (highest_distance, lowest_distance, str(mean), str(variance), str(math.sqrt(variance)))

    def optimize(self):
        # Gather some statistics before optimization
        self.statistics()

        # Use optimizations here
        try:
            # Will record deployment time
            t0 = time.time()
            if self.program.optimize():
                optimization_time = time.time() - t0
                print "Optimization successfully executed  in %s seconds!" % str(round(optimization_time, 2))
        except self.program.OptimizationException as e:
            print "Problems optimizing: %s" % str(e)

        # Gather statistics again after optimization
        self.statistics()

    def create_initial_slices(self):
        i = 0

        # Deploy initial load of slices
        for vxdl_file in self.init_setup:
            i += 1
            f = open(vxdl_file, "r")
            vxdl = f.read()
            user = User.objects.all()[0] # Get any user, this really doesn't matter

            print "Creating slice %s" % vxdl_file

            s = Slice()
            s.owner = user
            s.name = "exp_" + str(i)
            try:
                s.save_from_vxdl(vxdl)
                print "Slice %s saved!" % s.name
            except Slice.VXDLException as e:
                raise Exception("Problems saving slice %s from VXDL!" % s.name)

            try:
                program = DeployRandom()
                # Will record deployment time
                t0 = time.time()
                if program.deploy(s):
                    deployment_time = time.time() - t0
                    s.state = "deployed"
                    s.save()
                    print "Slice %s successfully deployed in %s seconds!" % (s.name, str(round(deployment_time, 2)))
            except program.DeploymentException as e:
                raise Exception("Problems deploying slice %s: %s" % (s.name, str(e)))

    def remove_slices(self):

        # Undeploy initial load of slices
        slices = Slice.objects.all()
        for s in slices:
            self.remove_slice(s)

    def remove_slice(self, s):
        print "Deleting slice %s" % s

        # List of Links to delete 
        links = s.virtuallink_set.all()
        for link in links:
            try:
                link.unestablish()
            except link.VirtualLinkException as e:
                raise Exception("Problems unestablishing a virtual link: " + str(e))
        # List of VMs to delete 
        vms = VirtualMachine.objects.filter(belongs_to_slice=s)
        for vm in vms:
            try:
                vm.undeploy()
            except vm.VirtualMachineException as e:
                raise Exception("Problems undeploying a virtual machine: " + str(e))

        # No virtual routers will be created
        
        s.delete()

    def add_vm(self, name, memory, vcpu, img, slice):
    
        vm = VirtualMachine()
        vm.name = name
        vm.memory = memory
        vm.vcpu = vcpu
        vm.image = img
        vm.belongs_to_slice = slice
        
        # Choose a host (randomly)
        vm.host = Host.objects.order_by('?')[0]
        
        # Save Virtual Machine to get an ID
        vm.save()
        
        interface = VirtualInterface()
        interface.alias = "net0"
        interface.attached_to = vm
        interface.if_type = "bridge"
        interface.save()

        try:
            # Creates disk and defines Virtual Machine in libvirt
            vm.deploy()
            vm.start()
            print "New Virtual Machine successfully created"
        except vm.VirtualMachineException as e:
            raise Exception("Problems deploying Virtual Machine: %s" % str(e))

        return vm
            
    def add_link(self, vm1, vm2):
        link = VirtualLink()
        link.if_start = vm1.virtualinterface_set.all()[0]
        link.if_end = vm2.virtualinterface_set.all()[0]
        link.save()

    def remove_vm(self, vm):
        try:
            vm.undeploy()
            print "Virtual Machine %s was successfully deleted!" % vm.name
        except vm.VirtualMachineException as e:
            raise Exception("Could not undefine Virtual Machine on hypervisor %s: %s" % (vm.name, str(e)))
            
        # Delete VM from database anyway
        vm.delete()

    def calculate_distances(self):
        sw = Switch.objects.all()
        if len(sw) < 1:
            raise Exception('No switches available')
        # Figure out the topology based on what is connected to every switch port
        topology = {}
        for s in sw:
            topology[s.name] = []
            for p in s.port_set.all():
                topology[s.name] += p.connected_devices()
            
        # Calculates here the distance to all hosts
        host_hops = {}

        # Get all available hosts
        hs = Host.objects.all()

        for host in hs:
            # Find this host in the topology
            for sw in topology:
                for dev in topology[sw]:
                    if isinstance(dev, Host) and host.name == dev.name:
                        connected_to_sw = sw
        
            # Calculate a list of other hosts and number of hops to them
            output = self.hop_count(connected_to_sw, topology, 1, [])
            # Hop count for itself is always zero
            output[host.name] = 0
            host_hops[host.name] = output
            #logger.debug("Hop count for %s is: %s " % (h.name, str(host_hops[h.name])))

        return host_hops
        
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

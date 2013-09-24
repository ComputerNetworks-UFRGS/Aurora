# Run this script from the django shell:
#
# python manage.py shell
# from scripts.create_topology_complex import Topology
# t = Topology()
# t.create()

import time
import logging
from manager.models.host import Host
from manager.models.interface import Interface
from manager.models.switch import Switch
from manager.models.port import Port
from manager.models.device import Device

# Configure logging for the module name
logger = logging.getLogger("Aurora")

class Topology():

    def create(self):
        
        logger.info("##### Creating physical topology from script #####")
        begin_time = time.time()

        # Create hosts
        i_list = []
        for i in range(20):
            h = Host()
            h.name = "Host " + str(i+1)
            h.description = "Libvirt capable host"
            h.hostname = "h" + str(i+1)
            h.username = ""
            h.path = "system"
            h.extraparameters = ""
            h.save()

            intf = Interface()
            intf.attached_to = h
            intf.alias = "virbr1"
            intf.uplink_speed = 1000000000
            intf.downlink_speed = 1000000000
            intf.save()

            i_list.append(intf)

        # Every switch has a different # of ports
        total_ports = [4, 4, 4, 5, 5, 5, 4, 3, 2, 2]

        # Create switches
        sw_list = []
        for i in range(10):
            s = Switch()
            s.name = "OpenFlow Switch " + str(i+1)
            s.description = "OpenFlow enabled switch"
            s.hostname = "s" + str(i+1)
            s.sw_type = "openflow"
            s.save()

            sw_list.append(s)
            
            for j in range(total_ports[i]):
                p = Port()
                p.switch = s
                p.alias = s.hostname + "-eth" + str(j+1)
                p.uplink_speed = 1000000000
                p.downlink_speed = 1000000000
                p.save()

        # Create topology
        s1_ps = sw_list[0].port_set.all()
        s2_ps = sw_list[1].port_set.all()
        s3_ps = sw_list[2].port_set.all()
        s4_ps = sw_list[3].port_set.all()
        s5_ps = sw_list[4].port_set.all()
        s6_ps = sw_list[5].port_set.all()
        s7_ps = sw_list[6].port_set.all()
        s8_ps = sw_list[7].port_set.all()
        s9_ps = sw_list[8].port_set.all()
        s10_ps = sw_list[9].port_set.all()
        
        # s1 -> s2
        s1_ps[0].connected_ports.add(s2_ps[0])
        # s2 -> s3
        s2_ps[1].connected_ports.add(s3_ps[0])
        # s2 -> s4
        s2_ps[2].connected_ports.add(s4_ps[0])
        # s2 -> s5
        s2_ps[3].connected_ports.add(s5_ps[0])
        # s3 -> s6
        s3_ps[1].connected_ports.add(s6_ps[0])
        # s4 -> s8
        s4_ps[1].connected_ports.add(s8_ps[0])
        # s5 -> s9
        s5_ps[1].connected_ports.add(s9_ps[0])
        # s5 -> s10
        s5_ps[2].connected_ports.add(s10_ps[0])
        # s6 -> s7
        s6_ps[1].connected_ports.add(s7_ps[0])

        # s1 -> h1
        s1_ps[1].connected_interfaces.add(i_list[0])
        # s1 -> h2
        s1_ps[2].connected_interfaces.add(i_list[1])
        # s1 -> h3
        s1_ps[3].connected_interfaces.add(i_list[2])

        # s3 -> h4
        s3_ps[2].connected_interfaces.add(i_list[3])
        # s3 -> h5
        s3_ps[3].connected_interfaces.add(i_list[4])

        # s4 -> h6
        s4_ps[2].connected_interfaces.add(i_list[5])
        # s4 -> h7
        s4_ps[3].connected_interfaces.add(i_list[6])
        # s4 -> h8
        s4_ps[4].connected_interfaces.add(i_list[7])

        # s5 -> h9
        s5_ps[3].connected_interfaces.add(i_list[8])
        # s5 -> h10
        s5_ps[4].connected_interfaces.add(i_list[9])

        # s6 -> h11
        s6_ps[2].connected_interfaces.add(i_list[10])
        # s6 -> h12
        s6_ps[3].connected_interfaces.add(i_list[11])
        # s6 -> h13
        s6_ps[4].connected_interfaces.add(i_list[12])

        # s7 -> h14
        s7_ps[1].connected_interfaces.add(i_list[13])
        # s7 -> h15
        s7_ps[2].connected_interfaces.add(i_list[14])
        # s7 -> h16
        s7_ps[3].connected_interfaces.add(i_list[15])

        # s8 -> h17
        s8_ps[1].connected_interfaces.add(i_list[16])
        # s8 -> h18
        s8_ps[2].connected_interfaces.add(i_list[17])

        # s9 -> h19
        s9_ps[1].connected_interfaces.add(i_list[18])

        # s10 -> h20
        s10_ps[1].connected_interfaces.add(i_list[19])

        total_time = time.time() - begin_time
        logger.info("##### Topology created in %s seconds #####" % str(round(total_time, 2)))

    def drop_all(self):
        for d in Device.objects.all():
            d.delete()

#!/usr/bin/python

# Import topology from floodlight

# Run this script from the django shell:
# python manage.py shell
# from scripts.import_topology_zones import import_topology 
# import_topology()

import urllib
import json

from cloud.models.host import Host
from cloud.models.interface import Interface
from cloud.models.switch import Switch
from cloud.models.port import Port
from cloud.models.device import Device


def import_topology():
    switches_url = "http://localhost:8080/wm/core/controller/switches/json"
    links_url = "http://localhost:8080/wm/topology/links/json"
    
    # Fetch switches
    sw_response = urllib.urlopen(switches_url)
    sw_data = json.loads(sw_response.read())
    
    # Fetch links
    link_response = urllib.urlopen(links_url)
    link_data = json.loads(link_response.read())
    
    i = 0
    sw_dict = {}
    link_list = []
    for sw in sw_data:
        if sw['dpid'].startswith('a0:b0:b4'): # Skip Aurora host local OVS bridges
            continue
    
        i += 1
        # Create switch objects
        s = Switch()
        s.name = sw['dpid']
        s.description = sw['attributes']['DescriptionData']['hardwareDescription'] + ', ' + \
                        sw['attributes']['DescriptionData']['softwareDescription'] + ', ' + \
                        sw['attributes']['DescriptionData']['manufacturerDescription']
        s.hostname = 's' + str(i)
        s.sw_type = 'openflow'
        s.save()
        sw_dict[sw['dpid']] = s
        print 'Switch created: ' + sw['dpid']
    
        # Only import ports connected with source links (links are bidirectional)
        # This avoids importing control porst with high port number (e.g., 65534)
        for link in link_data:
            if link['src-switch'] == sw['dpid']:
                # Link found from this switch, now find port details
                for pt in sw['ports']:
                    if pt['portNumber'] == link['src-port']:
                        # Create port object
                        p = Port()
                        p.switch = s
                        p.alias = pt['portNumber']
                        p.uplink_speed = 100000000
                        p.downlink_speed = 100000000
                        p.save()
                        print '\tPort created: ' + str(pt['portNumber'])

    # Create topology
    for link in link_data:
        # Store links in a set to avoid duplication
        link_set = set([link['src-switch'], link['src-port'], link['dst-switch'], link['dst-port']])
        if link_set not in link_list:
            link_list.append(link_set)
        else:
            continue # Link already created, so skip it

        print 'Ports connected: %s-%d -> %s-%d' % ( link['src-switch'], link['src-port'], link['dst-switch'], link['dst-port'] )
        src_port = Port.objects.get(alias=link['src-port'], switch__name=link['src-switch'])
        dst_port = Port.objects.get(alias=link['dst-port'], switch__name=link['dst-switch'])
        src_port.connected_ports.add(dst_port)
        

    # Down here is hardcoded
    
    # Add 32 hosts
    h_index = 0
    for sw in sorted(sw_data, key=lambda k: k['dpid']): # Needs to be sorted to guarantee h1 falls under zone 1 and so on
        # Skip Aurora hosts and core switches
        if sw['dpid'].startswith('a0:b0:b4') or sw['dpid'].startswith('00:00:00:00'): 
            continue
        
        # Edge switch dpids end in 01 or 02
        if sw['dpid'].endswith('01') or sw['dpid'].endswith('02'):
            sw_obj = Switch.objects.get(name=sw['dpid'])
            for i in range(4):
                h_index += 1

                h = Host()
                h.name = "Host " + str(h_index)
                h.description = "Libvirt capable host"
                h.hostname = "h" + str(h_index)
                h.username = ""
                h.transport = "tls"
                h.path = "system"
                h.extraparameters = ""
                h.ovsdb = "unix:/usr/local/var/run/openvswitch/h" + str(h_index) + "-db.sock"
                h.save()
                stat = h.check_openvswitch_status() # Checking the status will create the OVS bridge (possibly)
                print 'Host created: ' + h.name
    
                intf = Interface()
                intf.attached_to = h
                intf.alias = "h" + str(h_index) + "-eth0"
                intf.uplink_speed = 100000000
                intf.downlink_speed = 100000000
                intf.save()
                stat = intf.check_interface_status() # Checking the status will add this interface to the OVS bridge (possibly)
                print 'Interface created: ' + intf.alias

                # Connect host to switch port
                # Create port object
                p = Port()
                p.switch = sw_obj
                p.alias = 'h' + str(h_index)
                p.uplink_speed = 100000000
                p.downlink_speed = 100000000
                p.save()
                print 'Port created: ' + p.alias
                
                p.connected_interfaces.add(intf)
                print 'Port ' + p.alias + ' connected to interface ' + intf.alias


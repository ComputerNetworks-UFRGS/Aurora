#!/usr/bin/python

"""
This script creates a fattree topology and starts some services in its hosts
so that the Aurora platform can control them
"""
import time
import os

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, RemoteController, OVSSwitch
from mininet.log import setLogLevel, info, warn
from mininet.cli import CLI
from mininet.link import Link, TCIntf
from mininet.util import custom

# Topology choices
from fattree import FatTree
from zones import Zones

def startTopo(topo_choice = 'fattree'):

    if topo_choice == 'fattree':
        topology = FatTree(num_pods = 4, host_multiplier = 2)
    elif topo_choice == 'zones':
        topology = Zones()

    intf = custom (TCIntf, bw = 100, latency_ms = 2)
    net = Mininet(topo=topology, intf=intf, controller=RemoteController, autoSetMacs=True, build=False)

    # Create management network
    info('*** Creating management network\n' )
    mansw = OVSSwitch( 'man', failMode = 'standalone', inNamespace = False, dpid = ('9'.zfill(8) + '1'.zfill(8)) )

    # Create a node in root namespace and link to management network
    root = Node( 'root', inNamespace=False )
    manlink = Link( root , mansw )
    manlink.intf1.setMAC( '10:00:00:00:01:00' )
    manlink.intf1.setIP( '172.16.1.1', 16 )

    info('*** Adding controller\n' )
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    info( '*** Building network\n' )
    net.build()

    # Add a second interface to every host for the management network
    hindex = 1
    for h in net.hosts:
        link = Link( h, mansw )
        link.intf1.setMAC( '10:00:00:00:00:' +  ('%x' % hindex).zfill(2) ) # max 255 hosts
        link.intf1.setIP( '172.16.0.' + str(hindex), 16 ) # max 255 hosts
        hindex += 1
    
    info( '*** Starting network\n' )
    net.start()

    info( '*** Starting management network\n' )
    mansw.start([]) # starts switch with no controller

    info( '*** Starting Open vSwitch server in every host\n' )
    ovs_etc = '/usr/local/etc/openvswitch/'
    ovs_run = '/usr/local/var/run/openvswitch/'
    ovs_log = '/usr/local/var/log/openvswitch/'
    for h in net.hosts:
        # Only init database if it doesnt exist
        #if not os.path.exists( ovs_etc + h.name + '-conf.db' ):
        #    h.cmd( 'ovsdb-tool create ' + ovs_etc + h.name + '-conf.db /usr/share/openvswitch/vswitch.ovsschema' )

        # Reinitialize the database every time
        if os.path.exists( ovs_etc + h.name + '-conf.db' ):
            os.remove( ovs_etc + h.name + '-conf.db' )
        h.cmd( 'ovsdb-tool create ' + ovs_etc + h.name + '-conf.db /usr/share/openvswitch/vswitch.ovsschema' )

        h.cmd( 'ovsdb-server ' + ovs_etc + h.name + '-conf.db  --remote=punix:' + ovs_run + h.name + '-db.sock --pidfile=' + ovs_run + h.name + '-ovsdb-server.pid --log-file=' + ovs_log + h.name + '-ovsdb-server.log --detach' )
        h.cmd( 'ovs-vsctl --db=unix:' + ovs_run + h.name + '-db.sock --no-wait init' )
        h.cmd( 'ovs-vswitchd unix:' + ovs_run + h.name + '-db.sock --pidfile=' + ovs_run + h.name + '-ovs-vswitchd.pid --log-file=' + ovs_log + h.name + '-ovs-vswitchd.log --detach' )
        h.cmd( 'chmod 777 ' + ovs_run + h.name + '-db.sock' ) # Allow access to everyone to this OVS
        #h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock set-manager ptcp:8888' )

    info( '*** Starting SSH Server in every host\n' )
    for h in net.hosts:
        h.cmd( '/usr/local/sbin/dropbear -P /tmp/dropbear-' + h.name + '.pid' )

    info( '*** Starting Libvirt daemon in every host\n' )
    libv_etc = '/usr/local/libvirt/%s/etc/libvirt/'
    libv_run = '/usr/local/libvirt/%s/var/run/'
    for h in net.hosts:
        #h.cmd( 'libvirtd -dl -f ' + (libv_etc % h.name) + 'libvirtd.conf -p ' + (libv_run % h.name) + 'libvirtd.pid' )
        h.cmd( 'libvirtd-' + h.name + ' -l -d' )

    #info( '*** Running CLI\n' )
    #CLI( net )
    
    #info( '*** Killing daemons\n' )
    # Kill ssh daemon from any host
    #net.hosts[0].cmd( 'killall dropbear' )

    #for h in net.hosts:
    #    h.cmd( 'kill $(cat ' + (libv_run % h.name) + 'libvirtd.pid)' )
    #    h.cmd( 'kill $(cat ' + ovs_run + h.name + '-ovsdb-server.pid)' )
    #    h.cmd( 'kill $(cat ' + ovs_run + h.name + '-ovs-vswitchd.pid)' )

    #info( '*** Stopping management network\n' )
    #mansw.stop()

    #info( '*** Stopping network\n' )
    #net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )  # for CLI output
    #startTopo(topo_choice = 'zones')
    startTopo(topo_choice = 'fattree')

#!/usr/bin/python

"""
This example shows how to create an empty Mininet object
(without a topology object) and add nodes to it manually.
"""

import os
import time
from mininet.net import Mininet
from mininet.node import RemoteController, Node
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def emptyNet():

    "Create an empty network and add nodes to it."

    net = Mininet( controller=RemoteController )

    info( '*** Adding controller\n' )
    net.addController( 'c0' )

    info( '*** Adding hosts\n' )
    h1 = net.addHost( 'h1', ip='192.168.120.1' )
    h2 = net.addHost( 'h2', ip='192.168.120.2' )

    info( '*** Adding switch\n' )
    s3 = net.addSwitch( 's3' )

    info( '*** Creating links\n' )
    net.addLink( h1, s3 )
    net.addLink( h2, s3 )

    print "** Creating extra node to enable access to others"
    # Create a node in root namespace and link to switch 0
    root = Node( 'root', inNamespace=False )
    root.linkTo( s3 )
    root.setIP( '192.168.120.100', 24, root.defaultIntf() )

    info( '*** Starting network\n')
    net.start()

    print "** Starting SSH Server in every host"
    sshpids = {}
    for h in net.hosts:
        h.cmd( '/usr/sbin/sshd -D &' )
        time.sleep(1) # Whait for the daemon to come up so we can see its pid (this is not very safe)
        output = h.cmd( 'cat /var/run/sshd.pid' )
        sshpids[h.name] = output.rstrip()

    print "** Starting Libvirt in every host"
    for h in net.hosts:
        ip = h.IP()
        h.cmd( 'ip addr flush ' + str(h.defaultIntf()) )
        #if not os.path.exists( '/usr/local/etc/openvswitch/' + h.name + '-conf.db' ):
        #    h.cmd( 'ovsdb-tool create /usr/local/etc/openvswitch/' + h.name + '-conf.db /home/jwickboldt/openvswitch-1.10.0/vswitchd/vswitch.ovsschema' )
        #h.cmd( 'ovsdb-server /usr/local/etc/openvswitch/' + h.name + '-conf.db --remote=punix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock --pidfile=/usr/local/var/run/openvswitch/' + h.name + '-ovsdb-server.pid --detach' )
        #h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock --no-wait init' )
        #h.cmd( 'ovs-vswitchd unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock --pidfile=/usr/local/var/run/openvswitch/' + h.name + '-ovs-vswitchd.pid --detach' )
        #h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock add-br virbr1' )
        #h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock add-port virbr1 ' + str(h.defaultIntf()) )
        #h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock set-controller virbr1 tcp:192.168.120.100:6633' )
        h.cmd( 'brctl addbr virbr1' )
        h.cmd( 'brctl addif virbr1 ' + str(h.defaultIntf()) )
        h.cmd( 'ip link set dev virbr1 up' )
        h.cmd( 'ifconfig virbr1 ' + ip  )
        # Default route through root-eth0
        h.cmd ( 'route add default gw 192.168.120.100' )
        h.cmd ( 'libvirtd-' + h.name + ' -d -l' )

    info( '*** Running CLI\n' )
    CLI( net )

    print "** Killing daemons"
    for h in net.hosts:
        h.cmd( 'kill `pidof libvirtd-' + h.name + '`' )
        h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock del-br virbr1' )
        h.cmd( 'kill $(cat /usr/local/var/run/openvswitch/' + h.name + '-ovsdb-server.pid)' )
        h.cmd( 'kill $(cat /usr/local/var/run/openvswitch/' + h.name + '-ovs-vswitchd.pid)' )
        if len( sshpids[h.name] ) < 7:
            h.cmd( 'kill ' + sshpids[h.name] )

    info( '*** Stopping network' )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    emptyNet()

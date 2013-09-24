#!/usr/bin/python

"""
This is my first script network
"""

import time
import os
import sys

# Use mininet installation from user's home
sys.path.append('/home/jwickboldt/mininet')

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch, ControllerParams, Node
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.util import makeIntfPair

def myNet():
    "Defines a custom topology on mininet."

    print "*** Starting MyNet ***"
    cParams = ControllerParams( '10.0.3.0', 24 )
    net = Mininet( controller=RemoteController, switch=OVSKernelSwitch, cparams=cParams )

    print "** Adding controller"
    c = net.addController( 'c0' )

    print "** Adding switches"
    s1 = net.addSwitch( 's1' )
    s2 = net.addSwitch( 's2' )
    s3 = net.addSwitch( 's3' )
    s4 = net.addSwitch( 's4' )
    s5 = net.addSwitch( 's5' )
    s6 = net.addSwitch( 's6' )
    s7 = net.addSwitch( 's7' )
    s8 = net.addSwitch( 's8' )
    s9 = net.addSwitch( 's9' )
    s10 = net.addSwitch( 's10' )

    print "** Adding hosts"
    h1 = net.addHost( 'h1', ip='10.0.3.1' )
    h2 = net.addHost( 'h2', ip='10.0.3.2' )
    h3 = net.addHost( 'h3', ip='10.0.3.3' )
    h4 = net.addHost( 'h4', ip='10.0.3.4' )
    h5 = net.addHost( 'h5', ip='10.0.3.5' )
    h6 = net.addHost( 'h6', ip='10.0.3.6' )
    h7 = net.addHost( 'h7', ip='10.0.3.7' )
    h8 = net.addHost( 'h8', ip='10.0.3.8' )
    h9 = net.addHost( 'h9', ip='10.0.3.9' )
    h10 = net.addHost( 'h10', ip='10.0.3.10' )
    h11 = net.addHost( 'h11', ip='10.0.3.11' )
    h12 = net.addHost( 'h12', ip='10.0.3.12' )
    h13 = net.addHost( 'h13', ip='10.0.3.13' )
    h14 = net.addHost( 'h14', ip='10.0.3.14' )
    h15 = net.addHost( 'h15', ip='10.0.3.15' )
    h16 = net.addHost( 'h16', ip='10.0.3.16' )
    h17 = net.addHost( 'h17', ip='10.0.3.17' )
    h18 = net.addHost( 'h18', ip='10.0.3.18' )
    h19 = net.addHost( 'h19', ip='10.0.3.19' )
    h20 = net.addHost( 'h20', ip='10.0.3.20' )

    print "** Linking switches and hosts"
    # S1
    s1.linkTo( s2 )
    s1.linkTo( h1 )
    s1.linkTo( h2 )
    s1.linkTo( h3 )
    # S2
    s2.linkTo( s3 )
    s2.linkTo( s4 )
    s2.linkTo( s5 )
    # S3
    s3.linkTo( s6 )
    s3.linkTo( h4 )
    s3.linkTo( h5 )
    # S4
    s4.linkTo( s8 )
    s4.linkTo( h6 )
    s4.linkTo( h7 )
    s4.linkTo( h8 )
    # S5
    s5.linkTo( s9 )
    s5.linkTo( s10 )
    s5.linkTo( h9 )
    s5.linkTo( h10 )
    # S6
    s6.linkTo( s7 )
    s6.linkTo( h11 )
    s6.linkTo( h12 )
    s6.linkTo( h13 )
    # S7
    s7.linkTo( h14 )
    s7.linkTo( h15 )
    s7.linkTo( h16 )
    # S8
    s8.linkTo( h17 )
    s8.linkTo( h18 )
    # S9
    s9.linkTo( h19 )
    # S10
    s10.linkTo( h20 )

    print "** Creating extra node to enable access to others"
    # Create a node in root namespace and link to switch 0
    root = Node( 'root', inNamespace=False )
    root.linkTo( s1 )
    root.setMAC( root.defaultIntf(), "00:00:00:11:00:64" )
    root.setIP( root.defaultIntf(), "10.0.3.100", 24 )

    # Configure everything
    s1.setMAC ( 's1-eth1', '00:00:00:10:01:01' )
    s1.setMAC ( 's1-eth2', '00:00:00:10:01:02' )
    s1.setMAC ( 's1-eth3', '00:00:00:10:01:03' )
    s1.setMAC ( 's1-eth4', '00:00:00:10:01:04' )
    s1.setMAC ( 's1-eth5', '00:00:00:10:01:05' ) # Extra for the root

    s2.setMAC ( 's2-eth1', '00:00:00:10:02:01' )
    s2.setMAC ( 's2-eth2', '00:00:00:10:02:02' )
    s2.setMAC ( 's2-eth3', '00:00:00:10:02:03' )
    s2.setMAC ( 's2-eth4', '00:00:00:10:02:04' )

    s3.setMAC ( 's3-eth1', '00:00:00:10:03:01' )
    s3.setMAC ( 's3-eth2', '00:00:00:10:03:02' )
    s3.setMAC ( 's3-eth3', '00:00:00:10:03:03' )
    s3.setMAC ( 's3-eth4', '00:00:00:10:03:04' )

    s4.setMAC ( 's4-eth1', '00:00:00:10:04:01' )
    s4.setMAC ( 's4-eth2', '00:00:00:10:04:02' )
    s4.setMAC ( 's4-eth3', '00:00:00:10:04:03' )
    s4.setMAC ( 's4-eth4', '00:00:00:10:04:04' )
    s4.setMAC ( 's4-eth5', '00:00:00:10:04:05' )

    s5.setMAC ( 's5-eth1', '00:00:00:10:05:01' )
    s5.setMAC ( 's5-eth2', '00:00:00:10:05:02' )
    s5.setMAC ( 's5-eth3', '00:00:00:10:05:03' )
    s5.setMAC ( 's5-eth4', '00:00:00:10:05:04' )
    s5.setMAC ( 's5-eth5', '00:00:00:10:05:05' )

    s6.setMAC ( 's6-eth1', '00:00:00:10:06:01' )
    s6.setMAC ( 's6-eth2', '00:00:00:10:06:02' )
    s6.setMAC ( 's6-eth3', '00:00:00:10:06:03' )
    s6.setMAC ( 's6-eth4', '00:00:00:10:06:04' )
    s6.setMAC ( 's6-eth5', '00:00:00:10:06:05' )

    s7.setMAC ( 's7-eth1', '00:00:00:10:07:01' )
    s7.setMAC ( 's7-eth2', '00:00:00:10:07:02' )
    s7.setMAC ( 's7-eth3', '00:00:00:10:07:03' )
    s7.setMAC ( 's7-eth4', '00:00:00:10:07:04' )

    s8.setMAC ( 's8-eth1', '00:00:00:10:08:01' )
    s8.setMAC ( 's8-eth2', '00:00:00:10:08:02' )
    s8.setMAC ( 's8-eth3', '00:00:00:10:08:03' )

    s9.setMAC ( 's9-eth1', '00:00:00:10:09:01' )
    s9.setMAC ( 's9-eth2', '00:00:00:10:09:02' )

    s10.setMAC ( 's10-eth1', '00:00:00:10:10:01' )
    s10.setMAC ( 's10-eth2', '00:00:00:10:10:02' )

    s1.setIP ( s1.defaultIntf(), '10.0.3.101', 24 )
    s2.setIP ( s2.defaultIntf(), '10.0.3.102', 24 )
    s3.setIP ( s3.defaultIntf(), '10.0.3.103', 24 )
    s4.setIP ( s4.defaultIntf(), '10.0.3.104', 24 )
    s5.setIP ( s5.defaultIntf(), '10.0.3.105', 24 )
    s6.setIP ( s6.defaultIntf(), '10.0.3.106', 24 )
    s7.setIP ( s7.defaultIntf(), '10.0.3.107', 24 )
    s8.setIP ( s8.defaultIntf(), '10.0.3.108', 24 )
    s9.setIP ( s9.defaultIntf(), '10.0.3.109', 24 )
    s10.setIP ( s10.defaultIntf(), '10.0.3.110', 24 )

    h1.setMAC( h1.defaultIntf(), "00:00:00:11:00:01" )
    h2.setMAC( h2.defaultIntf(), "00:00:00:11:00:02" )
    h3.setMAC( h3.defaultIntf(), "00:00:00:11:00:03" )
    h4.setMAC( h4.defaultIntf(), "00:00:00:11:00:04" )
    h5.setMAC( h5.defaultIntf(), "00:00:00:11:00:05" )
    h6.setMAC( h6.defaultIntf(), "00:00:00:11:00:06" )
    h7.setMAC( h7.defaultIntf(), "00:00:00:11:00:07" )
    h8.setMAC( h8.defaultIntf(), "00:00:00:11:00:08" )
    h9.setMAC( h9.defaultIntf(), "00:00:00:11:00:09" )
    h10.setMAC( h10.defaultIntf(), "00:00:00:11:00:10" )
    h11.setMAC( h11.defaultIntf(), "00:00:00:11:00:11" )
    h12.setMAC( h12.defaultIntf(), "00:00:00:11:00:12" )
    h13.setMAC( h13.defaultIntf(), "00:00:00:11:00:13" )
    h14.setMAC( h14.defaultIntf(), "00:00:00:11:00:14" )
    h15.setMAC( h15.defaultIntf(), "00:00:00:11:00:15" )
    h16.setMAC( h16.defaultIntf(), "00:00:00:11:00:16" )
    h17.setMAC( h17.defaultIntf(), "00:00:00:11:00:17" )
    h18.setMAC( h18.defaultIntf(), "00:00:00:11:00:18" )
    h19.setMAC( h19.defaultIntf(), "00:00:00:11:00:19" )
    h20.setMAC( h20.defaultIntf(), "00:00:00:11:00:20" )

    print "** Firing up the network"
    net.build()
    c.start()
    for s in net.switches:
        s.start( [ c ] )
    
    print "** Starting SSH Server in every host"
    sshpids = {}
    for h in net.hosts:
        h.cmd( '/usr/sbin/sshd -D &' )
        time.sleep(0.5) # Whait for the daemon to come up so we can see its pid (this is not very safe)
        output = h.cmd( 'cat /var/run/sshd.pid' )
        sshpids[h.name] = output.rstrip()

    print "** Starting Libvirt in every host"
    for h in net.hosts:
        ip = h.IP()
        h.cmd( 'ip addr flush ' + h.defaultIntf() )
        if not os.path.exists( '/usr/local/etc/openvswitch/' + h.name + '-conf.db' ):
            h.cmd( 'ovsdb-tool create /usr/local/etc/openvswitch/' + h.name + '-conf.db /home/jwickboldt/openvswitch-1.10.0/vswitchd/vswitch.ovsschema' )
        h.cmd( 'ovsdb-server /usr/local/etc/openvswitch/' + h.name + '-conf.db --remote=punix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock --pidfile=/usr/local/var/run/openvswitch/' + h.name + '-ovsdb-server.pid --detach' )
        h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock --no-wait init' )
        h.cmd( 'ovs-vswitchd unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock --pidfile=/usr/local/var/run/openvswitch/' + h.name + '-ovs-vswitchd.pid --detach' )
        h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock add-br virbr1' )
        h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock add-port virbr1 ' + h.defaultIntf() )
        h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock set-controller virbr1 tcp:10.0.3.100:6633' )
        h.cmd( 'ip link set dev virbr1 up' )
        h.setIP( 'virbr1', ip, 24 )

        # Default route through root-eth0
        h.cmd ( 'route add default gw 10.0.3.100' )
        h.cmd ( 'libvirtd-' + h.name + ' -d -l' )

    #print "** Testing network"
    #net.pingAll()

    print "** Running CLI"
    CLI( net )

    print "** Killing daemons"
    for h in net.hosts:
        h.cmd( 'kill `pidof libvirtd-' + h.name + '`' )
        h.cmd( 'ovs-vsctl --db=unix:/usr/local/var/run/openvswitch/' + h.name + '-db.sock del-br virbr1' )
        h.cmd( 'kill $(cat /usr/local/var/run/openvswitch/' + h.name + '-ovsdb-server.pid)' )
        h.cmd( 'kill $(cat /usr/local/var/run/openvswitch/' + h.name + '-ovs-vswitchd.pid)' )
        if len( sshpids[h.name] ) < 7:
            h.cmd( 'kill ' + sshpids[h.name] )

    print "** Stopping network"
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'debug' )  # for CLI output
    myNet()


#!/usr/bin/python

"""
This is my first script network
"""

import time

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

   print "** Adding hosts"
   h5 = net.addHost( 'h5', ip='10.0.3.5' )
   h6 = net.addHost( 'h6', ip='10.0.3.6' )
   h7 = net.addHost( 'h7', ip='10.0.3.7' )
   h8 = net.addHost( 'h8', ip='10.0.3.8' )
   h9 = net.addHost( 'h9', ip='10.0.3.9' )

   print "** Linking switches together"
   s1.linkTo( s2 )
   s2.linkTo( s3 )
   s2.linkTo( s4 )

   print "** Linking hosts to switches"
   h5.linkTo( s1 )
   h6.linkTo( s3 )
   h7.linkTo( s3 )
   h8.linkTo( s4 )
   h9.linkTo( s4 )

   #print "** Setting up IP addresses"
   #h5.setIP( h5.defaultIntf(), '10.0.3.5', 24)

   #extraPort1 = s1.newPort()
   #extraPortName1 = s1.intfName( extraPort1 )
   #print "** Adding extra port to s1 - " + extraPortName1
   #s1.addIntf( extraPortName1, extraPort1 )

   #print "** Linking xeth0 to s1 port " + extraPortName1
   #makeIntfPair( "xeth0", extraPortName1 )

   #extraPort2 = s4.newPort()
   #extraPortName2 = s4.intfName( extraPort2 )
   #print "** Adding extra port to s4 - " + extraPortName2
   #s4.addIntf( extraPortName2, extraPort2 )

   #print "** Linking xeth1 to s4 port " + extraPortName2
   #makeIntfPair( "xeth1", extraPortName2 )

   print "** Creating extra node to enable access to others"
   # Create a node in root namespace and link to switch 0
   root = Node( 'root', inNamespace=False )
   root.linkTo( s1 )
   root.setMAC( root.defaultIntf(), "00:00:00:10:00:64" )
   root.setIP( root.defaultIntf(), "10.0.3.100", 24 )

   #Configure everything
   s1.setMAC ( 's1-eth1', '00:00:00:10:01:01' )
   s1.setMAC ( 's1-eth2', '00:00:00:10:01:02' )
   s1.setMAC ( 's1-eth3', '00:00:00:10:01:03' )
   s2.setMAC ( 's2-eth1', '00:00:00:10:02:01' )
   s2.setMAC ( 's2-eth2', '00:00:00:10:02:02' )
   s2.setMAC ( 's2-eth3', '00:00:00:10:02:03' )
   s3.setMAC ( 's3-eth1', '00:00:00:10:03:01' )
   s3.setMAC ( 's3-eth2', '00:00:00:10:03:02' )
   s3.setMAC ( 's3-eth3', '00:00:00:10:03:03' )
   s4.setMAC ( 's4-eth1', '00:00:00:10:04:01' )
   s4.setMAC ( 's4-eth2', '00:00:00:10:04:02' )
   s4.setMAC ( 's4-eth3', '00:00:00:10:04:03' )
   s1.setIP ( s1.defaultIntf(), '10.0.3.1', 24 )
   s2.setIP ( s2.defaultIntf(), '10.0.3.2', 24 )
   s3.setIP ( s3.defaultIntf(), '10.0.3.3', 24 )
   s4.setIP ( s4.defaultIntf(), '10.0.3.4', 24 )

   h5.setMAC( h5.defaultIntf(), "00:00:00:10:00:05" )
   h6.setMAC( h6.defaultIntf(), "00:00:00:10:00:06" )
   h7.setMAC( h7.defaultIntf(), "00:00:00:10:00:07" )
   h8.setMAC( h8.defaultIntf(), "00:00:00:10:00:08" )
   h9.setMAC( h9.defaultIntf(), "00:00:00:10:00:09" )

   print "** Firing up the network"
   net.build()
   # Try to add eth1 into s1
   #print s1.cmd( 'ovs-dpctl add-if dp0 eth1' )
   c.start()
   s1.start( [ c ] )
   s2.start( [ c ] )
   s3.start( [ c ] )
   s4.start( [ c ] )

   print "** Starting SSH Server in every host"
   sshpids = {}
   for h in net.hosts:
      h.cmd( '/usr/sbin/sshd -D &' )
      time.sleep(2) # Whait for the daemon to come up so we can see its pid (this is not very safe)
      output = h.cmd( 'cat /var/run/sshd.pid' )
      sshpids[h.name] = output.rstrip()

   print "** Starting Libvirt in every host"
   for h in net.hosts:
      ip = h.IP()
      h.cmd( 'ip addr flush ' + h.defaultIntf() )
      h.cmd( 'brctl addbr virbr1' )
      h.cmd( 'brctl addif virbr1 ' + h.defaultIntf() )
      h.cmd( 'ip link set dev virbr1 up' )
      h.setIP( 'virbr1', ip, 24 )
      h.cmd( '/home/juliano/' + h.name + '/sbin/libvirtd -d -l -p /home/juliano/' + h.name + '/var/run/libvirtd.pid -f /home/juliano/' + h.name + '/etc/libvirt/libvirtd.conf' )

   print "** Testing network"
   # net.pingAll()

   print "** Running CLI"
   CLI( net )

   print "** Killing daemons"
   for h in net.hosts:
      h.cmd( 'kill `cat /home/juliano/' + h.name + '/var/run/libvirtd.pid`' )
      if len( sshpids[h.name] ) < 7:
         h.cmd( 'kill ' + sshpids[h.name] )

   print "** Stopping network"
   net.stop()

if __name__ == '__main__':
   setLogLevel( 'debug' )  # for CLI output
   myNet()


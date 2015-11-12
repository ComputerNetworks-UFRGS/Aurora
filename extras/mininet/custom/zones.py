#!/usr/bin/python

"""
This script fires up a topology with four zones in mininet
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.log import setLogLevel, info
from mininet.cli import CLI

class Zones(Topo):
    """
    Creates topology with four zones, each zone has two egde switches connected 
    to four hosts and two aggregation switches connected to a ring core network
    with another four switches
    """

    def __init__(self):
        Topo.__init__(self)

        # Add 4 core switches
        cs1 = self.addSwitch('cs1', dpid = self.makeDpid(0, 1))
        cs2 = self.addSwitch('cs2', dpid = self.makeDpid(0, 2))
        cs3 = self.addSwitch('cs3', dpid = self.makeDpid(0, 3))
        cs4 = self.addSwitch('cs4', dpid = self.makeDpid(0, 4))

        # Core swiches form a ring
        self.addLink(cs1, cs2)
        self.addLink(cs2, cs3)
        self.addLink(cs3, cs4)
        self.addLink(cs4, cs1)

        # Global host index
        hindex = 0

        # Add four switches per zone
        for i in range(4):
            es1 = self.addSwitch('es1z' + str(i+1), dpid = self.makeDpid(i+1, 1))
            es2 = self.addSwitch('es2z' + str(i+1), dpid = self.makeDpid(i+1, 2))
            as1 = self.addSwitch('as1z' + str(i+1), dpid = self.makeDpid(i+1, 3))
            as2 = self.addSwitch('as2z' + str(i+1), dpid = self.makeDpid(i+1, 4))

            # Connect edge to aggregation switches (full mesh)
            self.addLink(es1, as1)
            self.addLink(es1, as2)
            self.addLink(es2, as1)
            self.addLink(es2, as2)
            self.addLink(es1, es2)
            self.addLink(as1, as2)

            # Zone 1 connects to core switches 1 and 2
            if i == 0:
                self.addLink(as1, cs1)
                self.addLink(as2, cs2)
            # Zone 2 connects to core switches 2 and 3
            elif i == 1:
                self.addLink(as1, cs2)
                self.addLink(as2, cs3)
            # Zone 3 connects to core switches 3 and 4
            elif i == 2:
                self.addLink(as1, cs3)
                self.addLink(as2, cs4)
            # Zone 4 connects to core switches 4 and 1
            elif i == 3:
                self.addLink(as1, cs4)
                self.addLink(as2, cs1)

            # Add 4 hosts to the es1 and 4 to es2
            for k in range(8):
                hindex += 1
                h = self.addHost('h' + str(hindex))
                # Link the host just created to the edge switch
                if k < 4:
                    self.addLink(es1, h)
                else:
                    self.addLink(es2, h)

    # This will make a representation of the switch dpid showing the layer (core, edge, aggr) and switch_id
    def makeDpid(self, layer, switch_id):
        # Layer info is shifted 4 bytes to the left
        return str(layer).zfill(8) + str(switch_id).zfill(8)


def startTopo():

    topology = Zones()
    net = Mininet(topo=topology, controller=RemoteController, autoSetMacs=True, build=False)
    
    info('*** Adding controller\n')
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    info( '*** Building network\n')
    net.build()
    
    info( '*** Starting network\n')
    net.start()
    
    info( '*** Running CLI\n' )
    CLI( net )
    
    info( '*** Stopping network' )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    startTopo()


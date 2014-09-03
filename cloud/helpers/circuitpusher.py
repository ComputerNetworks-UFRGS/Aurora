#! /usr/bin/python
"""
Copyright 2013, Big Switch Networks, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.

circuitpusher utilizes floodlight rest APIs to create a bidirectional circuit, 
i.e., permanent flow entry, on all switches in route between two devices based 
on IP addresses with specified priority.
 
Notes:
 1. The circuit pusher currently only creates circuit with two IP end points 
 2. Prior to sending restAPI requests to the circuit pusher, the specified end
    points must already been known to the controller (i.e., already have sent
    packets on the network, easy way to assure this is to do a ping (to any
    target) from the two hosts.
 3. The current supported command syntax format is:
    a) circuitpusher.py --controller={IP}:{rest port} --type ip --src {IP} --dst {IP} --add --name {circuit-name}
 
       adds a new circuit between src and dst devices Currently ip circuit is supported. ARP is automatically supported.
    
       Currently a simple circuit record storage is provided in a text file circuits.json in the working directory.
       The file is not protected and does not clean itself between controller restarts.  The file is needed for correct operation
       and the user should make sure deleting the file when floodlight controller is restarted.

    b) circuitpusher.py --controller={IP}:{rest port} --delete --name {circuit-name}

       deletes a created circuit (as recorded in circuits.json) using the previously given name

@author kcwang
"""

import os
import sys
import subprocess
import json
import argparse
import io
import time

# parse circuit options.  Currently supports add and delete actions.
# Syntax:
#   circuitpusher --controller {IP:REST_PORT} --add --name {CIRCUIT_NAME} --type ip --src {IP} --dst {IP} 
#   circuitpusher --controller {IP:REST_PORT} --add --name {CIRCUIT_NAME} --type eth --src {mac} --dst {mac} 
#   circuitpusher --controller {IP:REST_PORT} --add --name {CIRCUIT_NAME} --type phy --src {port:switch} --dst {port:switch} 
#   circuitpusher --controller {IP:REST_PORT} --delete --name {CIRCUIT_NAME}

parser = argparse.ArgumentParser(description='Circuit Pusher')
parser.add_argument('--controller', dest='controllerRestIp', action='store', default='localhost:8080', help='controller IP:RESTport, e.g., localhost:8080 or A.B.C.D:8080')
parser.add_argument('--add', dest='action', action='store_const', const='add', default='add', help='action: add, delete')
parser.add_argument('--delete', dest='action', action='store_const', const='delete', default='add', help='action: add, delete')
parser.add_argument('--type', dest='type', action='store', default='ip', help='valid types: ip|eth|phy')
parser.add_argument('--src', dest='srcAddress', action='store', default='0.0.0.0', help='source address: if type=ip, A.B.C.D')
parser.add_argument('--dst', dest='dstAddress', action='store', default='0.0.0.0', help='destination address: if type=ip, A.B.C.D')
parser.add_argument('--name', dest='circuitName', action='store', default='circuit-1', help='name for circuit, e.g., circuit-1')

args = parser.parse_args()
print args

controllerRestIp = args.controllerRestIp

# first check if a local file exists, which needs to be updated after add/delete
if os.path.exists('/home/aurora/Aurora/cloud/helpers/circuits.json'):
    circuitDb = open('/home/aurora/Aurora/cloud/helpers/circuits.json','r')
    lines = circuitDb.readlines()
    circuitDb.close()
else:
    lines={}

if args.action=='add':

    circuitDb = open('/home/aurora/Aurora/cloud/helpers/circuits.json','a')
    
    for line in lines:
        data = json.loads(line)
        if data['name']==(args.circuitName):
            print "Circuit %s exists already. Use new name to create." % args.circuitName
            sys.exit()
        else:
            circuitExists = False
    
    # retrieve source and destination device attachment points
    # using DeviceManager rest API 
    
    if args.type == "eth":
        command = "curl -s http://%s/wm/device/?mac=%s" % (args.controllerRestIp, args.srcAddress)
    elif args.type == "ip":
        command = "curl -s http://%s/wm/device/?ipv4=%s" % (args.controllerRestIp, args.srcAddress)
    elif args.type == "phy":
        # Need to translate vif:bridge to port:dpid
        command = "curl -s http://%s/wm/core/controller/switches/json" % (args.controllerRestIp)
        srcPort, srcSwitch = args.srcAddress.split(":")
    else:
        print "Invalid type: %s" % args.type
        sys.exit()

    result = os.popen(command).read()
    parsedResult = json.loads(result)
    print command+"\n"
    if args.type == "eth" or args.type == "ip":
        if len(parsedResult) > 0:
            sourceSwitch = parsedResult[0]['attachmentPoint'][0]['switchDPID']
            sourcePort = parsedResult[0]['attachmentPoint'][0]['port']
        else:
            print "Could not find device: %s" % args.srcAddress
            sys.exit()
    else:
        # Search for switch and port pair
        for sw in parsedResult:
            srcSwitchDpid = srcPortNumber = None
            for pt in sw['ports']:
                if pt['name'] == srcPort:
                    srcPortNumber = pt['portNumber']
                elif pt['name'] == srcSwitch:
                    srcSwitchDpid = sw['dpid']

            if not srcSwitchDpid is None or srcPortNumber is None:
                sourceSwitch = srcSwitchDpid
                sourcePort = srcPortNumber
    
    if args.type == "eth":
        command = "curl -s http://%s/wm/device/?mac=%s" % (args.controllerRestIp, args.dstAddress)
    elif args.type == "ip":
        command = "curl -s http://%s/wm/device/?ipv4=%s" % (args.controllerRestIp, args.dstAddress)
    elif args.type == "phy":
        # No need to read again the topology
        command = None
        dstPort, dstSwitch = args.dstAddress.split(":")
    if not command is None:
        result = os.popen(command).read()
        parsedResult = json.loads(result)
        print command+"\n"

    if args.type == "eth" or args.type == "ip":
        if len(parsedResult) > 0:
            destSwitch = parsedResult[0]['attachmentPoint'][0]['switchDPID']
            destPort = parsedResult[0]['attachmentPoint'][0]['port']
        else:
            print "Could not find device: %s" % args.dstAddress
            sys.exit()
    else:
        # Search for switch and port pair
        for sw in parsedResult:
            dstSwitchDpid = dstPortNumber = None
            for pt in sw['ports']:
                if pt['name'] == dstPort:
                    dstPortNumber = pt['portNumber']
                elif pt['name'] == dstSwitch:
                    dstSwitchDpid = sw['dpid']

            if not dstSwitchDpid is None or dstPortNumber is None:
                destSwitch = dstSwitchDpid
                destPort = dstPortNumber

    print "Creating circuit:"
    print "from source device at switch %s port %s" % (sourceSwitch, sourcePort)
    print "to destination device at switch %s port %s" % (destSwitch, destPort)
    
    # retrieving route from source to destination
    # using Routing rest API
    
    command = "curl -s http://%s/wm/topology/route/%s/%s/%s/%s/json" % (controllerRestIp, sourceSwitch, sourcePort, destSwitch, destPort)
    
    result = os.popen(command).read()
    parsedResult = json.loads(result)

    print command+"\n"
    print result+"\n"

    for i in range(len(parsedResult)):
        if i % 2 == 0:
            ap1Dpid = parsedResult[i]['switch']
            ap1Port = parsedResult[i]['port']
            print ap1Dpid, ap1Port
        else:
            ap2Dpid = parsedResult[i]['switch']
            ap2Port = parsedResult[i]['port']
            print ap2Dpid, ap2Port
            
            if args.type == "eth":
                addrType = "mac"
            else:
                addrType = "ip"

            # send one flow mod per pair of APs in route
            # using StaticFlowPusher rest API

            # IMPORTANT NOTE: current Floodlight StaticflowEntryPusher
            # assumes all flow entries to have unique name across all switches
            # this will most possibly be relaxed later, but for now we
            # encode each flow entry's name with both switch dpid, user
            # specified name, and flow type (f: forward, r: reverse, farp/rarp: arp)
            if args.type == "eth" or args.type == "ip":
                command = "curl -s -d '{\"switch\": \"%s\", \"name\":\"%s\", \"src-%s\":\"%s\", \"dst-%s\":\"%s\", \"ether-type\":\"%s\", \"cookie\":\"0\", \"priority\":\"32768\", \"ingress-port\":\"%s\",\"active\":\"true\", \"actions\":\"output=%s\"}' http://%s/wm/staticflowentrypusher/json" % (ap1Dpid, ap1Dpid+"."+args.circuitName+".f", addrType, args.srcAddress, addrType, args.dstAddress, "0x800", ap1Port, ap2Port, controllerRestIp)
                result = os.popen(command).read()
                print command

                command = "curl -s -d '{\"switch\": \"%s\", \"name\":\"%s\", \"ether-type\":\"%s\", \"cookie\":\"0\", \"priority\":\"32768\", \"ingress-port\":\"%s\",\"active\":\"true\", \"actions\":\"output=%s\"}' http://%s/wm/staticflowentrypusher/json" % (ap1Dpid, ap1Dpid+"."+args.circuitName+".farp", "0x806", ap1Port, ap2Port, controllerRestIp)
                result = os.popen(command).read()
                print command

                # Allow OSPF traffic
                command = "curl -s -d '{\"switch\": \"%s\", \"name\":\"%s\", \"ether-type\":\"%s\", \"protocol\":\"%s\", \"cookie\":\"0\", \"priority\":\"32768\", \"ingress-port\":\"%s\",\"active\":\"true\", \"actions\":\"output=%s\"}' http://%s/wm/staticflowentrypusher/json" % (ap1Dpid, ap1Dpid+"."+args.circuitName+".fospf", "0x800", 89, ap1Port, ap2Port, controllerRestIp)
                result = os.popen(command).read()
                print command

                command = "curl -s -d '{\"switch\": \"%s\", \"name\":\"%s\", \"src-%s\":\"%s\", \"dst-%s\":\"%s\", \"ether-type\":\"%s\", \"cookie\":\"0\", \"priority\":\"32768\", \"ingress-port\":\"%s\",\"active\":\"true\", \"actions\":\"output=%s\"}' http://%s/wm/staticflowentrypusher/json" % (ap1Dpid, ap1Dpid+"."+args.circuitName+".r", addrType, args.dstAddress, addrType, args.srcAddress, "0x800", ap2Port, ap1Port, controllerRestIp)
                result = os.popen(command).read()
                print command

                command = "curl -s -d '{\"switch\": \"%s\", \"name\":\"%s\", \"ether-type\":\"%s\", \"cookie\":\"0\", \"priority\":\"32768\", \"ingress-port\":\"%s\",\"active\":\"true\", \"actions\":\"output=%s\"}' http://%s/wm/staticflowentrypusher/json" % (ap1Dpid, ap1Dpid+"."+args.circuitName+".rarp", "0x806", ap2Port, ap1Port, controllerRestIp)
                result = os.popen(command).read()
                print command

                # Allow OSPF traffic
                command = "curl -s -d '{\"switch\": \"%s\", \"name\":\"%s\", \"ether-type\":\"%s\", \"protocol\":\"%s\", \"cookie\":\"0\", \"priority\":\"32768\", \"ingress-port\":\"%s\",\"active\":\"true\", \"actions\":\"output=%s\"}' http://%s/wm/staticflowentrypusher/json" % (ap1Dpid, ap1Dpid+"."+args.circuitName+".rospf", "0x800", 89, ap2Port, ap1Port, controllerRestIp)
                result = os.popen(command).read()
                print command

            else:
                # Physical links need only one rule
                command = "curl -s -d '{\"switch\": \"%s\", \"name\":\"%s\", \"priority\":\"32768\", \"ingress-port\":\"%s\", \"active\":\"true\", \"actions\":\"output=%s\"}' http://%s/wm/staticflowentrypusher/json" % (ap1Dpid, ap1Dpid+"."+args.circuitName+".f", ap1Port, ap2Port, controllerRestIp)
                result = os.popen(command).read()
                print command

                command = "curl -s -d '{\"switch\": \"%s\", \"name\":\"%s\", \"priority\":\"32768\", \"ingress-port\":\"%s\", \"active\":\"true\", \"actions\":\"output=%s\"}' http://%s/wm/staticflowentrypusher/json" % (ap1Dpid, ap1Dpid+"."+args.circuitName+".r", ap2Port, ap1Port, controllerRestIp)
                result = os.popen(command).read()
                print command

            # store created circuit attributes in local ./circuits.json
            datetime = time.asctime()
            circuitParams = {'name':args.circuitName, 'type': args.type, 'Dpid':ap1Dpid, 'inPort':ap1Port, 'outPort':ap2Port, 'datetime':datetime}
            str = json.dumps(circuitParams)
            circuitDb.write(str+"\n")

            # confirm successful circuit creation
            # using controller rest API
            
            command="curl -s http://%s/wm/core/switch/all/flow/json| python -mjson.tool" % (controllerRestIp)
            result = os.popen(command).read()
            print command + "\n" + result

elif args.action=='delete':
    
    circuitDb = open('/home/aurora/Aurora/cloud/helpers/circuits.json','w')

    # removing previously created flow from switches
    # using StaticFlowPusher rest API       
    # currently, circuitpusher records created circuits in local file ./circuits.db 
    # with circuit name and list of switches                                  

    circuitExists = False

    for line in lines:
        data = json.loads(line)
        if data['name']==(args.circuitName):
            circuitExists = True

            sw = data['Dpid']
            circuitType = data['type']
            print data, sw, circuitType

            command = "curl -X DELETE -d '{\"name\":\"%s\", \"switch\":\"%s\"}' http://%s/wm/staticflowentrypusher/json" % (sw+"."+args.circuitName+".f", sw, controllerRestIp)
            result = os.popen(command).read()
            print command, result

            command = "curl -X DELETE -d '{\"name\":\"%s\", \"switch\":\"%s\"}' http://%s/wm/staticflowentrypusher/json" % (sw+"."+args.circuitName+".r", sw, controllerRestIp)
            result = os.popen(command).read()
            print command, result

            if circuitType == "ip" or circuitType == "eth":
                command = "curl -X DELETE -d '{\"name\":\"%s\", \"switch\":\"%s\"}' http://%s/wm/staticflowentrypusher/json" % (sw+"."+args.circuitName+".farp", sw, controllerRestIp)
                result = os.popen(command).read()
                print command, result

                command = "curl -X DELETE -d '{\"name\":\"%s\", \"switch\":\"%s\"}' http://%s/wm/staticflowentrypusher/json" % (sw+"."+args.circuitName+".fospf", sw, controllerRestIp)
                result = os.popen(command).read()
                print command, result

                command = "curl -X DELETE -d '{\"name\":\"%s\", \"switch\":\"%s\"}' http://%s/wm/staticflowentrypusher/json" % (sw+"."+args.circuitName+".rarp", sw, controllerRestIp)
                result = os.popen(command).read()
                print command, result            

                command = "curl -X DELETE -d '{\"name\":\"%s\", \"switch\":\"%s\"}' http://%s/wm/staticflowentrypusher/json" % (sw+"."+args.circuitName+".rospf", sw, controllerRestIp)
                result = os.popen(command).read()
                print command, result            
            
        else:
            circuitDb.write(line)

    circuitDb.close()

    if not circuitExists:
        print "specified circuit does not exist"
        sys.exit()


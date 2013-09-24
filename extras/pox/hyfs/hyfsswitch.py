# Copyright 2011 James McCauley
#
# This file is part of POX.
#
# POX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# POX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with POX.  If not, see <http://www.gnu.org/licenses/>.

"""
This is an L2 learning switch written directly against the OpenFlow library.
It is derived from one written live for an SDN crash course.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpidToStr
from pox.lib.util import str_to_bool
from pox.web.webcore import SplitRequestHandler
import time
import json
import pprint

log = core.getLogger()

# We don't want to flood immediately when a switch connects.
FLOOD_DELAY = 5

# Contains the link information database
linkdb = {}

# General function to dump linkdb information to a file
def update_linkdb_file():
  global linkdb

  # Update file with persistent links
  f = file("linkdb.json", "w+")
  f.write(json.dumps(linkdb))
  f.close()

# Informs the current state of a link
def link_state(link_id):
  global linkdb
  log.info('State requested for link ' + link_id)
  if linkdb.has_key(link_id):
    return json.dumps(linkdb[link_id])
  else:
    log.warning('Link not found ' + link_id)
    return False

# Creates a new link on the database
def link_create(link):
  global linkdb
  log.info('Create new link')
  log.debug('Data: ' + str( link ))

  if link.has_key('id') and link.has_key('mac_start') and link.has_key('mac_end'):
    # Record link info in the local database
    link["state"] = "Established"
    linkdb[str(link["id"])] = link
  else:
    log.warning('Malformed link object ')
    return False

  # Update the file after adding every new link
  update_linkdb_file()

  return True

# Creates a set of links on the database all at once
def link_create_bundle(link_set):
  log.info('Create a set of links')

  for link in link_set:
    if not link_create(link):
      log.warning("Link set creation aborted")
      return False

  return True

# Deletes all links
def link_delete_all():
  global linkdb
  log.info('Deleting everything!!!')
  linkdb = {}
  update_linkdb_file()
  return True

# Deletes information about a link
def link_delete(link_id):
  global linkdb
  log.info('Delete link ' + link_id)
  if linkdb.has_key(link_id):
    del linkdb[link_id]
    update_linkdb_file()
    return True
  else:
    log.warning('Link not found ' + link_id)
    return False

# Determines if a link exists between macs src and dst
def is_allowed_path(src_mac, dst_mac):
  global linkdb
  for link in linkdb:
    if (linkdb[link]["mac_start"] == src_mac or linkdb[link]["mac_end"] == src_mac) and (linkdb[link]["mac_start"] == dst_mac or linkdb[link]["mac_end"] == dst_mac):
      log.info('Link found, install path\n\nLink Info: ' + str(link) + "\nMac src: "+ src_mac + "\nMac dst: "+ dst_mac)
      return True

  return False

class LearningSwitch (EventMixin):
  """
  The learning switch "brain" associated with a single OpenFlow switch.

  When we see a packet, we'd like to output it on a port which will
  eventually lead to the destination.  To accomplish this, we build a
  table that maps addresses to ports.

  We populate the table by observing traffic.  When we see a packet
  from some source coming from some port, we know that source is out
  that port.

  When we want to forward traffic, we look up the desintation in our
  table.  If we don't know the port, we simply send the message out
  all ports except the one it came in on.  (In the presence of loops,
  this is bad!).

  In short, our algorithm looks like this:

  For each new flow:
  1) Use source address and port to update address/port table
  2) Is destination address a Bridge Filtered address, or is Ethertpe LLDP?
     * This step is ignored if transparent = True *
     Yes:
        2a) Drop packet to avoid forwarding link-local traffic (LLDP, 802.1x)
            DONE
  3) Is destination multicast?
     Yes:
        3a) Flood the packet
            DONE
  4) Port for destination address in our address/port table?
     No:
        4a) Flood the packet
            DONE
  5) Is output port the same as input port?
     Yes:
        5a) Drop packet and similar ones for a while
  6) Install flow table entry in the switch so that this
     flow goes out the appopriate port
     6a) Send buffered packet out appopriate port
  """
  def __init__ (self, connection, transparent):
    # Switch we'll be adding L2 learning switch capabilities to
    self.connection = connection
    self.transparent = transparent

    # Our table
    self.macToPort = {}

    # We want to hear PacketIn messages, so we listen
    self.listenTo(connection)

    log.debug("Initializing LearningSwitch, transparent=%s",
              str(self.transparent))

  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch to implement above algorithm.
    """

    packet = event.parse()

    def flood ():
      """ Floods the packet """
      if event.ofp.buffer_id == -1:
        log.warning("Not flooding unbuffered packet on %s",
                    dpidToStr(event.dpid))
        return
      msg = of.ofp_packet_out()
      if time.time() - self.connection.connect_time > FLOOD_DELAY:
        # Only flood if we've been connected for a little while...
        log.debug("%i: flood %s -> %s", event.dpid, packet.src, packet.dst)
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
      else:
        pass
        log.info("Holding down flood for %s", dpidToStr(event.dpid))
      msg.buffer_id = event.ofp.buffer_id
      msg.in_port = event.port
      self.connection.send(msg)

    def drop (duration = None):
      """
      Drops this packet and optionally installs a flow to continue
      dropping similar ones for a while
      """
      if duration is not None:
        if not isinstance(duration, tuple):
          duration = (duration,duration)
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = duration[0]
        msg.hard_timeout = duration[1]
        msg.buffer_id = event.ofp.buffer_id
        self.connection.send(msg)
      elif event.ofp.buffer_id != -1:
        msg = of.ofp_packet_out()
        msg.buffer_id = event.ofp.buffer_id
        msg.in_port = event.port
        self.connection.send(msg)

    self.macToPort[packet.src] = event.port # 1

    if not self.transparent:
      if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered(): # 2
        drop()
        return

    if packet.dst.isMulticast():
      flood() # 3a
    else:
      # Check here if unicast traffic is allowed
      # Condition 1: Both source and destination have always allowed mac addresses (they are mininet nodes or switches)
      if not (str(packet.dst).startswith('00:00:00:1') or str(packet.src).startswith('00:00:00:1')):
        # Condition 2: there is a link defined between src and dst
        if not is_allowed_path(str(packet.src), str(packet.dst)):
          drop(2)
          return
      # If all conditions pass follow the normal flow
      if packet.dst not in self.macToPort: # 4
        log.debug("Port for %s unknown -- flooding" % (packet.dst,))
        flood() # 4a
      else:
        port = self.macToPort[packet.dst]
        if port == event.port: # 5
          # 5a
          log.warning("Same port for packet from %s -> %s on %s.  Drop." %
                      (packet.src, packet.dst, port), dpidToStr(event.dpid))
          drop(10)
          return
        # 6
        log.debug("installing flow for %s.%i -> %s.%i" %
                  (packet.src, event.port, packet.dst, port))
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = 10
        msg.hard_timeout = 30
        msg.actions.append(of.ofp_action_output(port = port))
        msg.buffer_id = event.ofp.buffer_id # 6a
        self.connection.send(msg)

class manager_handler (SplitRequestHandler):
  """Default handler for HTTP requests"""

  def do_GET (self):
    """Serve a GET request."""
    log.info("Received a GET")
    self.parse_request("GET", True)

  def do_PUT (self):
    """Serve a PUT request."""
    log.info("Received a PUT")
    length = int(self.headers.getheader('content-length'))
    data_string = self.rfile.read(length)
    log.debug(data_string)
    self.parse_request("PUT", True, data_string)

  def do_HEAD (self):
    """Serve a HEAD request."""
    log.info("Received a HEAD")
    self.parse_request("HEAD", False)

  def parse_request(self, method, respond=False, data=""):
    #The path identifies which service is being accessed (format is something like /link/create or /link/state/1)
    spath = self.path.split("/")
    log.debug("Path is " + self.path + "(" + str(spath) + ")")
    if len(spath) > 2:
      section = spath[1]
      action = spath[2]

      if section == 'link':
        if action == 'create' and method == 'PUT' and data != "":
          r = link_create(json.loads(data))
          if r == False:
            r = {"response": "cloud not create link"}
            self.send_response(500)
          else:
            r = {"response": "link created successfully"}
            self.send_response(200)
        elif action == 'create_bundle' and method == 'PUT' and data != "":
          r = link_create_bundle(json.loads(data))
          if r == False:
            r = {"response": "cloud not create link bundle"}
            self.send_response(500)
          else:
            r = {"response": "link created successfully"}
            self.send_response(200)
        elif action == 'delete' and method == 'GET' and len(spath) == 4:
          r = link_delete(spath[3])
          if r == False:
            r = {"response": "link not found"}
            self.send_response(404)
          else:
            self.send_response(200)
        elif action == 'delete_all' and method == 'GET':
          r = link_delete_all()
          if r == False:
            r = {"response": "could not clean link database"}
            self.send_response(500)
          else:
            self.send_response(200)
        elif action == 'state' and method == 'GET' and len(spath) == 4:
          r = link_state(spath[3])
          if r == False:
            r = {"response": "link not found"}
            self.send_response(404)
          else:
            self.send_response(200)
        else:
          r = {"response": "wrong action or parameters: " + action}
          self.send_response(404)  
      else:
        r = {"response": "unknown section: " + section}
        self.send_response(404)

    else:
      r = {"response": "malformed path"}
      self.send_response(404)

    self.send_header("Content-type", "application/json")
    self.send_header("Content-Length", len(str(r)))
    self.end_headers()

    log.debug("Replied: " + str(r))
    if respond:
      self.wfile.write(r)


class l2_learning (EventMixin):
  """
  Waits for OpenFlow switches to connect and makes them learning switches.
  """
  def __init__ (self, transparent):
    self.listenTo(core.openflow)
    self.transparent = transparent

  def _handle_ConnectionUp (self, event):
    log.debug("Connection %s" % (event.connection,))
    LearningSwitch(event.connection, self.transparent)

def launch (transparent=False):
  """
  Starts an L2 learning switch.
  """
  core.registerNew(l2_learning, str_to_bool(transparent))

  core.WebServer.set_handler("/manager", manager_handler)

  # Load persistent links from file (or creates a new one)
  global linkdb
  f = file("linkdb.json", "a+")
  content = f.read()
  if content != '':
    linkdb = json.loads(content)
    log.debug("Link database initialized: " + str(linkdb))
  f.close()


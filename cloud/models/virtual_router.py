import commands
import logging
import socket
import time
from django.db import models
from cloud.models.virtual_device import VirtualDevice

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Supported routing protocols
ROUTING_PROTOCOLS = (
        (u'openflow', u'OpenFlow'),
        (u'bgp', u'BGP'),
        (u'ospf', u'OSPF'),
        (u'rip', u'RIP'),
)

# Control Plane types
CP_TYPES = (
        (u'dynamic', u'Dynamic'),
        (u'static', u'Static'),
)

class VirtualRouter(VirtualDevice):

    host = models.ForeignKey(
        'Host',
        verbose_name="Connected to",
        blank=True,
        null=True
    )
    cp_routing_protocol = models.CharField(max_length=10, choices=ROUTING_PROTOCOLS, default='openflow', db_index=True)
    cp_type = models.CharField(max_length=10, choices=CP_TYPES, default='dynamic', db_index=True)

    # Bridge name
    dev_name = models.CharField(max_length=15, db_index=True)

    def current_state(self):

        if self.host == None:
            return "Not Deployed"
        else:
            h_ip = socket.gethostbyname(self.host.hostname)
            out = commands.getstatusoutput('ovs-vsctl --db=tcp:' + h_ip + ':8888 --timeout=3 br-exists "' + self.dev_name + '"')
            if out[0] != 0:
                return "Not Found"
            else:
                return "Active"

    def deploy(self):
        # Details of deployment times
        t0 = time.time()

        state = self.current_state()
        
        if self.host is not None:
            h_ip = socket.gethostbyname(self.host.hostname)

        if state == "Not Deployed" or state == "Not Found":
            out = commands.getstatusoutput('ovs-vsctl --db=tcp:' + h_ip + ':8888 --timeout=3 add-br "' + self.dev_name + '"')
            if out[0] != 0:
                raise self.VirtualRouterException('Could not deploy Virtual Router: %s %s' % (self.dev_name, out[1]))

        # Configures controllers
        if self.cp_routing_protocol == "openflow":
            controllers = self.remotecontroller_set.order_by("controller_type")
            if controllers:
                c_str = ""
                for c in controllers:
                    # Generates a space separated list of controllers (the connection is already formatted by the __unicode__ of the controller object)
                    c_str += " " + str(c)

        # Allways update the list of controllers, which may be empty
        out = commands.getstatusoutput('ovs-vsctl --db=tcp:' + h_ip + ':8888 set-controller "' + self.dev_name + '" ' + c_str)
        if out[0] != 0:
            raise self.VirtualRouterException('Could not set controllers for: %s %s' % (self.dev_name, out[1]))

        # Time spent defining and saving
        define_time = time.time() - t0

        return {"define_time": define_time}

    def undeploy(self):
        if self.current_state() == "Active":
            h_ip = socket.gethostbyname(self.host.hostname)
            out = commands.getstatusoutput('ovs-vsctl --db=tcp:' + h_ip + ':8888 --timeout=3 del-br "' + self.dev_name + '"')
            if out[0] != 0:
                raise self.VirtualRouterException('Could not undeploy Virtual Router: %s %s' % (self.dev_name, out[1]))

        return True

    # If a Switch belongs to a slice it should have the slice name as suffix
    def save(self, *args, **kwargs):
        if self.belongs_to_slice != None:
            slice_name = self.belongs_to_slice.name
            # If Switch name is shorter than the slice name, it means there is no suffix
            # Or of the suffix is not found in the name
            if len(self.name) <= len(slice_name) or self.name[-len(slice_name):] != slice_name:
                self.name += "-" + slice_name

        # Use normal save from model
        super(VirtualRouter, self).save(*args, **kwargs)

        need_to_save = False

        # Id exists dev_name
        if not self.dev_name:
            self.dev_name = "br" + str(self.id)
            need_to_save = True

        if need_to_save:
            # This save will update changed information
            self.save()


    def __unicode__(self):
        return self.name

    class VirtualRouterException(VirtualDevice.VirtualDeviceException):
        pass

    # Makes django recognize model in split modules
    class Meta:
        app_label = 'cloud'


import json
import logging
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring, tostring
from django.db import models, transaction
from django.contrib.auth.models import User
from cloud.models.virtual_machine import VirtualMachine
from cloud.models.image import Image
from cloud.models.virtual_link import VirtualLink
from cloud.models.virtual_link_qos import VirtualLinkQos
from cloud.models.virtual_interface import VirtualInterface
from cloud.models.base_model import BaseModel
from cloud.models.remote_controller import RemoteController
from cloud.models.virtual_router import VirtualRouter
from cloud.models.deployment_program import DeploymentProgram
from cloud.models.optimization_program import OptimizationProgram

# Get an instance of a logger
logger = logging.getLogger(__name__)

SLICE_STATES = (
        (u'created', u'Created'),
        (u'deploying', u'Deploying'),
        (u'deployed', u'Deployed'),
        (u'optimizing', u'Optimizing'),
        (u'disabled', u'Disabled'),
)

class Slice(BaseModel):

    name = models.CharField(max_length=200)
    state = models.CharField(max_length=10, choices=SLICE_STATES, default='created', db_index=True)
    owner = models.ForeignKey(
        User,
        verbose_name="Slice Owner",
    )
    deployed_with = models.ForeignKey(
        DeploymentProgram,
        verbose_name="Deployed with program",
        null=True,
        on_delete=models.SET_NULL,
    )
    optimized_by = models.ManyToManyField(
        OptimizationProgram,
        verbose_name="Optimized by",
        through='OptimizesSlice',
    )

    def total_virtual_machines(self):
        return VirtualMachine.objects.filter(belongs_to_slice=self).count()

    def total_virtual_routers(self):
        return VirtualRouter.objects.filter(belongs_to_slice=self).count()

    def total_virtual_links(self):
        return self.virtuallink_set.count()

    def current_state(self):
        return self.get_state_display()

    @transaction.commit_on_success
    def save_from_vxdl(self, vxdl):

        # Saves the slice to get an id
        self.save()

        # Whole virtual infrastructure
        v_infra = fromstring(vxdl)

        # Temporary mapping to associate vNodes with the actual VM and Interface objects
        vm_mapping = {}

        # Same thing for vRouters
        vr_mapping = {}

        # VMs
        v_nodes = v_infra.findall("vNode")
        i = 0
        for v_node in v_nodes:
            # Every v_node is a new VM
            vm = VirtualMachine()
            # VMs are associate with the current slice
            vm.belongs_to_slice = self
            if v_node.attrib.has_key("id"):
                v_node_id = v_node.attrib["id"]
            else:
                v_node_id = "vm" + str(i)

            vm.name = v_node_id
            logger.debug('Creating new Virtual Machine from VXDL ' + vm.name)

            # VM memory
            v_mem = v_node.find("memory/simple")
            v_mem_unit = v_node.find("memory/unit")
            if v_mem != None and v_mem_unit != None:
                if v_mem_unit.text == "TB":
                    multiplier = 1024*1024*1024
                elif v_mem_unit.text == "GB":
                    multiplier = 1024*1024
                elif v_mem_unit.text == "MB":
                    multiplier = 1024
                else:
                    multiplier = 1

                vm.memory = int( v_mem.text ) * multiplier
                logger.debug("Memory: " + v_mem.text + " " + v_mem_unit.text + " Multiplier: " + str(multiplier))
            else:
                # Default memory amount
                vm.memory = 128*1024
                logger.debug("Memory set to default: " + str(vm.memory))

            # VM vCPU
            v_cpu = v_node.find("cpu/cores/simple")
            if v_cpu != None:
                vm.vcpu = int( v_cpu.text )
            else:
                # Default number of CPUs
                vm.vcpu = 1

            logger.debug("CPU: " + str(vm.vcpu))

            # VM image (volatile)
            v_image = v_node.find("image")
            if v_image != None:
                images = Image.objects.filter(name=v_image.text)
                if len(images) > 0:
                    vm.image = images[0]
                else:
                    vm.image = None
            else:
                vm.image = None

            if vm.image == None:
                logger.warning('Could not determine Virtual Machine image: ' + v_image.text)
                raise self.VXDLException('Could not determine Virtual Machine image: ' + v_image.text)
            logger.debug("Image: " + str(vm.image))

            # Saves associated VM to get an id
            vm.save()

            # Network interfaces
            v_ifs = v_node.findall("interface")
            j = 0
            for v_if in v_ifs:
                interface = VirtualInterface()
                interface.attached_to = vm

                # Interface alias
                v_if_alias = v_if.find("alias")
                if v_if_alias != None:
                    interface.alias = v_if_alias.text
                else:
                    interface.alias = "veth" + str(j)

                # Type of network (e.g. bridge or NAT)
                v_if_type = v_if.find("type")
                if v_if_type != None:
                    if v_if_type.text == "NAT":
                        interface.if_type = "network"
                    else:
                        interface.if_type = v_if_type.text
                else:
                    interface.if_type = "bridge"

                # Interface mac address (optional), will auto generate if omitted
                v_if_mac = v_if.find("macaddress")
                if v_if_mac != None:
                    interface.mac_address = v_if_mac.text

                logger.debug("Network interface: " + interface.alias)

                interface.save()

                j = j + 1

            # Put vm in the temporary mapping
            vm_mapping[v_node_id] = vm

            i = i + 1

        # Controller list
        controller_lists = []
        v_clists = v_infra.findall("controllerList")
        for v_clist in v_clists:
            if v_clist.attrib.has_key("id"):
                v_clist_id = v_clist.attrib["id"]
            else:
                # Controller list must have id
                logger.warning('Error! Controller list must have an attribute id.')
                raise self.VXDLException('Error! Controller list must have an attribute id.')

            controller_list = {
                'id': v_clist_id,
                'controllers': []
            }

            # Now find controllers
            v_controllers = v_clist.findall("controller")
            for v_controller in v_controllers:
                # Controllers are implemented as Remote Controller objects
                controller = RemoteController()
                # Associate with the current slice
                controller.belongs_to_slice = self
                logger.debug('Creating Remote Controller from VXDL')

                if v_controller.attrib.has_key("type"):
                    controller.controller_type = v_controller.attrib['type']
                else:
                    controller.controller_type = 'master'

                v_connectionType = v_controller.find("connectionType")
                if v_connectionType != None:
                    controller.connection = v_connectionType.text
                else:
                    controller.connection = 'tcp'

                v_ipAddress = v_controller.find("ipAddress")
                if v_ipAddress != None:
                    controller.ip = v_ipAddress.text
                else:
                    # Controller list must have id
                    logger.warning('Error! Controller IP address must be specified.')
                    raise self.VXDLException('Error! Controller IP address must be specified.')

                v_port = v_controller.find("port")
                if v_port != None:
                    controller.port = v_port.text
                else:
                    controller.port = '6633'

                # Saves associated Link
                controller.save()

                controller_list['controllers'].append(controller)

            controller_lists.append(controller_list)

        # Routers
        i = 0
        v_routers = v_infra.findall("vRouter")
        for v_router in v_routers:
            # Every v_router is a new Virtual Router
            vr = VirtualRouter()
            # Associate with the current slice
            vr.belongs_to_slice = self
            if v_router.attrib.has_key("id"):
                v_router_id = v_router.attrib["id"]
            else:
                v_router_id = "vr" + str(i)

            vr.name = v_router_id
            logger.debug('Creating new Virtual Router from VXDL ' + vr.name)

            v_controlPlane = v_router.find("controlPlane")
            if v_controlPlane != None:
                if v_controlPlane.attrib.has_key("type"):
                    vr.cp_type = v_controlPlane.attrib["type"]
                else:
                    vr.cp_type = "dynamic"

                if v_controlPlane.attrib.has_key("routingProtocol"):
                    vr.cp_routing_protocol = v_controlPlane.attrib["routingProtocol"].lower()
                else:
                    vr.cp_routing_protocol = "openflow"
            else:
                # Routers must have control plane
                logger.warning('Error! Virtual Routers must have a controlPlane tag.')
                raise self.VXDLException('Error! Virtual Routers must have a controlPlane tag.')

            # Will deploy later
            vr.host = None

            vr.save()

            # Associate router with openflow controllers
            if vr.cp_routing_protocol == "openflow":
                found = False
                for controller_list in controller_lists:
                    if v_controlPlane.text == controller_list['id']:
                        for controller in controller_list['controllers']:
                            controller.controls_vrouters.add(vr)
                        found = True
                        break

                if not found:
                    # Openflow Routers must have at least one controller associated
                    raise self.VXDLException('Error! Virtual Routers with OpenFlow must have at least one controller associated.')


            # Put vr in the temporary mapping
            vr_mapping[v_router_id] = vr

            i = i + 1

        # Links
        v_links = v_infra.findall("vLink")
        for v_link in v_links:
            # Every v_link is a new Link
            link = VirtualLink()
            # Links are associate with the current slice
            link.belongs_to_slice = self
            logger.debug('Creating Link from VXDL')

            # Link Source Host/Interface
            v_source = v_link.find("source/vNode")
            v_source_int = v_link.find("source/interface")
            if v_source != None and v_source_int != None:
                # Tries to find the VM and its interface in the mapping
                if vm_mapping.has_key(v_source.text):
                    # Should return an array with exactly one interface based on the alias
                    if_starts = vm_mapping[v_source.text].virtualinterface_set.filter(alias=v_source_int.text)
                    if len(if_starts) == 1:
                        link.if_start = if_starts[0]
                        logger.debug('Source ' + v_source.text + " " + v_source_int.text)
                    else:
                        # Not possible to create link, so abort the whole slice creation
                        logger.warning('Incorrect alias for source, will not create virtual link: ' + v_source.text + ' ' + v_source_int.text)
                        raise self.VXDLException('Incorrect alias for source, will not create virtual link: ' + v_source.text + ' ' + v_source_int.text)
            else:
                # Link Source Router
                v_source = v_link.find("source/vRouter")
                if v_source != None:
                    # Tries to find the Virtual Router in the mapping
                    if vr_mapping.has_key(v_source.text):
                        # Routers have no interface on VXDL, so we need to create one
                        interface = VirtualInterface()
                        interface.alias = "port" + str(vr_mapping[v_source.text].virtualinterface_set.count())
                        interface.attached_to = vr_mapping[v_source.text]
                        interface.save()

                        # Associate newly created interface with link
                        link.if_start = interface
                        logger.debug('Source ' + v_source.text + " " + interface.alias)
                    else:
                        # Not possible to create link, so abort the whole slice creation
                        logger.warning('Incorrect alias for source, will not create virtual link: ' + v_source.text)
                        raise self.VXDLException('Incorrect alias for source, will not create virtual link: ' + v_source.text)
                else:
                    # Cannot create link if don't know source
                    logger.warning('Source not specified, will not create virtual link')
                    raise self.VXDLException('Source not specified, will not create virtual link')

            # Link Destination Host/Interface
            v_dest = v_link.find("destination/vNode")
            v_dest_int = v_link.find("destination/interface")
            if v_dest != None and v_dest_int != None:
                # Tries to find the VM and its interface in the mapping
                if vm_mapping.has_key(v_dest.text):
                    # Should return an array with exactly one interface based on the alias
                    if_ends = vm_mapping[v_dest.text].virtualinterface_set.filter(alias=v_dest_int.text)
                    if len(if_ends) == 1:
                        link.if_end = if_ends[0]
                        logger.debug('Source ' + v_dest.text + " " + v_dest_int.text)
                    else:
                        # Not possible to create link, so abort the whole slice creation
                        logger.warning('Incorrect alias for source, will not create virtual link: ' + v_dest.text + ' ' + v_dest_int.text)
                        raise self.VXDLException('Incorrect alias for source, will not create virtual link: ' + v_dest.text + ' ' + v_dest_int.text)
            else:
                # Link Destination Router
                v_dest = v_link.find("destination/vRouter")
                if v_dest != None:
                    # Tries to find the Virtual Router in the mapping
                    if vr_mapping.has_key(v_dest.text):
                        # Routers have no interface on VXDL, so we need to create one
                        interface = VirtualInterface()
                        interface.alias = "port" + str(vr_mapping[v_dest.text].virtualinterface_set.count())
                        interface.attached_to = vr_mapping[v_dest.text]
                        interface.save()

                        # Associate newly created interface with link
                        link.if_end = interface
                        logger.debug('Destination ' + v_dest.text + " " + interface.alias)
                    else:
                        # Not possible to create link, so abort the whole slice creation
                        logger.warning('Incorrect alias for destination, will not create virtual link: ' + v_dest.text)
                        raise self.VXDLException('Incorrect alias for destination, will not create virtual link: ' + v_dest.text)
                else:
                    # Cannot create link if don't know destination
                    logger.warning('Destination not specified, will not create virtual link')
                    raise self.VXDLException('Destination not specified, will not create virtual link')

            # Saves associated Link
            link.save()

            # Process QoS information associated with link
            link_qos = VirtualLinkQos()
            link_qos.belongs_to_virtual_link = link

            # Upload bandwidth
            bandwidth_up = v_link.find("bandwidth/forward")
            link_qos.bandwidth_up_maximum = 0
            link_qos.bandwidth_up_committed = 0
            if bandwidth_up != None:
                bw_up_max = bandwidth_up.find("interval/max")
                bw_up_min = bandwidth_up.find("interval/min")
                bw_up_uni = bandwidth_up.find("unit")

                # When both are set
                if bw_up_max != None and bw_up_min != None:
                    link_qos.bandwidth_up_maximum = round(float(bw_up_max.text))
                    link_qos.bandwidth_up_committed = round(float(bw_up_min.text) / float(bw_up_max.text) * 100)
                # Only min is set
                elif bw_up_min != None:
                    link_qos.bandwidth_up_maximum = round(float(bw_up_min.text))
                    link_qos.bandwidth_up_committed = 100
                # Only max is set
                elif bw_up_max != None:
                    link_qos.bandwidth_up_maximum = round(float(bw_up_max.text))
                    link_qos.bandwidth_up_committed = 0

                # Unit conversion
                if bw_up_uni != None and link_qos.bandwidth_up_maximum > 0:
                    if bw_up_uni.text == "bps":
                        link_qos.bandwidth_up_maximum = round(link_qos.bandwidth_up_maximum / (1024 * 1024))
                    elif bw_up_uni.text == "Kbps":
                        link_qos.bandwidth_up_maximum = round(link_qos.bandwidth_up_maximum / 1024)
                    elif bw_up_uni.text == "Gbps":
                        link_qos.bandwidth_up_maximum = round(link_qos.bandwidth_up_maximum * 1024)

                    # Make sure bandwith is at least 1Mbps after this conversion
                    if link_qos.bandwidth_up_maximum < 1:
                        link_qos.bandwidth_up_maximum = 1

            # Download bandwidth
            bandwidth_down = v_link.find("bandwidth/reverse")
            link_qos.bandwidth_down_maximum = 0
            link_qos.bandwidth_down_committed = 0
            if bandwidth_down != None:
                bw_down_max = bandwidth_down.find("interval/max")
                bw_down_min = bandwidth_down.find("interval/min")
                bw_down_uni = bandwidth_down.find("unit")

                # When both are set
                if bw_down_max != None and bw_down_min != None:
                    link_qos.bandwidth_down_maximum = round(float(bw_down_max.text))
                    link_qos.bandwidth_down_committed = round(float(bw_down_min.text) / float(bw_down_max.text) * 100)
                # Only min is set
                elif bw_down_min != None:
                    link_qos.bandwidth_down_maximum = round(float(bw_down_min.text))
                    link_qos.bandwidth_down_committed = 100
                # Only max is set
                elif bw_down_max != None:
                    link_qos.bandwidth_down_maximum = round(float(bw_down_max.text))
                    link_qos.bandwidth_down_committed = 0

                # Unit conversion
                if bw_down_uni != None and link_qos.bandwidth_down_maximum > 0:
                    if bw_down_uni.text == "bps":
                        link_qos.bandwidth_down_maximum = round(link_qos.bandwidth_down_maximum / (1024 * 1024))
                    elif bw_down_uni.text == "Kbps":
                        link_qos.bandwidth_down_maximum = round(link_qos.bandwidth_down_maximum / 1024)
                    elif bw_down_uni.text == "Gbps":
                        link_qos.bandwidth_down_maximum = round(link_qos.bandwidth_down_maximum * 1024)

                    # Make sure bandwith is at least 1Mbps after this conversion
                    if link_qos.bandwidth_down_maximum < 1:
                        link_qos.bandwidth_down_maximum = 1

            # Latency
            link_qos.latency = 0
            latency = v_link.find("latency")
            if latency != None:
                latency_max = latency.find("interval/max")
                latency_uni = latency.find("unit")

                if latency_max != None:
                    link_qos.latency = round(float(latency_max.text))

                # Unit conversion
                if latency_uni != None and link_qos.latency > 0:
                    if latency_uni.text == "us":
                        link_qos.latency = round(link_qos.latency / 1000)
                    elif latency_uni.text == "s":
                        link_qos.latency = round(link_qos.latency * 1000)

                    # Make sure latency is at least 1ms after this conversion
                    if link_qos.latency < 1:
                        link_qos.latency = 1

            # Saves associated QoS information
            link_qos.save()

        return True

    def get_json_graph_data(self):

        vms = VirtualMachine.objects.filter(belongs_to_slice=self)
        vrs = VirtualRouter.objects.filter(belongs_to_slice=self)

        json_data = []

        # TODO: Complete json description with more complex information (e.g., link capacity or VM capacities)
        for vm in vms:
            ifs = vm.virtualinterface_set.all()
            adjacencies = []
            for intf in ifs:
                links = intf.virtuallink_set_start.all()
                for link in links:
                    adjacencies.append(str(link.if_end.attached_to_id))

            vm_info = {
                "adjacencies": adjacencies,
                "id": str(vm.id),
                "name": vm.name,
                "data": {
                    "$color": "#416D9C",
                    "$type": "circle",
                    "$dim": 10
                }
            }
            json_data.append(vm_info)

        for vr in vrs:
            ifs = vr.virtualinterface_set.all()
            adjacencies = []
            for intf in ifs:
                links = intf.virtuallink_set_start.all()
                for link in links:
                    adjacencies.append(str(link.if_end.attached_to_id))

            vm_info = {
                "adjacencies": adjacencies,
                "id": str(vr.id),
                "name": vr.name,
                "data": {
                    "$color": "#77D4F9",
                    "$type": "square",
                    "$dim": 10
                }
            }
            json_data.append(vm_info)

        return json.dumps(json_data)

    def __unicode__(self):
        return self.name

    class SliceException(BaseModel.ModelException):
        pass

    # Exception to throw when there is problems with the VXDL input file
    # (should roll back the whole slice creation)
    class VXDLException(SliceException):
        pass

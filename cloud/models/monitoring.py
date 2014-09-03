import base64
import httplib
import logging
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring, tostring
from django.db import models
from cloud.models.base_singleton_model import BaseSingletonModel
from cloud.models.slice import Slice
from cloud.models.virtual_device import VirtualDevice

# Configure logging for the module name
logger = logging.getLogger(__name__)


class Monitoring(BaseSingletonModel):
    """Connection with the monitoring system

    Implements basic functionality to communicate with the external monitoring
    system. It is a singleton model, this means it stores basically settings.
    """

    name = models.CharField(max_length=100,
        default='Generic Monitoring System')
    hostname = models.CharField(max_length=200,
        default='www.example-monitoring.com')
    path = models.CharField(max_length=200, default='/deploy')
    username = models.CharField(max_length=100, default='')
    password = models.CharField(max_length=100, default='')

    def deploy_infrastructure(self, slice):
        """Deploy monitoring infrastructure for a slice

        Currently deploys the whole infrastructe every time it is called. The
        monitoring system is able to detect changes and update where necessary.
        """
        # POST to get_flexcms_xml()
        # Full URL http://flexcms.inf.ufrgs.br/flexcms/platforms.xml
        username = self.username
        password = self.password
        host = self.hostname
        request = self.generate_flexcms_platform_xml()

        #Connect to remote system
        webservice = httplib.HTTP(host)
        webservice.putrequest("POST", self.path)
        if username != '' and password != '':
            auth = base64.encodestring('%s:%s' %
                (username, password)).replace('\n', '')
            webservice.putheader("Authorization", "Basic %s" % auth)
        webservice.putheader("Host", host)
        webservice.putheader("User-Agent", "Python post")
        webservice.putheader("Content-type", "text/xml; charset=\"UTF-8\"")
        webservice.putheader("Content-length", "%d" % len(request))
        webservice.endheaders()
        webservice.send(request)
        statuscode, statusmessage, header = webservice.getreply()
        result = webservice.getfile().read()
        logger.debug("Deploying slice %s monitoring infrastructure: %s %s" %
            (str(slice), str(statuscode), statusmessage))
        logger.debug("Deployment result: %s " % (str(result)))

    def generate_flexcms_platform_xml(self):
        # Create XML object structure root for the platform
        platform = ET.Element('platform')
        identifier = ET.SubElement(platform, 'identifier')
        identifier.text = 'cloud'
        cloud_attr = ET.SubElement(platform, 'cloud_attributes',
            attrib={'type': 'array'})
        slices = Slice.objects.filter(state="deployed")
        for s in slices:
            cloud_attr.append(self.generate_flexcms_cloud_xml_obj(s))

        # Includes unbound devices
        cloud_attr.append(self.generate_flexcms_cloud_xml_obj(None))
        xml_out = '<?xml version="1.0" encoding="UTF-8"?>'
        return xml_out + tostring(platform)

    # When slice is None generates a "cloud" of unbound devices
    def generate_flexcms_cloud_xml_obj(self, slice):
        # Slice is represented as Cloud object in FlexCMS
        cloud = ET.Element('cloud')
        identifier = ET.SubElement(cloud, 'identifier')
        if slice is not None:
            identifier.text = slice.name
            devices = slice.virtualdevice_set.all()
        else:
            identifier.text = "Unbound Devices"
            devices = VirtualDevice.objects.filter(belongs_to_slice=None)

        # List of Virtual Devices (actually called Slices in FlexCMS)
        slice_attr = ET.SubElement(cloud, 'slices_attributes',
            attrib={'type': 'array'})
        for dev in devices:
            slice_attr.append(self.generate_flexcms_slice_xml_obj(dev))

        return cloud

    def generate_flexcms_cloud_xml(self, slice):
        return tostring(self.generate_flexcms_cloud_xml_obj(slice))

    def generate_flexcms_slice_xml_obj(self, device):
        # Virtual Device are represented as Slice object in FlexCMS
        slice = ET.Element('slice')
        identifier = ET.SubElement(slice, 'identifier')
        identifier.text = device.name

        if device.is_virtual_machine() and device.virtualmachine.current_state() != 'not deployed':
            slice.append(
                self.generate_flexcms_vm_info_xml_obj(device.virtualmachine))
            slice.append(
                self.generate_flexcms_vm_resources_xml_obj(
                    device.virtualmachine))
        return slice

    def generate_flexcms_slice_xml(self, device):
        return tostring(self.generate_flexcms_slice_xml_obj(device))

    def generate_flexcms_vm_info_xml_obj(self, vm):
        # List of information attributes for a VM (called Slice in FlexCMS)
        slice_info_attr = ET.Element('slice_information_attributes',
            attrib={'type': 'array'})
        # Status
        slice_info = ET.SubElement(slice_info_attr, 'slice_information')
        name = ET.SubElement(slice_info, 'name')
        name.text = 'status'
        value = ET.SubElement(slice_info, 'value')
        if vm.current_state() == 'not deployed':
            value.text = 'INACTIVE'
        else:
            value.text = 'ACTIVE'

        # TODO: Allow changing VM type in the future. For now only
        # libvirt_generic_host is available.

        # VM Type
        slice_info = ET.SubElement(slice_info_attr, 'slice_information')
        name = ET.SubElement(slice_info, 'name')
        name.text = 'type'
        value = ET.SubElement(slice_info, 'value')
        value.text = 'libvirt_generic_host'
        # Guest Status
        slice_info = ET.SubElement(slice_info_attr, 'slice_information')
        name = ET.SubElement(slice_info, 'name')
        name.text = 'guest_status'
        value = ET.SubElement(slice_info, 'value')
        value.text = vm.current_state()
        # Pysical host
        if vm.host is not None:
            slice_info = ET.SubElement(slice_info_attr, 'slice_information')
            name = ET.SubElement(slice_info, 'name')
            name.text = 'physical_hostname'
            value = ET.SubElement(slice_info, 'value')
            value.text = vm.host.hostname
        # Image
        if vm.image is not None:
            slice_info = ET.SubElement(slice_info_attr, 'slice_information')
            name = ET.SubElement(slice_info, 'name')
            name.text = 'image_name'
            value = ET.SubElement(slice_info, 'value')
            value.text = vm.image.name

        return slice_info_attr

    def generate_flexcms_vm_info_xml(self, vm):
        return tostring(self.generate_flexcms_vm_info_xml_obj(vm))

    def generate_flexcms_vm_resources_xml_obj(self, vm):
        # List of resource attributes for a VM (called Slice in FlexCMS)
        resource_attr = ET.Element('resource_attributes',
            attrib={'type': 'array'})

        # CPU
        resource = ET.SubElement(resource_attr, 'resource')
        identifier = ET.SubElement(resource, 'identifier')
        identifier.text = 'vcpus'
        resource_info_attr = ET.SubElement(resource,
            'resource_information_attributes', attrib={'type': 'array'})
        resource_info = ET.SubElement(resource_info_attr,
            'resource_information')
        name = ET.SubElement(resource_info, 'name')
        name.text = 'amount'
        value = ET.SubElement(resource_info, 'value')
        value.text = str(vm.vcpu)

        # RAM
        resource = ET.SubElement(resource_attr, 'resource')
        identifier = ET.SubElement(resource, 'identifier')
        identifier.text = 'ram'
        resource_info_attr = ET.SubElement(resource,
            'resource_information_attributes', attrib={'type': 'array'})
        resource_info = ET.SubElement(resource_info_attr,
            'resource_information')
        name = ET.SubElement(resource_info, 'name')
        name.text = 'amount'
        value = ET.SubElement(resource_info, 'value')
        value.text = str(vm.memory / 1024)

        # Disk
        resource = ET.SubElement(resource_attr, 'resource')
        identifier = ET.SubElement(resource, 'identifier')
        identifier.text = 'root_disk'
        resource_info_attr = ET.SubElement(resource,
            'resource_information_attributes', attrib={'type': 'array'})
        resource_info = ET.SubElement(resource_info_attr,
            'resource_information')
        name = ET.SubElement(resource_info, 'name')
        name.text = 'amount'
        value = ET.SubElement(resource_info, 'value')
        value.text = str(vm.get_main_disk_size() / 1024 / 1024 / 1024)

        # Disk device
        resource_info = ET.SubElement(resource_info_attr,
            'resource_information')
        name = ET.SubElement(resource_info, 'name')
        name.text = 'device'
        value = ET.SubElement(resource_info, 'value')
        value.text = vm.get_main_disk_device()

        # Network device
        resource = ET.SubElement(resource_attr, 'resource')
        identifier = ET.SubElement(resource, 'identifier')
        identifier.text = 'root_interface'
        resource_info_attr = ET.SubElement(resource,
            'resource_information_attributes', attrib={'type': 'array'})
        resource_info = ET.SubElement(resource_info_attr,
            'resource_information')
        name = ET.SubElement(resource_info, 'name')
        name.text = 'device'
        value = ET.SubElement(resource_info, 'value')
        value.text = vm.get_main_interface_device()

        return resource_attr

    def generate_flexcms_vm_resources_xml(self, vm):
        return tostring(self.generate_flexcms_vm_resources_xml_obj(vm))

    def __unicode__(self):
        return self.name

    class MonitoringException(BaseSingletonModel.SingletonModelException):
        pass

    # Makes django recognize model in split modules
    class Meta:
        app_label = 'cloud'


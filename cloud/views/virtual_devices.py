import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from cloud.models.virtual_router import VirtualRouter
from cloud.models.virtual_machine import VirtualMachine
from cloud.models.virtual_device import VirtualDevice

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Webservice to get virtual devices of a given type
@login_required
def virtual_devices(request, virtual_device_type):
    
    if virtual_device_type == "virtual_routers":
        dev_list = VirtualRouter.objects.all()
    elif virtual_device_type == "virtual_machines":
        dev_list = VirtualMachine.objects.all()
    else:
        dev_list = []
    
    output = []
    for dev in dev_list:
        output.append([
            dev.id,
            str( dev )
        ])
    
    return HttpResponse(json.dumps(output), mimetype='application/json')

# Webservice to get virtual interface details for a given device
@login_required
def virtual_interfaces(request, virtual_device_id):
    try:
        dev = VirtualDevice.objects.get(pk=virtual_device_id)
    except VirtualDevice.DoesNotExist:
        raise Http404

    if_list = dev.virtualinterface_set.all()
    
    output = []
    for interface in if_list:
        output.append([
            str(interface.id),
            str( interface )
        ])
    
    # Output value will be "i-id" for interfaces and "p-id" for ports
    return HttpResponse(json.dumps(output), mimetype='application/json')

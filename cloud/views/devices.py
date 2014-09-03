import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from cloud.models.router import Router
from cloud.models.switch import Switch
from cloud.models.host import Host
from cloud.models.device import Device

# Configure logging for the module name
logger = logging.getLogger(__name__)

# Webservice to get devices of a given type
@login_required
def devices(request, device_type):
    
    if device_type == "routers":
        dev_list = Router.objects.all()
    elif device_type == "switches":
        dev_list = Switch.objects.all()
    elif device_type == "hosts":
        dev_list = Host.objects.all()
    else:
        dev_list = []
    
    output = []
    for dev in dev_list:
        output.append([
            dev.id,
            str( dev )
        ])
    
    return HttpResponse(json.dumps(output), mimetype='application/json')

# Webservice to get interface or port details for a given device
@login_required
def interfaces(request, device_id):
    try:
        dev = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        raise Http404

    if dev.is_switch():
        if_list = dev.switch.port_set.all()
        prefix = "p-"
    else:
        if_list = dev.host.interface_set.all()
        prefix = "i-"
    
    output = []
    for interface in if_list:
        output.append([
            prefix + str(interface.id),
            str( interface )
        ])
    
    # Output value will be "i-id" for interfaces and "p-id" for ports
    return HttpResponse(json.dumps(output), mimetype='application/json')

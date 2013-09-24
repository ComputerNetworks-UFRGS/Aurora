import logging
from django.http import HttpResponse
from django.template import Context, RequestContext, loader
from manager.models.switch import Switch, SWITCH_TYPE
from django.http import Http404
from django import forms
from django.shortcuts import render_to_response, redirect
from django.contrib.auth.decorators import login_required
from manager.helpers import session_flash
from manager.widgets.number_input import NumberInput
from manager.models.port import Port, PORT_DUPLEX_TYPE
from manager.models.device import Device
from django.core.validators import EMPTY_VALUES
from django.core.exceptions import ValidationError
from manager.models.interface import Interface

# Configure logging for the module name
logger = logging.getLogger(__name__)
active_menu = "Resources"

@login_required
def index(request):
    t = loader.get_template('switches-index.html')
    switch_list = Switch.objects.all()
    view_vars = {
        'active_menu': active_menu,
        'title': "Switches List",
        'actions': [{ 'name': "New Switch", 'url': "/Aurora/manager/switches/new/" }]
    }
    c = Context({
        'switch_list': switch_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return HttpResponse(t.render(c))

@login_required
def detail(request, switch_id):
    view_vars = {
        'active_menu': active_menu,
        'title': "Switch Details",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/manager/switches/" },
        ]
    }
    try:
        switch = Switch.objects.get(pk=switch_id)
    except Switch.DoesNotExist:
        raise Http404
    
    port_list = switch.port_set.all()
    # TODO: Collect network usage statistics from network ports
    
    return render_to_response('switches-detail.html', { 
        'switch': switch, 
        'port_list': port_list,
        'view_vars': view_vars, 
        'request': request,
        'flash': session_flash.get_flash(request)
    })

#Form for new Switch creation
class SwitchForm(forms.Form):
    action = "/Aurora/manager/switches/new/"
    name = forms.CharField(max_length=200, help_text="Human readable name")
    description = forms.CharField(widget=forms.Textarea)
    sw_type = forms.ChoiceField(choices=SWITCH_TYPE, label="Type of Switch")
    hostname = forms.CharField(max_length=200, help_text="Valid hostname or IP address")
    
@login_required
def new(request):
    if request.method == 'POST': # If the form has been submitted...
        form = SwitchForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            s = Switch()
            s.name = form.cleaned_data['name']
            s.description = form.cleaned_data['description']
            s.sw_type = form.cleaned_data['sw_type']
            s.hostname = form.cleaned_data['hostname']
            s.save()
            
            session_flash.set_flash(request, "New Switch successfully created")
            return redirect('manager-switches-index') # Redirect after POST
    else:
        form = SwitchForm() # An unbound form
    
    view_vars = {
        'active_menu': active_menu,
        'title': "New Switch",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/manager/switches/" },
        ]
    }
    c = RequestContext(request, {
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request) 
    })
    return render_to_response('base-form.html', c)

@login_required
def delete(request, switch_id):
    try:
        switch = Switch.objects.get(pk=switch_id)
    except Switch.DoesNotExist:
        raise Http404

    switch.delete()
    session_flash.set_flash(request, "Switch %s was successfully deleted!" % str(switch))
    logger.debug("Switch %s was successfully deleted!" % str(switch))
    
    return redirect('manager-switches-index')

#Form for new Network Port creation
class PortForm(forms.Form):
    action = "/Aurora/manager/switches/%s/new_port/"
    alias = forms.CharField(max_length=20)
    uplink_speed = forms.IntegerField(widget=NumberInput(attrs={"max": 10**12, "min": 10**3, "step": 10**3}), max_value=10**12, min_value=10**3, help_text="bps")
    downlink_speed = forms.IntegerField(widget=NumberInput(attrs={"max": 10**12, "min": 10**3, "step": 10**3}), max_value=10**12, min_value=10**3, help_text="bps")
    duplex = forms.ChoiceField(choices=PORT_DUPLEX_TYPE)
    
@login_required
def new_port(request, switch_id):
    try:
        switch = Switch.objects.get(pk=switch_id)
    except Switch.DoesNotExist:
        raise Http404
    
    if request.method == 'POST': # If the form has been submitted...
        form = PortForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            p = Port()
            p.switch = switch
            p.alias = form.cleaned_data['alias']
            p.uplink_speed = form.cleaned_data['uplink_speed']
            p.downlink_speed = form.cleaned_data['downlink_speed']
            p.duplex = form.cleaned_data['duplex']
            p.save()
            
            session_flash.set_flash(request, "New Port successfully created")
            return redirect('/Aurora/manager/switches/' + switch_id + '/') # Redirect after POST
    else:
        form = PortForm() # An unbound form
    
    view_vars = {
        'active_menu': active_menu,
        'title': "New Port for " + switch.name,
        'actions': [
            { 'name': "Back to Details", 'url': "/Aurora/manager/switches/" + switch_id + "/" },
        ]
    }
    # insert slice_id in the action url
    form.action = form.action % switch_id
    c = RequestContext(request, {
        'switch': switch,
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request) 
    })
    return render_to_response('base-form.html', c)

class DeviceModelChoiceField(forms.ModelChoiceField):
    # Override to_python function to avoid "select a valid choice" errors
    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        try:
            dev = Device.objects.get(pk=value)
        except Device.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])
        return dev

class InterfaceModelChoiceField(forms.ModelChoiceField):
    # Override to_python function to avoid "select a valid choice" errors
    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        # Value should have "i-id" or "p-id" format for interfaces and ports, respectively 
        svalue = value.split("-")
        if svalue[0] == "i":
            try:
                interface = Interface.objects.get(pk=svalue[1])
            except Interface.DoesNotExist:
                raise ValidationError(self.error_messages['invalid_choice'])
            return interface
        elif svalue[0] == "p":
            try:
                port = Port.objects.get(pk=svalue[1])
            except Port.DoesNotExist:
                raise ValidationError(self.error_messages['invalid_choice'])
            return port
        else:
            return None

#Form for connecting devices to ports
class ConnectDeviceForm(forms.Form):
    action = "/Aurora/manager/switches/%s/connect_device/%s/"
    device_type = forms.ChoiceField(
        choices=(("routers", "Router"), ("switches", "Switch"), ("hosts", "Host")),
        widget=forms.RadioSelect(attrs={'onChange':'select_load_options(this, "/Aurora/manager/devices/__selected_id__/", "id_device")'})
    )
    device = DeviceModelChoiceField(
        queryset=Device.objects.none(),
        widget=forms.Select(attrs={'onChange':'select_load_options(this, "/Aurora/manager/devices/__selected_id__/interfaces/", "id_interface")'})
    )
    interface = InterfaceModelChoiceField(queryset=Interface.objects.none(), label="Interface/Port")
    
def connect_device(request, switch_id, port_id):
    try:
        sw = Switch.objects.get(pk=switch_id)
        port = Port.objects.get(pk=port_id, switch=sw)
    except Switch.DoesNotExist:
        raise Http404
    
    if request.method == 'POST': # If the form has been submitted...
        form = ConnectDeviceForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            interface = form.cleaned_data['interface']
            if type(interface) == Port:
                port.connected_ports.add(interface)
            else:
                port.connected_interfaces.add(interface)
            
            session_flash.set_flash(request, "Device successfully connected to port %s" % str(port))
            return redirect('/Aurora/manager/switches/' + switch_id + '/') # Redirect after POST
    else:
        form = ConnectDeviceForm() # An unbound form
    
    view_vars = {
        'active_menu': active_menu,
        'title': "Connect Device on port " + port.alias + " of " + sw.name,
        'actions': [
            { 'name': "Back to Details", 'url': "/Aurora/manager/switches/" + switch_id + "/" },
        ]
    }
    # insert slice_id in the action url
    form.action = form.action % (switch_id, port_id)
    c = RequestContext(request, {
        'switch': sw,
        'port': port,
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request) 
    })
    return render_to_response('base-form.html', c)

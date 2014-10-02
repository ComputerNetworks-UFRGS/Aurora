import json
import logging
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import Context, RequestContext, loader
from libvirt import libvirtError
from cloud.helpers import session_flash, paginate
from cloud.models.host import Host, DRIVERS, TRANSPORTS
from cloud.models.interface import Interface, INTERFACE_TYPES, INTERFACE_DUPLEX_TYPE
from cloud.models.virtual_machine import VirtualMachine
from cloud.widgets.number_input import NumberInput

# Configure logging for the module name
logger = logging.getLogger(__name__)
view_vars = {
    'active_menu': 'Resources',
    'active_section': 'Hosts',
}

@login_required
def index(request):
    global view_vars
    t = loader.get_template('hosts-index.html')
    hosts = Host.objects.all()
    host_list = paginate.paginate(hosts, request)

    view_vars.update({
        'active_item': None,
        'title': "Hosts List",
        'actions': [{ 
            'name': "New Host", 
            'url': "/Aurora/cloud/hosts/new/",
            'image': 'plus'
        }]
    })
    c = Context({
        'host_list': host_list,
        'paginate_list': host_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return HttpResponse(t.render(c))

@login_required
def detail(request, host_id):
    global view_vars
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        raise Http404

    view_vars.update({
        'active_item': host,
        'title': "Host Details",
        'actions': [{ 
            'name': 'Back to List', 
            'url': '/Aurora/cloud/hosts/',
            'image': 'chevron-left'
            }, { 
            'name': 'XML', 
            'url': '/Aurora/cloud/hosts/' + host_id + '/xml/' 
            },
        ]
    })
    
    sys_info = host.get_info()
    memory_list = host.get_memory_info()
    memory_stats = host.get_memory_stats()
    cpu_list = host.get_cpu_info()
    cpu_stats = host.get_cpu_stats()
    vms_state = host.get_state_of_vms()
    vms_total = host.get_num_of_vms()
    if_list = host.interface_set.all()
    # TODO: Collect network usage statistics from network interfaces
    
    return render_to_response('hosts-detail.html', { 
        'host': host, 
        'sys_info': sys_info,
        'memory_list': memory_list,
        'memory_stats': memory_stats,
        'if_list': if_list,
        'cpu_list': cpu_list,
        'cpu_stats': cpu_stats,
        'vms_state': vms_state,
        'vms_total': vms_total,
        'view_vars': view_vars, 
        'request': request,
        'flash': session_flash.get_flash(request)
    })

@login_required
def xml(request, host_id):
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        raise Http404
    
    response = HttpResponse(mimetype='text/xml')
    response['Content-Disposition'] = 'attachment; filename=Host_XML_' + host_id + '.xml'
    response.write(host.get_xml_info())
    
    return response

#Form for new Host creation
class HostForm(forms.Form):
    action = "/Aurora/cloud/hosts/new/"
    name = forms.CharField(max_length=200, help_text="Human readable name")
    description = forms.CharField(widget=forms.Textarea)
    driver = forms.ChoiceField(choices=DRIVERS)
    transport = forms.ChoiceField(choices=TRANSPORTS)
    username = forms.CharField(max_length=100, required=False)
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    hostname = forms.CharField(max_length=200, required=False, help_text="Valid hostname or IP address")
    port = forms.IntegerField(widget=NumberInput(attrs={"max": 65536, "min": 1}), max_value=65536, min_value=1, help_text="(defaults - tls:16514, tcp:16509, ssh:22, local:empty)", required=False)
    path = forms.CharField(max_length=200, required=False)
    extraparameters = forms.CharField(max_length=200, required=False, label="Extra Parameters")
    
@login_required
def new(request):
    global view_vars
    if request.method == 'POST': # If the form has been submitted...
        form = HostForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            h = Host()
            h.name = form.cleaned_data['name']
            h.description = form.cleaned_data['description']
            h.driver = form.cleaned_data['driver']
            h.transport = form.cleaned_data['transport']
            h.username = form.cleaned_data['username']
            h.password = form.cleaned_data['password']
            h.hostname = form.cleaned_data['hostname']
            h.port = form.cleaned_data['port']
            h.path = form.cleaned_data['path']
            h.extraparameters = form.cleaned_data['extraparameters']
            
            # Save Host to get an ID
            h.save()
            
            # Checks to see if Open vSwitch is properly configured (if it is 
            # not, it will try to configure)
            ovs_status = h.check_openvswitch_status()
            if ovs_status != "OK":
                session_flash.set_flash(request, "Could not configure Open vSwitch for this host: " + ovs_status, 'danger')

            session_flash.set_flash(request, "New Host successfully created")
            return redirect('cloud-hosts-index') # Redirect after POST
    else:
        form = HostForm() # An unbound form
    
    view_vars.update({
        'active_item': None,
        'title': 'New Host',
        'actions': [{ 
            'name': 'Back to List', 
            'url': '/Aurora/cloud/hosts/',
            'image': 'chevron-left'
        }]
    })
    c = RequestContext(request, {
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request) 
    })
    return render_to_response('base-form.html', c)

@login_required
def delete(request, host_id):
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        raise Http404

    host.delete()
    session_flash.set_flash(request, "Host %s was successfully deleted!" % str(host))
    logger.debug("Host %s was successfully deleted!" % str(host))
    
    return redirect('cloud-hosts-index')

#Form for new Network Interface creation
class InterfaceForm(forms.Form):
    action = "/Aurora/cloud/hosts/%s/new_interface/"
    alias = forms.CharField(max_length=20)
    if_type = forms.ChoiceField(choices=INTERFACE_TYPES)
    uplink_speed = forms.IntegerField(widget=NumberInput(attrs={"max": 10**12, "min": 10**3, "step": 10**3}), max_value=10**12, min_value=10**3, help_text="bps")
    downlink_speed = forms.IntegerField(widget=NumberInput(attrs={"max": 10**12, "min": 10**3, "step": 10**3}), max_value=10**12, min_value=10**3, help_text="bps")
    duplex = forms.ChoiceField(choices=INTERFACE_DUPLEX_TYPE)
    
@login_required
def new_interface(request, host_id):
    global view_vars
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        raise Http404
    
    if request.method == 'POST': # If the form has been submitted...
        form = InterfaceForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            i = Interface()
            i.attached_to = host
            i.alias = form.cleaned_data['alias']
            i.if_type = form.cleaned_data['if_type']
            i.uplink_speed = form.cleaned_data['uplink_speed']
            i.downlink_speed = form.cleaned_data['downlink_speed']
            i.duplex = form.cleaned_data['duplex']
            i.save()
            
            session_flash.set_flash(request, "New Interface successfully created")
            return redirect('/Aurora/cloud/hosts/' + host_id + '/') # Redirect after POST
    else:
        form = InterfaceForm() # An unbound form
    
    view_vars.update({
        'active_item': host,
        'title': 'New Interface for ' + host.name,
        'actions': [{
            'name': 'Back to Details', 
            'url': '/Aurora/cloud/hosts/' + host_id + '/',
            'image': 'chevron-left'
        }]
    })
    # insert slice_id in the action url
    form.action = form.action % host_id
    c = RequestContext(request, {
        'host': host,
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request) 
    })
    return render_to_response('base-form.html', c)

@login_required
def list_infrastructure(request):
    ''' Temporary just to keep the infrastructure consistent '''
    hosts = Host.objects.all()

    all_domains = {}

    for h in hosts:
        lv_conn = h.libvirt_connect()
        all_domains[h.name] = []
        try:
            def_domains = lv_conn.listDefinedDomains()
            active_domains = lv_conn.listDomainsID()
        except libvirtError as e:
            logger.error('Failed to read domains from hypervisor: ' + lv_conn + ' ' + str(e))
            session_flash.set_flash(request, 'Failed to read domains from hypervisor: ' + lv_conn + ' ' + str(e), 'danger')
        for dom_id in active_domains:
            # Get domain info from libvirt
            try:
                dom = lv_conn.lookupByID(dom_id)
                dom_name = dom.name()
                vms = VirtualMachine.objects.filter(name=dom_name)
                if len(vms) > 0 and vms[0].host == h:
                    dom_name += " (OK)"
                elif len(vms) == 0:
                    dom_name += " (not found in DB)"
                else:
                    vms[0].host = h
                    vms[0].save()
                    dom_name += " (Fixed DB)"
                all_domains[h.name].append(dom_name)

            except libvirtError as e:
                logger.error('Failed to read domain info from hypervisor: ' + lv_conn + ' ' + str(e))
                session_flash.set_flash(request, 'Failed to read domains from hypervisor: ' + lv_conn + ' ' + str(e), 'danger')

        for dom_name in def_domains:
            # Get domain info from libvirt
            try:
                dom = lv_conn.lookupByName(dom_name)
                vms = VirtualMachine.objects.filter(name=dom_name)
                if len(vms) > 0 and vms[0].host == h:
                    dom_name += " (OK)"
                elif len(vms) == 0:
                    dom_name += " (not found in DB)"
                else:
                    vms[0].host = h
                    vms[0].save()
                    dom_name += " (Fixed DB)"
                all_domains[h.name].append(dom_name)

            except libvirtError as e:
                logger.error('Failed to read domain info from hypervisor: ' + lv_conn + ' ' + str(e))
                session_flash.set_flash(request, 'Failed to read domains from hypervisor: ' + lv_conn + ' ' + str(e), 'danger')

    return HttpResponse("<pre>" + json.dumps(all_domains, sort_keys=True, indent=2, separators=(',', ': ')) + "</pre>")


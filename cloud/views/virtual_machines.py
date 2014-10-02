import json
import logging
import commands
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, RequestContext
from django.template.loader import get_template
from cloud.helpers import session_flash, paginate
from cloud.models.virtual_machine import VirtualMachine
from cloud.models.host import Host
from cloud.models.image import Image
from cloud.models.slice import Slice
from cloud.models.virtual_interface import (
    VIRTUAL_INTERFACE_TYPES, VirtualInterface
)
from cloud.widgets.number_input import NumberInput

# Configure logging for the module name
logger = logging.getLogger(__name__)
view_vars = {
    'active_menu': 'Computing',
    'active_section': 'Virtual Machines',
}


#Form index filters
class VirtualMachinesIndexFiltersForm(forms.Form):
    slices = Slice.objects.all()
    slice_choices = (
        ("", "---------------"),
        (-1, "--Unbound Virtual Machines--")
    )
    for slc in slices:
        slice_choices += ((slc.id, slc.name),)

    s = forms.ChoiceField(choices=slice_choices, label="Slice", required=False)
    p = forms.CharField(widget=forms.HiddenInput(), required=False)


@login_required
def index(request):
    global view_vars
    form = VirtualMachinesIndexFiltersForm(request.GET)  # Filter form
    if form.is_valid():
        s = form.cleaned_data['s']
        if s != '':
            # Search for unbound Virtual Machines
            if s == '-1':
                s = None
            vms = VirtualMachine.objects.filter(belongs_to_slice=s)
        else:
            vms = VirtualMachine.objects.all()
    else:
        vms = []

    vm_list = paginate.paginate(vms, request)

    t = get_template('virtual-machines-index.html')
    view_vars.update({
        'active_item': None,
        'title': 'Virtual Machines List',
        'actions': [{
            'name': 'New Virtual Machine',
            'url': '/Aurora/cloud/virtual_machines/new/',
            'image': 'plus'
        }, {
            'name': 'Synchronize',
            'url': '/Aurora/cloud/virtual_machines/sync/',
            'image': 'retweet'
        }]
    })

    c = Context({
        'form': form,
        'view_vars': view_vars,
        'vm_list': vm_list,
        'paginate_list': vm_list,
        'request': request,
        'flash': session_flash.get_flash(request)
    })

    return HttpResponse(t.render(c))


@login_required
def detail(request, virtual_machine_id):
    global view_vars
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    view_vars.update({
        'active_item': vm,
        'title': 'Virtual Machine Details',
        'actions': [{
            'name': 'Back to List',
            'url': '/Aurora/cloud/virtual_machines/',
            'image': 'chevron-left'
        }, {
            'name': 'XML',
            'url': '/Aurora/cloud/virtual_machines/' +
            virtual_machine_id + '/xml/'
        }]
    })

    if vm.current_state() == 'running':
        view_vars['actions'].append({
            'name': "Console",
            'url': "/Aurora/cloud/virtual_machines/" +
                virtual_machine_id + "/console/",
            'extras': "popup",
        })

    if_list = vm.get_interface_info()
    hd_list = vm.get_disk_info()

    return render_to_response('virtual-machines-detail.html', {
        'vm': vm,
        'if_list': if_list,
        'hd_list': hd_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })


@login_required
def start(request, virtual_machine_id):
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    try:
        vm.start()
        session_flash.set_flash(request,
            "Virtual Machine %s was successfully started!" % vm.name
        )
        logger.debug("Virtual Machine %s was successfully started!" % vm.name)
    except:
        session_flash.set_flash(request,
            "Could not start Virtual Machine %s!" % vm.name, "danger"
        )
        logger.warning("Could not start Virtual Machine %s!" % vm.name)

    return redirect(request.META['HTTP_REFERER'])


@login_required
def stop(request, virtual_machine_id):
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    try:
        vm.stop()
        session_flash.set_flash(request,
            "Virtual Machine %s was successfully stopped!" % vm.name
        )
        logger.debug("Virtual Machine %s was successfully stopped!" % vm.name)
    except vm.VirtualMachineException as e:
        session_flash.set_flash(request,
            "Could not stop Virtual Machine %s: %s" % (vm.name, str(e)),
            "danger"
        )
        logger.warning(
            "Could not stop Virtual Machine %s: %s" % (vm.name, str(e))
        )

    return redirect(request.META['HTTP_REFERER'])


@login_required
def console(request, virtual_machine_id):
    global view_vars
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    view_vars.update({
        'title': "Virtual Machine Console",
        'actions': [{
            'name': "New Virtual Machine",
            'url': "/Aurora/cloud/virtual_machines/new/"
        }, {
            'name': "Synchronize",
            'url': "/Aurora/cloud/virtual_machines/sync/"
        }]
    })

    try:
        # Get VNC info for this VM (hostname and port)
        vnc_info = vm.get_vnc_info()

        # Get the VNC port info on the destination host
        vnc_port = vnc_info['port']

        # Generate a unique port for the WebSocket server in the 40k range
        vnc_info['port'] = "4" + str(vm.id).zfill(4)

        out = commands.getstatusoutput(
            'websockify --daemon --idle-timeout 60 ' +
            vnc_info['port'] + ' ' +
            vnc_info['host'] + ':' +
            vnc_port
        )

        if out[0] != 0:
            logger.debug(out)
            logger.warning("Could not start Websocket %s" % out[1])

        logger.debug("Loading console for %s" % vm.name)
    except vm.VirtualMachineException as e:
        session_flash.set_flash(request, "Could load console information for %s: %s" % (vm.name, str(e)), "danger")

    return render_to_response('virtual-machines-console.html', {'vm': vm, 'vnc_info': vnc_info, 'view_vars': view_vars, 'request': request, 'flash': session_flash.get_flash(request) })

@login_required
def shutdown(request, virtual_machine_id):
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    try:
        vm.shutdown()
        session_flash.set_flash(request, "Virtual Machine %s is about to shutdown... (wait a bit)!" % vm.name)
        logger.debug("Virtual Machine %s is about to shutdown..." % vm.name)
    except vm.VirtualMachineException as e:
        session_flash.set_flash(request, "Could not shutdown Virtual Machine %s: %s" % (vm.name, str(e)), "danger")
        logger.warning("Could not shutdown Virtual Machine %s: %s" % (vm.name, str(e)))

    return redirect(request.META['HTTP_REFERER'])

@login_required
def resume(request, virtual_machine_id):
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    try:
        vm.resume()
        session_flash.set_flash(request, "Virtual Machine %s was successfully resumed!" % vm.name)
        logger.debug("Virtual Machine %s was successfully resumed!" % vm.name)
    except vm.VirtualMachineException as e:
        session_flash.set_flash(request, "Could not resume Virtual Machine %s: %s" % (vm.name, str(e)), "danger")
        logger.warning("Could not resume Virtual Machine %s: %s" % (vm.name, str(e)))

    return redirect(request.META['HTTP_REFERER'])

@login_required
def suspend(request, virtual_machine_id):
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    try:
        vm.suspend()
        session_flash.set_flash(request, "Virtual Machine %s was successfully suspended!" % vm.name)
        logger.debug("Virtual Machine %s was successfully suspended!" % vm.name)
    except vm.VirtualMachineException as e:
        session_flash.set_flash(request, "Could not suspend Virtual Machine %s: %s" % (vm.name, str(e)), "danger")
        logger.warning("Could not suspend Virtual Machine %s: %s" % (vm.name, str(e)))

    return redirect(request.META['HTTP_REFERER'])

# Synchronizes virtual machines with their libvirt status
@login_required
def sync(request):
    try:
        hosts = Host.objects.all()
    except:
        session_flash.set_flash(request, "Problems loading hosts", "danger")
        raise redirect('cloud-virtual-machines-index')

    for h in hosts:
        # Sync physical host current status with the database
        try:
            h.sync()
        except h.HostException as e:
            session_flash.set_flash(request, 'Problems synchronizing host "' + str(h) + '": ' + str(e), "danger")
            return redirect('cloud-virtual-machines-index')

    session_flash.set_flash(request, "Synchronization finished")

    return redirect('cloud-virtual-machines-index')

@login_required
def xml(request, virtual_machine_id):

    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    xml_desc = vm.get_xml_desc()
    if xml_desc == False:
        session_flash.set_flash(request, "Could not read XML description for Virtual Machine %s" % vm.name, "danger")
        return redirect(request.META['HTTP_REFERER'])
    else:
        response = HttpResponse(mimetype='text/xml')
        response['Content-Disposition'] = 'attachment; filename=VM_XML_' + virtual_machine_id + '.xml'
        response.write(xml_desc)

    return response

#Form for new Virtual Machine creation
class VirtualMachineForm(forms.Form):
    action = "/Aurora/cloud/virtual_machines/new/"
    name = forms.CharField(max_length=200)
    memory = forms.IntegerField(widget=NumberInput(attrs={"max": 8192, "min": 64, "step": 64}), max_value=8192, min_value=64, help_text="Size in MB")
    vcpu = forms.IntegerField(widget=NumberInput(attrs={"max": 4, "min": 1, "step": 1}), max_value=4, min_value=1)
    image = forms.ModelChoiceField(queryset=Image.objects.all(), empty_label=None)
    network = forms.ChoiceField(choices=((u'', '---------'),) + VIRTUAL_INTERFACE_TYPES, required=False)
    belongs_to_slice = forms.ModelChoiceField(queryset=Slice.objects.all(), required=False)

@login_required
def new(request):
    global view_vars
    if request.method == 'POST': # If the form has been submitted...
        form = VirtualMachineForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data

            vm = VirtualMachine()
            vm.name = form.cleaned_data['name']
            vm.memory = form.cleaned_data['memory']*1024
            vm.vcpu = form.cleaned_data['vcpu']
            vm.image = form.cleaned_data['image']
            vm.belongs_to_slice = form.cleaned_data['belongs_to_slice']

            # Choose a host (randomly)
            vm.host = Host.objects.order_by('?')[0]

            # Save Virtual Machine to get an ID
            vm.save()

            if form.cleaned_data['network'] != '':
                # Create network interface
                interface = VirtualInterface()
                interface.alias = "net0"
                interface.attached_to = vm
                interface.if_type = form.cleaned_data['network']
                interface.save()

            try:
                # Creates disk and defines Virtual Machine in libvirt
                vm.deploy()
                session_flash.set_flash(request, "New Virtual Machine successfully created")
            except vm.VirtualMachineException as e:
                session_flash.set_flash(request, "Problems deploying Virtual Machine: %s" % str(e), "danger")

            return redirect('cloud-virtual-machines-index') # Redirect after POST
    else:
        form = VirtualMachineForm() # An unbound form

    view_vars.update({
        'active_item': None,
        'title': "New Virtual Machine",
        'actions': [{ 
            'name': 'Back to List', 
            'url': 'javascript: history.back()',
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

#Form for Virtual Machine migration
class VirtualMachineMigrationForm(forms.Form):
    action = "/Aurora/cloud/virtual_machines/%s/migrate/"
    host = forms.ModelChoiceField(queryset=Host.objects.all(), empty_label=None)

@login_required
def migrate(request, virtual_machine_id):
    global view_vars
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    if request.method == 'POST': # If the form has been submitted...
        form = VirtualMachineMigrationForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data

            # Migrate Virtual Machine to new host
            try:
                # TODO: investigate other options in the migration operation in libvirt
                vm.migrate(form.cleaned_data['host'])

                # Save Virtual Machine with new host
                vm.host = form.cleaned_data['host']
                vm.save()

                session_flash.set_flash(request, "Virtual Machine successfully migrated")
            except vm.VirtualMachineException as e:
                session_flash.set_flash(request, "Could not migrate Virtual Machine %s: %s" % (vm.name, str(e)), "danger")
                logger.warning("Could not migrate Virtual Machine %s: %s" % (vm.name, str(e)))

            return redirect('cloud-virtual-machines-index') # Redirect after POST
    else:
        form = VirtualMachineMigrationForm() # An unbound form

    # insert slice_id in the action url
    form.action = form.action % virtual_machine_id

    view_vars.update({
        'active_item': vm,
        'title': "Migrate Virtual Machine",
        'actions': [{ 
            'name': 'Back to List', 
            'url': 'javascript: history.back()',
            'image': 'chevron-left'
        }]
    })
    c = RequestContext(request, {
        'vm': vm,
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return render_to_response('base-form.html', c)

@login_required
def delete(request, virtual_machine_id):
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    try:
        vm.undeploy()
    except vm.VirtualMachineException as e:
        session_flash.set_flash(request, "Could not undefine Virtual Machine on hypervisor %s: %s" % (vm.name, str(e)), "warning")
        logger.warning("Could not undefine Virtual Machine on hypervisor %s: %s" % (vm.name, str(e)))

    # Delete VM from database anyway
    vm.delete()
    session_flash.set_flash(request, "Virtual Machine %s was successfully deleted!" % vm.name)
    logger.debug("Virtual Machine %s was successfully deleted!" % vm.name)

    return redirect(request.META['HTTP_REFERER'])

# Webservice to get interface details for a Virtual Machine
@login_required
def interfaces(request, virtual_machine_id):
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    if_list = vm.get_interface_info()

    output = []
    for interface in if_list:
        output.append([
            interface.id,
            "Interface " + str( interface.alias ) + " - " + interface.mac_address
        ])

    # Output format is [ [mac1, label1], [mac2, label2], ... [macN, labelN]]
    return HttpResponse(json.dumps(output), mimetype='application/json')

#Form for new Virtual Interface creation
class VirtualInterfaceForm(forms.Form):
    action = "/Aurora/cloud/virtual_machines/%s/new_virtual_interface/"
    alias = forms.CharField(max_length=20)
    if_type = forms.ChoiceField(choices=VIRTUAL_INTERFACE_TYPES)

@login_required
def new_virtual_interface(request, virtual_machine_id):
    global view_vars
    try:
        vm = VirtualMachine.objects.get(pk=virtual_machine_id)
    except VirtualMachine.DoesNotExist:
        raise Http404

    if request.method == 'POST': # If the form has been submitted...
        form = VirtualInterfaceForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data

            interface = VirtualInterface()
            interface.alias = form.cleaned_data['alias']
            interface.if_type = form.cleaned_data['if_type']
            interface.mac_address = None
            interface.attached_to = vm
            interface.save()

            try:
                vm.install_interface(interface)
                session_flash.set_flash(request, "New Virtual Interface successfully added")
            except vm.VirtualMachineException as e:
                session_flash.set_flash(request, "Could not install Virtual Interface on VM %s: %s" % (vm.name, str(e)), "warning")
                logger.warning("Could not install Virtual Interface on VM %s: %s" % (vm.name, str(e)))

            return redirect('/Aurora/cloud/virtual_machines/' + virtual_machine_id + '/') # Redirect after POST
    else:
        form = VirtualInterfaceForm() # An unbound form

    view_vars.update({
        'active_item': vm,
        'title': 'New Virtual Interface for ' + vm.name,
        'actions': [{ 
            'name': 'Back to Details', 
            'url': '/Aurora/cloud/virtual_machines/' + virtual_machine_id + '/',
            'image': 'chevron-left'
        }]
    })
    # insert slice_id in the action url
    form.action = form.action % virtual_machine_id
    c = RequestContext(request, {
        'vm': vm,
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return render_to_response('base-form.html', c)



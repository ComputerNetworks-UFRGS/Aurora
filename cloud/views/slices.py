import base64
import time
import httplib
import logging
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring, tostring
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, RequestContext
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from cloud.helpers import session_flash 
from cloud.models.slice import Slice
from cloud.models.monitoring import Monitoring
from cloud.models.virtual_machine import VirtualMachine
from cloud.models.virtual_link import VirtualLink
from cloud.models.virtual_router import VirtualRouter
from cloud.models.deployment_program import DeploymentProgram
from cloud.models.optimization_program import OptimizationProgram
from cloud.models.optimizes_slice import OptimizesSlice
from cloud.widgets.number_input import NumberInput

# Configure logging for the module name
logger = logging.getLogger(__name__)
view_vars = {
    'active_menu': 'Slice Management',
    'active_section': 'Slices',
    'active_item': None,
}

@login_required
def index(request):
    global view_vars
    t = get_template('slices-index.html')
    slice_list = Slice.objects.all()
    view_vars.update({
        'active_item': None,
        'title': "Slices List",
        'actions': [{ 
            'name': "New Slice", 
            'url': "/Aurora/cloud/slices/new/",
            'image': 'plus'
        }]
    })
    
    c = Context({
        'view_vars': view_vars,
        'slice_list': slice_list,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    
    return HttpResponse(t.render(c))

@login_required
def detail(request, slice_id):
    global view_vars
    try:
        slc = Slice.objects.get(pk=slice_id)
    except Slice.DoesNotExist:
        raise Http404
    view_vars.update({
        'active_item': slc,
        'title': 'Slice Details',
        'actions': [{ 
            'name': 'Back to List', 
            'url': '/Aurora/cloud/slices/',
            'image': 'chevron-left'
        }]
    })

    if slc.state == 'created':
        view_vars['actions'].append({ 
            'name': "Deploy", 
            'url': "/Aurora/cloud/slices/" + str(slc.id) + "/deploy/"
        })

    vm_list = VirtualMachine.objects.filter(belongs_to_slice=slc)
    vr_list = VirtualRouter.objects.filter(belongs_to_slice=slc)
    link_list = slc.virtuallink_set.all()
    optimized_by_list = slc.optimizesslice_set.order_by('priority')
    
    return render_to_response('slices-detail.html', {
        'slc': slc, 
        'vm_list': vm_list, 
        'vr_list': vr_list, 
        'link_list': link_list, 
        'optimized_by_list': optimized_by_list,
        'view_vars': view_vars, 
        'request': request, 
        'flash': session_flash.get_flash(request)
    })

#Form for new Slice creation
class SliceForm(forms.Form):
    action = "/Aurora/cloud/slices/new/"
    name = forms.CharField(max_length=200)
    owner = forms.ModelChoiceField(queryset=User.objects.all())
    vxdl_file = forms.FileField()
    
@login_required
def new(request):
    global view_vars
    if request.method == 'POST': # If the form has been submitted...
        form = SliceForm(request.POST, request.FILES) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            s = Slice()
            s.owner = form.cleaned_data['owner']
            s.name = form.cleaned_data['name']

            # Get VXDL description for slice
            vxdl = request.FILES['vxdl_file'].read()
            
            # Save slice using uploaded VXDL description
            try:
                s.save_from_vxdl(vxdl)
                session_flash.set_flash(request, "New Slice successfully created")
            except Slice.VXDLException as e:
                session_flash.set_flash(request, "Problems creating slice from VXDL: " + e.msg, "danger")
            
            # TODO: Deploy slice using program here
            
            return redirect('cloud-slices-index') # Redirect after POST

    else:
        form = SliceForm() # An unbound form
    
    view_vars.update({
        'active_item': None,
        'title': 'New Slice',
        'actions': [{
            'name': 'Back to List',
            'url': '/Aurora/cloud/slices/',
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

# Remote call to add a slice
# TODO: Authenticate the remote system
@csrf_exempt
def new_remote(request):
    if request.method == 'POST': # If the form has been submitted...
            
        s = Slice()
        s.owner = User.objects.all()[0]
        s.name = request.POST['name']

        try:
            deployed_with = DeploymentProgram.objects.get(name="DeployProvinet")
        except DeploymentProgram.DoesNotExist as e:
            message = "ERROR: " + str(e)
            return HttpResponse(message)

        # Get VXDL description for slice
        vxdl = request.POST['vxdl_file']
    
        # Save slice using uploaded VXDL description
        try:
            # Deploy slice with specific program
            from cloud.programs.DeployProvinet import DeployProvinet
            program = DeployProvinet()
            s.save_from_vxdl(vxdl)
            if program.deploy(s):
                s.state = "deployed"
                s.deployed_with = deployed_with
                s.save()
                message = "OK" 
                logger.info("Slice deployed remotely %s!" % (str(s)))
        except Exception as e:
            message = "ERROR: " + str(e)
            logger.warning("Error deploying remotely %s: %s!" % (str(s), str(e)))
        except Slice.VXDLException as e:
            message = "ERROR: Problems creating slice from VXDL: " + str(e)
            logger.warning("Error deploying remotely %s: Problems creating slice from VXDL %s!" % (str(s), str(e)))
        except program.DeploymentException as e:
            message = "ERROR: Problems deploying slice: " + str(e)
            logger.warning("Error deploying remotely %s: Problems deploying slice %s!" % (str(s), str(e)))

    else:
        message = "ERROR: Only POST method is allowed"
        logger.warning("Error deploying remotely %s: Only POST method is allowed!" % (str(s)))
    
    return HttpResponse(message)

# Remote call to remove a slice
# TODO: Authenticate the remote system
@csrf_exempt
def delete_remote(request, slice_name):
    try:
        slc = Slice.objects.get(name=slice_name)
    except Slice.DoesNotExist:
        logger.info("Attempt to delete slice %s!" % (slice_name))
        raise Http404
    
    message = None
    #TODO: Slice deployment is undone hardcoded here. Possibly in the future there should be undeploy programs.
    # List of Links to delete 
    links = slc.virtuallink_set.all()
    for link in links:
        try:
            link.unestablish()
        except link.VirtualLinkException as e:
            message = "Problems unestablishing a virtual link: " + str(e)

    # List of VMs to delete 
    vms = VirtualMachine.objects.filter(belongs_to_slice=slc)
    for vm in vms:
        try:
            vm.undeploy()
            logger.info("VM %s was undeployed!" % str( vm ))
        except vm.VirtualMachineException as e:
            message = "Problems undeploying a virtual machine: " + str(e)

    # Virtual Routers to undeploy
    vrs = VirtualRouter.objects.filter(belongs_to_slice=slc)
    for vr in vrs:
        try:
            vr.undeploy()
        except vm.VirtualRouterException as e:
            message = "Problems undeploying a virtual router: " + str(e)

    slc.delete()
    if message is None:
        message = "OK"
    logger.info("Slice %s was successfully deleted!" % str( slc ))
    
    return HttpResponse(message)


#Form for new Slice creation
class SliceDeploymentForm(forms.Form):
    action = "/Aurora/cloud/slices/%s/deploy/"
    program = forms.ModelChoiceField(
        queryset=DeploymentProgram.objects.all(), 
        empty_label=None
    )

@login_required
def deploy(request, slice_id):
    global view_vars
    try:
        s = Slice.objects.get(pk=slice_id)
    except Slice.DoesNotExist:
        raise Http404

    if request.method == 'POST': # If the form has been submitted...
        form = SliceDeploymentForm(request.POST, request.FILES) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            # Load program and run
            program = form.cleaned_data['program']
            # File name without the '.py' and with '/' replaced by '.'
            file_path = program.file.name[0:-3].replace("/", ".")
            # Generata a list to extract the classname
            program_classname = file_path.split(".")[-1]
            program_path = 'cloud.' + file_path
            try:
                program_module = __import__(program_path, fromlist=[program_classname])
                program_class = getattr(program_module, program_classname)
            except (ImportError, NotImplementedError) as e:
                session_flash.set_flash(request, "Problems loading program: " + str(e), "danger")

            try:
                algo = program_class()
                # Will record deployment time
                t0 = time.time()
                if algo.deploy(s):
                    deployment_time = time.time() - t0
                    s.state = "deployed"
                    s.deployed_with = program
                    s.save()
                    session_flash.set_flash(request, "Slice successfully deployed in " + str(round(deployment_time, 2)) + " seconds")
            except algo.DeploymentException as e:
                session_flash.set_flash(request, "Problems deploying slice: " + str(e), "danger")
            
            # Send new slice information to monitoring system
            #Monitoring.load().deploy_infrastructure(s)

            return redirect('cloud-slices-index') # Redirect after POST

    else:
        form = SliceDeploymentForm() # An unbound form
    
    view_vars.update({
        'active_item': s,
        'title': 'Deploy Slice',
        'actions': [{
            'name': 'Back to List',
            'url': '/Aurora/cloud/slices/',
            'image': 'chevron-left'
        }]
    })
    # insert slice_id in the action url
    form.action = form.action % slice_id
    c = RequestContext(request, {
        's': s,
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request) 
    })
    return render_to_response('base-form.html', c)

@login_required
def delete(request, slice_id):
    try:
        slc = Slice.objects.get(pk=slice_id)
    except Slice.DoesNotExist:
        raise Http404
    
    #TODO: Slice deployment is undone hardcoded here. Possibly in the future there should be undeploy programs.
    # List of Links to delete 
    links = VirtualLink.objects.filter(belongs_to_slice=slc)
    for link in links:
        try:
            link.unestablish()
        except link.VirtualLinkException as e:
            session_flash.set_flash(request, "Problems unestablishing a virtual link: " + str(e), "warning")

    # List of VMs to delete 
    vms = VirtualMachine.objects.filter(belongs_to_slice=slc)
    for vm in vms:
        try:
            vm.undeploy()
            logger.debug("Virtual Machine %s was undeployed!" % str( vm ))
        except vm.VirtualMachineException as e:
            session_flash.set_flash(request, "Problems undeploying a virtual machine: " + str(e), "warning")

    # Virtual Routers to undeploy
    vrs = VirtualRouter.objects.filter(belongs_to_slice=slc)
    for vr in vrs:
        try:
            vr.undeploy()
            logger.debug("Virtual Router %s was undeployed!" % str( vm ))
        except vm.VirtualRouterException as e:
            session_flash.set_flash(request, "Problems undeploying a virtual router: " + str(e), "warning")

    slc.delete()
    session_flash.set_flash(request, "Slice %s was successfully deleted!" % str( slc ))
    logger.info("Slice %s was successfully deleted!" % str( slc ))
    
    return redirect('cloud-slices-index')

#Form for adding Optimization Program
class OptimizationProgramForm(forms.Form):
    action = "/Aurora/cloud/slices/%s/add_optimization_program/"
    program = forms.ModelChoiceField(
        queryset=OptimizationProgram.objects.all(), 
        empty_label=None
    )
    priority = forms.IntegerField(widget=NumberInput(attrs={"max": 99, "min": 0, "step": 1}), max_value=99, min_value=0)

@login_required
def add_optimization_program(request, slice_id):
    try:
        slc = Slice.objects.get(pk=slice_id)
    except Slice.DoesNotExist:
        raise Http404
    
    if request.method == 'POST': # If the form has been submitted...
        form = OptimizationProgramForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            opt = OptimizesSlice.objects.create(
                slice=slc, 
                program=form.cleaned_data['program'],
                priority=form.cleaned_data['priority']
            )
            opt.save()
            session_flash.set_flash(request, "Optimization Program successfully added")
            
            return redirect('/Aurora/cloud/slices/' + slice_id + '/') # Redirect after POST
    else:
        form = OptimizationProgramForm() # An unbound form
    
    view_vars.update({
        'active_item': slc,
        'title': 'Add Optimization Program for ' + slc.name,
        'actions': [{
            'name': 'Back to Details',
            'url': '/Aurora/cloud/slices/' + slice_id + '/',
            'image': 'chevron-left'
        }]
    })
    # insert slice_id in the action url
    form.action = form.action % slice_id
    c = RequestContext(request, {
        'slc': slc,
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request) 
    })
    return render_to_response('base-form.html', c)

@login_required
def remove_optimization_program(request, slice_id, optimizes_id):
    try:
        slc = Slice.objects.get(pk=slice_id)
    except Slice.DoesNotExist:
        raise Http404
    
    try:
        opt = OptimizesSlice.objects.get(pk=optimizes_id, slice=slc)
    except OptimizesSlice.DoesNotExist:
        raise Http404

    algo = opt.program
    opt.delete()

    session_flash.set_flash(request, "Optimization program %s was successfully removed from Slice %s!" % ( str(algo), str( slc ) ))
    logger.debug("Optimization program %s was successfully removed from Slice %s!" % (str(algo), str( slc )))
    
    return redirect(request.META['HTTP_REFERER'])

def export_all_flexcms(request):
    #Only calls the flexcms export function
    return HttpResponse(Monitoring.load().generate_flexcms_platform_xml())


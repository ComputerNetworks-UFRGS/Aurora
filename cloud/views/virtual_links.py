import logging
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.validators import EMPTY_VALUES
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, RequestContext
from django.template.loader import get_template
from cloud.helpers import session_flash, paginate
from cloud.models.slice import Slice
from cloud.models.virtual_link import VirtualLink
from cloud.models.virtual_link_qos import VirtualLinkQos
from cloud.models.virtual_machine import VirtualMachine
from cloud.models.virtual_interface import VirtualInterface
from cloud.widgets.number_input import NumberInput

# Configure logging for the module name
logger = logging.getLogger(__name__)
view_vars = {
    'active_item': None,
    'active_menu': 'Network',
    'active_section': 'Virtual Links',
}

#Form index filters
class VirtualLinksIndexFiltersForm(forms.Form):
    action = "/Aurora/cloud/virtual_links/"
    slices = Slice.objects.all()
    slice_choices = (("", "---------------"), (-1, "--Unbound Virtual Links--"))
    for slc in slices:
        slice_choices += ((slc.id, slc.name),)
    
    s = forms.ChoiceField(choices=slice_choices, label="Slice", required=False)

@login_required
def index(request):
    form = VirtualLinksIndexFiltersForm(request.GET) # Filter form
    if form.is_valid():
        s = form.cleaned_data['s']
        if s != '':
            # Search for unbound Virtual Links
            if s == '-1':
                s = None
            links = VirtualLink.objects.filter(belongs_to_slice=s)
        else:
            links = VirtualLink.objects.all()
    else:
        links = []

    link_list = paginate.paginate(links, request)

    t = get_template('virtual-links-index.html')
    view_vars.update({
        'active_item': None,
        'title': 'Virtual Links List',
        'actions': [{
            'name': 'New Virtual Link',
            'url': '/Aurora/cloud/virtual_links/new/',
            'image': 'plus'
        }]
    })
    
    c = Context({
        'filter_form': form,
        'view_vars': view_vars,
        'link_list': link_list,
        'paginate_list': link_list,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    
    return HttpResponse(t.render(c))

# Synchronizes virtual links with the controller
@login_required
def sync(request):
    # Dump the current link database on the controller
    link = VirtualLink()
    link.delete_all()

    # Loads the links again as a bundle (only deployed or failed)
    link_list = VirtualLink.objects.exclude(state='created')
    if len(link_list) > 0:
        try:
            link.establish_bundle(link_list)
            logger.debug("New Virtual bundle successfully established!")
            session_flash.set_flash(request, "Synchronization finished")
        except link.VirtualLinkException as e:
            session_flash.set_flash(request, "Could not establish virtual link(s) on network: %s" % str(e), "warning")
            logger.warning("Could not establish virtual link(s) on network: %s" % str(e))

    return redirect('cloud-virtual-links-index')

@login_required
def detail(request, virtual_link_id):
    try:
        link = VirtualLink.objects.get(pk=virtual_link_id)
    except VirtualLink.DoesNotExist:
        raise Http404

    view_vars.update({
        'active_item': link,
        'title': 'Virtual Link Details',
        'actions': [{
            'name': 'Back to List',
            'url': '/Aurora/cloud/virtual_links/',
            'image': 'chevron-left'
        }]
    })
    return render_to_response('virtual-links-detail.html', {'link': link, 'view_vars': view_vars, 'request': request, 'flash': session_flash.get_flash(request) })

class InterfaceModelChoiceField(forms.ModelChoiceField):
    # Override to_python function to avoid "select a valid choice" errors
    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        try:
            interface = VirtualInterface.objects.get(pk=value)
        except VirtualInterface.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])
        return interface

#Form for new Virtual Link creation
class LinkForm(forms.Form):
    action = "/Aurora/cloud/virtual_links/new/"
    vm_start = forms.ModelChoiceField(
        queryset=VirtualMachine.objects.all(), 
        empty_label="-- Select VM --", 
        label="VM start",
        widget=forms.Select(attrs={'onChange':'select_load_options(this, "/Aurora/cloud/virtual_machines/__selected_id__/interfaces/", "id_if_start")'})
    )
    if_start = InterfaceModelChoiceField(queryset=VirtualInterface.objects.none(), label="Interface start")
    vm_end  = forms.ModelChoiceField(
        queryset=VirtualMachine.objects.all(), 
        empty_label="-- Select VM --", 
        label="VM end",
        widget=forms.Select(attrs={'onChange':'select_load_options(this, "/Aurora/cloud/virtual_machines/__selected_id__/interfaces/", "id_if_end")'})
    )
    if_end = InterfaceModelChoiceField(queryset=VirtualInterface.objects.none(), label="Interface end")
    belongs_to_slice = forms.ModelChoiceField(queryset=Slice.objects.all(), required=False)

    # QoS Parameters
    bandwidth_up_maximum = forms.IntegerField(widget=NumberInput(attrs={"max": 1000, "min": 0, "step": 10}), max_value=1000, min_value=0, help_text="MB")
    bandwidth_up_committed = forms.IntegerField(widget=NumberInput(attrs={"max": 100, "min": 0, "step": 10}), max_value=100, min_value=0, help_text="%")
    bandwidth_down_maximum = forms.IntegerField(widget=NumberInput(attrs={"max": 1000, "min": 0, "step": 10}), max_value=1000, min_value=0, help_text="MB")
    bandwidth_down_committed = forms.IntegerField(widget=NumberInput(attrs={"max": 100, "min": 0, "step": 10}), max_value=100, min_value=0, help_text="%")
    latency = forms.IntegerField(widget=NumberInput(attrs={"max": 10000, "min": 0, "step": 100}), max_value=10000, min_value=0, help_text="ms", label="Maximum Latency")

    def clean(self):
        if_start = self.cleaned_data.get("if_start")
        if_end = self.cleaned_data.get("if_end")
        
        # Cannot create a virtual link to the same mac_address
        if if_start and if_end and if_start == if_end:
            msg = "Cannot create a virtual link to the same mac address"
            self._errors["if_start"] = self.error_class([msg])
            self._errors["if_end"] = self.error_class([msg])

            # These fields are no longer valid. Remove them from the cleaned data.
            del self.cleaned_data["if_start"]
            del self.cleaned_data["if_end"]

        # Always return the full collection of cleaned data.
        return self.cleaned_data
    
@login_required
def new(request):
    if request.method == 'POST': # If the form has been submitted...
        form = LinkForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            link = VirtualLink()
            link.if_start = form.cleaned_data['if_start']
            link.if_end = form.cleaned_data['if_end']
            link.belongs_to_slice = form.cleaned_data['belongs_to_slice']
            # Save Virtual Link
            link.save()
            
            link_qos = VirtualLinkQos()
            link_qos.bandwidth_up_maximum = form.cleaned_data['bandwidth_up_maximum']
            link_qos.bandwidth_up_committed = form.cleaned_data['bandwidth_up_committed']
            link_qos.bandwidth_down_maximum = form.cleaned_data['bandwidth_down_maximum']
            link_qos.bandwidth_down_committed = form.cleaned_data['bandwidth_down_committed']
            link_qos.latency = form.cleaned_data['latency']
            link_qos.belongs_to_virtual_link = link

            # Save Virtual Link Qos parameters
            link_qos.save()
            session_flash.set_flash(request, "New Virtual Link successfully created")

            try:
                link.establish()
                logger.debug("New Virtual Link (%s) successfully established!" % str(link))
            except link.VirtualLinkException as e:
                session_flash.set_flash(request, "Could not establish virtual link on network: %s" % str(e), "warning")
                logger.warning("Could not establish virtual link on network: %s" % str(e))

            return redirect('cloud-virtual-links-index') # Redirect after POST
        else:
            # TODO: Refill mac address fields when error occurs
            pass

    else:
        form = LinkForm() # An unbound form
    
    view_vars.update({
        'active_item': None,
        'title': 'New Virtual Link',
        'actions': [{
            'name': 'Back to List',
            'url': '/Aurora/cloud/virtual_links/',
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
def delete(request, virtual_link_id):
    try:
        link = VirtualLink.objects.get(pk=virtual_link_id)
    except VirtualLink.DoesNotExist:
        raise Http404
    
    # Undo OpenFlow stuff here
    try:
        link.unestablish()
        logger.debug("Virtual Link (%s) successfully unestablished!" % str(link))
    except link.VirtualLinkException as e:
        session_flash.set_flash(request, "Could not unestablish virtual link on network: %s" % str(e), "warning")
        logger.warning("Could not unestablish virtual link on network: %s" % str(e))

    link.delete()
    session_flash.set_flash(request, "Virtual Link <id: %s> was successfully deleted!" % virtual_link_id)
    logger.debug("Virtual Link <id: %s> was successfully deleted!" % virtual_link_id)
    
    return redirect(request.META['HTTP_REFERER'])

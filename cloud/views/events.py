import logging
import string
import time
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, loader
from django.template.context import RequestContext
from cloud.models.event import Event, EVENT_STATES, RELATIONAL_OPERATION
from cloud.models.metric import Metric
from cloud.models.slice import Slice
from cloud.models.optimization_program import OptimizationProgram
from cloud.helpers import session_flash

# Configure logging for the module name
logger = logging.getLogger(__name__)
active_menu = "Programs"

#Form index filters
class EventsIndexFiltersForm(forms.Form):
    slices = Slice.objects.all()
    slice_choices = (("", "---------------"), (-1, "--Unbound Events--"))
    for slc in slices:
        slice_choices += ((slc.id, slc.name),)

    s = forms.ChoiceField(choices=slice_choices, label="Slice", required=False)
    p = forms.CharField(widget=forms.HiddenInput(), required=False)

@login_required
def index(request):
    form = EventsIndexFiltersForm(request.GET) # Filter form
    if form.is_valid():
        s = form.cleaned_data['s']
        if s != '':
            # Search for unbound Events
            if s == '-1':
                s = None
            evs = Event.objects.filter(belongs_to_slice=s)
        else:
            evs = Event.objects.all()
    else:
        evs = []

    paginator = Paginator(evs, 10) # Show 10 objects per page

    p = request.GET.get('p')

    try:
        event_list = paginator.page(p)
    except (PageNotAnInteger, TypeError):
        event_list = paginator.page(1) # If page is not an integer, deliver first page.
    except EmptyPage:
        event_list = paginator.page(paginator.num_pages) # If page is out of range (e.g. 9999), deliver last page of results.

    t = loader.get_template('events-index.html')
    view_vars = {
        'active_menu': active_menu,
        'title': "Events List",
        'actions': [{ 'name': "New Event", 'url': "/Aurora/cloud/events/new/" }]
    }
    c = Context({
        'event_list': event_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return HttpResponse(t.render(c))

@login_required
def detail(request, event_id):
    view_vars = {
        'active_menu': active_menu,
        'title': "Event Details",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/cloud/events/" },
        ]
    }
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        raise Http404
    return render_to_response('events-detail.html', {'event': event, 'view_vars': view_vars, 'request': request })

#Form for new Event creation
class EventForm(forms.Form):
    action = "/Aurora/cloud/events/new/"
    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea)
    state = forms.ChoiceField(choices=EVENT_STATES)
    belongs_to_slice = forms.ModelChoiceField(queryset=Slice.objects.all(), required=False)
    metric = forms.ModelChoiceField(queryset=Metric.objects.all())
    relational_operation = forms.ChoiceField(choices=RELATIONAL_OPERATION)
    value = forms.CharField(max_length=200)
    program = forms.ModelChoiceField(queryset=OptimizationProgram.objects.all())
    
@login_required
def new(request):
    if request.method == 'POST': # If the form has been submitted...
        form = EventForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            event = Event()
            event.name = form.cleaned_data['name']
            event.description = form.cleaned_data['description']
            event.state = form.cleaned_data['state']
            event.belongs_to_slice = form.cleaned_data['belongs_to_slice']
            event.metric = form.cleaned_data['metric']
            event.relational_operation = form.cleaned_data['relational_operation']
            event.value = form.cleaned_data['value']
            event.program = form.cleaned_data['program']
            
            # TODO: Configure monitoring system for this event
            event.save()
            
            session_flash.set_flash(request, "New Event successfully created")
            return redirect('cloud-events-index') # Redirect after POST
    else:
        form = EventForm() # An unbound form
    
    view_vars = {
        'active_menu': active_menu,
        'title': "New Event",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/cloud/events/" },
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
def delete(request, event_id):
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        raise Http404
    
    event.delete()
    
    return redirect('cloud-events-index')



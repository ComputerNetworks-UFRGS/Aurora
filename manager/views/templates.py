import logging
from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, loader
from django.template.context import RequestContext
from manager.helpers import session_flash
from manager.models.template import Template
from manager.widgets.number_input import NumberInput

# Configure logging for the module name
logger = logging.getLogger(__name__)
active_menu = "Computing"

@login_required
def index(request):
    t = loader.get_template('templates-index.html')
    template_list = Template.objects.all()
    view_vars = {
        'active_menu': active_menu,
        'title': "Templates List",
        'actions': [{ 'name': "New Template", 'url': "/Aurora/manager/templates/new/" }]
    }
    c = Context({
        'template_list': template_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)

    })
    return HttpResponse(t.render(c))

@login_required
def detail(request, template_id):
    view_vars = {
        'active_menu': active_menu,
        'title': "Template Details",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/manager/templates/" },
        ]
    }
    try:
        template = Template.objects.get(pk=template_id)
    except Template.DoesNotExist:
        raise Http404
    return render_to_response('templates-detail.html', { 'template': template, 'view_vars': view_vars, 'request': request })


#Form for new Template creation
class TemplateForm(forms.Form):
    action = "/Aurora/manager/templates/new/"
    name = forms.CharField(max_length=200)
    memory = forms.IntegerField(widget=NumberInput(attrs={"max": 8192, "min": 64, "step": 64}), max_value=8192, min_value=64, help_text="Size in MB")
    vcpu = forms.IntegerField(widget=NumberInput(attrs={"max": 4, "min": 1, "step": 1}), max_value=4, min_value=1)
    description = forms.CharField(widget=forms.Textarea)
    
@login_required
def new(request):
    if request.method == 'POST': # If the form has been submitted...
        form = TemplateForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            t = Template()
            t.name = form.cleaned_data['name']
            t.memory = form.cleaned_data['memory']
            t.vcpu = form.cleaned_data['vcpu']
            t.description = form.cleaned_data['description']
            
            # Save to get an ID
            t.save()
            
            session_flash.set_flash(request, "New Template successfully created")
            return redirect('manager-templates-index') # Redirect after POST
    else:
        form = TemplateForm() # An unbound form
    
    view_vars = {
        'active_menu': active_menu,
        'title': "New Templates",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/manager/templates/" },
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
def delete(request, template_id):
    try:
        t = Template.objects.get(pk=template_id)
    except Template.DoesNotExist:
        raise Http404
    
    t.delete()
    session_flash.set_flash(request, "Template %s was successfully deleted!" % str(t))
    logger.debug("Host %s was successfully deleted!" % str(t))
    
    return redirect('manager-templates-index')

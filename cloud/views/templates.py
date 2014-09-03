import logging
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, loader
from django.template.context import RequestContext
from cloud.helpers import session_flash
from cloud.models.template import Template
from cloud.widgets.number_input import NumberInput

# Configure logging for the module name
logger = logging.getLogger(__name__)
view_vars = {
    'active_menu': 'Computing',
    'active_section': 'Templates',
}

@login_required
def index(request):
    global view_vars
    t = loader.get_template('templates-index.html')
    templates = Template.objects.all()

    paginator = Paginator(templates, 10)  # Show 10 objects per page
    p = request.GET.get('p')

    try:
        template_list = paginator.page(p)
    except (PageNotAnInteger, TypeError):
        # If page is not an integer, deliver first page.                                                  
        template_list = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        template_list = paginator.page(paginator.num_pages)

    view_vars.update({
        'title': 'Templates List',
        'actions': [{ 
            'name': 'New Template', 
            'url': '/Aurora/cloud/templates/new/',
            'image': 'plus'
        }]
    })
    c = Context({
        'template_list': template_list,
        'paginate_list': template_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)

    })
    return HttpResponse(t.render(c))

@login_required
def detail(request, template_id):
    global view_vars
    try:
        template = Template.objects.get(pk=template_id)
    except Template.DoesNotExist:
        raise Http404
    view_vars.update({
        'title': 'Template Details',
        'actions': [{
            'name': 'Back to List', 
            'url': '/Aurora/cloud/templates/',
            'image': 'chevron-left'
        }]
    })
    return render_to_response('templates-detail.html', { 'template': template, 'view_vars': view_vars, 'request': request })


#Form for new Template creation
class TemplateForm(forms.Form):
    action = "/Aurora/cloud/templates/new/"
    name = forms.CharField(max_length=200)
    memory = forms.IntegerField(widget=NumberInput(attrs={"max": 8192, "min": 64, "step": 64}), max_value=8192, min_value=64, help_text="Size in MB")
    vcpu = forms.IntegerField(widget=NumberInput(attrs={"max": 4, "min": 1, "step": 1}), max_value=4, min_value=1)
    description = forms.CharField(widget=forms.Textarea)
    
@login_required
def new(request):
    global view_vars
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
            return redirect('cloud-templates-index') # Redirect after POST
    else:
        form = TemplateForm() # An unbound form
    
    view_vars.update({
        'title': 'New Template',
        'actions': [{ 
            'name': 'Back to List', 
            'url': '/Aurora/cloud/templates/',
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
def delete(request, template_id):
    try:
        t = Template.objects.get(pk=template_id)
    except Template.DoesNotExist:
        raise Http404
    
    t.delete()
    session_flash.set_flash(request, "Template %s was successfully deleted!" % str(t))
    logger.debug("Host %s was successfully deleted!" % str(t))
    
    return redirect('cloud-templates-index')

import logging
from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, loader
from django.template.context import RequestContext
from cloud.helpers import session_flash
from cloud.models.monitoring import Monitoring
from cloud.widgets.number_input import NumberInput

# Configure logging for the module name
logger = logging.getLogger(__name__)
view_vars = {
    'active_item': None,
    'active_menu': 'Monitoring',
    'active_section': 'Settings',
}

#Form for editting monitoring settings
class MonitoringForm(forms.ModelForm):
    class Meta:
        model = Monitoring

#class MonitoringForm(forms.Form):
#    action = "/Aurora/cloud/monitoring/settings/"
#    name = forms.CharField(max_length=100)
#    hostname = forms.CharField(max_length=200)
#    path = forms.CharField(max_length=200)
#    username = forms.CharField(max_length=100)
#    password = forms.CharField(max_length=100)

@login_required
def settings(request):
    global view_vars
    if request.method == 'POST': # If the form has been submitted...
        form = MonitoringForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data

            m = Monitoring()
            m.name = form.cleaned_data['name']
            m.hostname = form.cleaned_data['hostname']
            m.path = form.cleaned_data['path']
            m.username = form.cleaned_data['username']
            m.password = form.cleaned_data['password']
            m.save()

            session_flash.set_flash(request, "Monitoring settings successfully saved")
            return redirect('cloud-monitoring-settings') # Redirect after POST
    else:
        form = MonitoringForm(instance=Monitoring.load()) # A form with saved info

    view_vars.update({
        'title': "Monitoring Settings",
    })
    c = RequestContext(request, {
        'form': form,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return render_to_response('base-form.html', c)

import logging
import string
import time
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, loader
from django.template.context import RequestContext
from manager.models.metric import Metric, METRIC_SCOPES, METRIC_STATES, RETURN_DATA_TYPE
from manager.helpers import session_flash

# Configure logging for the module name
logger = logging.getLogger(__name__)
active_menu = "Programs"

@login_required
def index(request):
    t = loader.get_template('metrics-index.html')
    metric_list = Metric.objects.all()
    view_vars = {
        'active_menu': active_menu,
        'title': "Metrics List",
        'actions': [{ 'name': "New Metric", 'url': "/Aurora/manager/metrics/new/" }]
    }
    c = Context({
        'metric_list': metric_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return HttpResponse(t.render(c))

@login_required
def detail(request, metric_id):
    view_vars = {
        'active_menu': active_menu,
        'title': "Metric Details",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/manager/metrics/" },
        ]
    }
    try:
        metric = Metric.objects.get(pk=metric_id)
    except Metric.DoesNotExist:
        raise Http404
    return render_to_response('metrics-detail.html', {'metric': metric, 'view_vars': view_vars, 'request': request })

#Form for new Metric creation
class MetricForm(forms.Form):
    action = "/Aurora/manager/metrics/new/"
    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea)
    returns = forms.ChoiceField(choices=RETURN_DATA_TYPE)
    scope = forms.ChoiceField(choices=METRIC_SCOPES)
    state = forms.ChoiceField(choices=METRIC_STATES)
    file = forms.CharField(widget=forms.Textarea)
    
    def clean(self):
        # Generate a valid filename
        valid = valid_chars = "-_.%s%s" % (string.ascii_letters, string.digits)
        filename = self.cleaned_data['name'].replace(" ", "_")
        
        final_filename = ""
        for c in filename:
            if c in valid:
                final_filename += c

        if len(final_filename) > 0:
            self.cleaned_data["filename"] = final_filename + ".py"
        else:
            msg = "Invalid name"
            self._errors["name"] = self.error_class([msg])
            del self.cleaned_data["name"]

        return self.cleaned_data

@login_required
def new(request):
    if request.method == 'POST': # If the form has been submitted...
        form = MetricForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            
            metr = Metric()
            metr.name = form.cleaned_data['name']
            metr.description = form.cleaned_data['description']
            metr.returns = form.cleaned_data['returns']
            metr.scope = form.cleaned_data['scope']
            metr.state = form.cleaned_data['state']
            #Save the contents in a file
            filename = form.cleaned_data['filename']
            metr.file.save(filename, ContentFile(form.cleaned_data['file']))
            
            metr.save()
            
            session_flash.set_flash(request, "New Metric successfully created")
            return redirect('manager-metrics-index') # Redirect after POST
    else:
        form = MetricForm() # An unbound form
    
    view_vars = {
        'active_menu': active_menu,
        'title': "New Metric",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/manager/metrics/" },
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
def delete(request, metric_id):
    try:
        metr = Metric.objects.get(pk=metric_id)
    except Metric.DoesNotExist:
        raise Http404
    
    # Delete saved file
    try:
        metr.file.delete()
        session_flash.set_flash(request, "Metric %s was successfully deleted!" % str(metr))
        logger.debug("Metric %s was successfully deleted!" % str(metr))
    except:
        session_flash.set_flash(request, "Could not delete file %s of metric %s: %s" % (metr.file, str(metr), str(e)), "warning")

    metr.delete()
    
    return redirect('manager-metrics-index')

# Remote call to metrics
def web_services(request, metric_name):
    # Load metric and run
    try:
        metric = Metric.objects.get(name=metric_name)
    except Metric.DoesNotExist:
        raise Http404

    # File name without the '.py' and with '/' replaced by '.'
    file_path = metric.file.name[0:-3].replace("/", ".")
    # Generata a list to extract the classname
    metric_classname = file_path.split(".")[-1]
    metric_path = 'Aurora.manager.' + file_path
    try:
        metric_module = __import__(metric_path, fromlist=[metric_classname])
        metric_class = getattr(metric_module, metric_classname)
    except (ImportError, NotImplementedError) as e:
        logger.error("Problems loading metric: " + str(e))
        return HttpResponse("Problems loading metric: " + str(e) + " - " + metric_path + " - " + metric_classname)
    except AttributeError as e:
        logger.error("Must implement main class: " + str(e))
        return HttpResponse("Must implement main class: " + str(e))

    try:
        metric = metric_class()
        # Will record collecting time
        t0 = time.time()
        kargs = {}
        for param in request.GET:
            kargs[param] = request.GET.get(param)

        if len(kargs) > 0:
            result = metric.collect(**kargs)
        else:
            result = metric.collect()

        collecting_time = time.time() - t0
        logger.info("Metric %s successfully collected in %d seconds" % (metric_classname, round(collecting_time, 2)))
    except TypeError as e:
        logger.error("Wrong parameters: %s" % str(e))
        return HttpResponse("Wrong parameters: %s" % str(e))
    except metric.MetricException as e:
        logger.error("Problems collecting metric: %s" % str(e))
        return HttpResponse("Problems collecting metric: %s" % str(e))

    return HttpResponse(result)



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
from manager.models.program import PROGRAM_STATES
from manager.models.optimization_program import OptimizationProgram, OPTMIZATION_SCOPES
from manager.helpers import session_flash

# Configure logging for the module name
logger = logging.getLogger(__name__)
active_menu = "Programs"

@login_required
def index(request):
    t = loader.get_template('optimization-programs-index.html')
    program_list = OptimizationProgram.objects.all()
    view_vars = {
        'active_menu': active_menu,
        'title': "Optimization Programs List",
        'actions': [{ 'name': "New Optimization Program", 'url': "/Aurora/manager/optimization_programs/new/" }]
    }
    c = Context({
        'program_list': program_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return HttpResponse(t.render(c))

@login_required
def detail(request, optimization_program_id):
    view_vars = {
        'active_menu': active_menu,
        'title': "Optimization Program Details",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/manager/optimization_programs/" },
        ]
    }
    try:
        optimization_program = OptimizationProgram.objects.get(pk=optimization_program_id)
    except OptimizationProgram.DoesNotExist:
        raise Http404
    return render_to_response('optimization-programs-detail.html', {'program': optimization_program, 'view_vars': view_vars, 'request': request })

#Form for new Optimization Program creation
class OptimizationProgramForm(forms.Form):
    action = "/Aurora/manager/optimization_programs/new/"
    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea)
    scope = forms.ChoiceField(choices=OPTMIZATION_SCOPES)
    state = forms.ChoiceField(choices=PROGRAM_STATES)
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
        form = OptimizationProgramForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data

            alg = OptimizationProgram()
            alg.name = form.cleaned_data['name']
            alg.description = form.cleaned_data['description']
            alg.scope = form.cleaned_data['scope']
            alg.state = form.cleaned_data['state']
            #Save the contents in a file
            filename = form.cleaned_data['filename']
            alg.file.save(filename, ContentFile(form.cleaned_data['file']))

            alg.save()

            session_flash.set_flash(request, "New Optimization Program successfully created")
            return redirect('manager-optimization-programs-index') # Redirect after POST
    else:
        form = OptimizationProgramForm() # An unbound form

    view_vars = {
        'active_menu': active_menu,
        'title': "New Optimization Program",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/manager/optimization_programs/" },
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
def delete(request, optimization_program_id):
    try:
        alg = OptimizationProgram.objects.get(pk=optimization_program_id)
    except OptimizationProgram.DoesNotExist:
        raise Http404

    # Delete saved file
    try:
        alg.file.delete()
        session_flash.set_flash(request, "Optimization Program %s was successfully deleted!" % str(alg))
        logger.debug("Optimization Program %s was successfully deleted!" % str(alg))
    except:
        session_flash.set_flash(request, "Could not delete file %s of program %s: %s" % (alg.file, str(alg), str(e)), "warning")

    alg.delete()

    return redirect('manager-optimization-programs-index')

# Remote call to optimization programs
def web_services(request, program_name):
    # Load program and run
    try:
        program = OptimizationProgram.objects.get(name=program_name)
    except OptimizationProgram.DoesNotExist:
        raise Http404

    # File name without the '.py' and with '/' replaced by '.'
    file_path = program.file.name[0:-3].replace("/", ".")
    # Generata a list to extract the classname
    program_classname = file_path.split(".")[-1]
    program_path = 'Aurora.manager.' + file_path
    try:
        program_module = __import__(program_path, fromlist=[program_classname])
        program_class = getattr(program_module, program_classname)
    except (ImportError, NotImplementedError) as e:
        logger.error("Problems loading program: " + str(e))
        return HttpResponse("Problems loading program: " + str(e))
    except AttributeError as e:
        logger.error("Must implement main class: " + str(e))
        return HttpResponse("Must implement main class: " + str(e))

    try:
        algo = program_class()
        # Will record optimization time
        t0 = time.time()
        if algo.optimize():
            optimization_time = time.time() - t0
            logger.info("Optimization successfully executed in " + str(round(optimization_time, 2)) + " seconds")
    except algo.OptimizationException as e:
        logger.error("Problems executing optimization: " + str(e))
        return HttpResponse("Problems executing optimization: " + str(e))

    return HttpResponse("OK")



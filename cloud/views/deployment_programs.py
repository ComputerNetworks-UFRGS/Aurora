import logging
import string
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, loader
from django.template.context import RequestContext
from cloud.models.program import PROGRAM_STATES
from cloud.models.deployment_program import DeploymentProgram
from cloud.helpers import session_flash

# Configure logging for the module name
logger = logging.getLogger(__name__)
active_menu = "Programs"


@login_required
def index(request):
    t = loader.get_template('deployment-programs-index.html')
    program_list = DeploymentProgram.objects.all()
    view_vars = {
        'active_menu': active_menu,
        'title': "Deployment Programs List",
        'actions': [{ 'name': "New Deployment Program", 'url': "/Aurora/cloud/deployment_programs/new/" }]
    }
    c = Context({
        'program_list': program_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return HttpResponse(t.render(c))

@login_required
def detail(request, deployment_program_id):
    view_vars = {
        'active_menu': active_menu,
        'title': "Deployment Program Details",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/cloud/deployment_programs/" },
        ]
    }
    try:
        deployment_program = DeploymentProgram.objects.get(pk=deployment_program_id)
    except DeploymentProgram.DoesNotExist:
        raise Http404
    return render_to_response('deployment-programs-detail.html', {'program': deployment_program, 'view_vars': view_vars, 'request': request })

#Form for new Deployment Program creation
class DeploymentProgramForm(forms.Form):
    action = "/Aurora/cloud/deployment_programs/new/"
    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea)
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
            self._dangers["name"] = self.danger_class([msg])
            del self.cleaned_data["name"]

        return self.cleaned_data

@login_required
def new(request):
    if request.method == 'POST': # If the form has been submitted...
        form = DeploymentProgramForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data

            alg = DeploymentProgram()
            alg.name = form.cleaned_data['name']
            alg.description = form.cleaned_data['description']
            alg.state = form.cleaned_data['state']
            #Save the contents in a file
            filename = form.cleaned_data['filename']
            alg.file.save(filename, ContentFile(form.cleaned_data['file']))

            alg.save()

            session_flash.set_flash(request, "New Deployment Program successfully created")
            return redirect('cloud-deployment-programs-index') # Redirect after POST
    else:
        form = DeploymentProgramForm() # An unbound form

    view_vars = {
        'active_menu': active_menu,
        'title': "New Deployment Program",
        'actions': [
            { 'name': "Back to List", 'url': "/Aurora/cloud/deployment_programs/" },
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
def delete(request, deployment_program_id):
    try:
        alg = DeploymentProgram.objects.get(pk=deployment_program_id)
    except DeploymentProgram.DoesNotExist:
        raise Http404

    # Delete saved file
    try:
        alg.file.delete()
        session_flash.set_flash(request, "Deployment Program %s was successfully deleted!" % str(alg))
        logger.debug("Deployment Program %s was successfully deleted!" % str(alg))
    except:
        session_flash.set_flash(request, "Could not delete file %s of program %s: %s" % (alg.file, str(alg), str(e)), "warning")

    alg.delete()

    return redirect('cloud-deployment-programs-index')

import logging
from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect
from django.template import Context, loader
from django.template.context import RequestContext
from manager.models.image import Image, IMG_FORMATS, IMG_TARGETS
from manager.helpers import session_flash

# Configure logging for the module name
logger = logging.getLogger(__name__)
active_menu = "Computing"


@login_required
def index(request):
    t = loader.get_template('images-index.html')
    image_list = Image.objects.all()
    view_vars = {
        'active_menu': active_menu,
        'title': "Images List",
        'actions': [{
            'name': "New Image",
            'url': "/Aurora/manager/images/new/"
        }]
    }
    c = Context({
        'image_list': image_list,
        'view_vars': view_vars,
        'request': request,
        'flash': session_flash.get_flash(request)
    })
    return HttpResponse(t.render(c))


@login_required
def detail(request, image_id):
    view_vars = {
        'active_menu': active_menu,
        'title': "Image Details",
        'actions': [
            {'name': "Back to List", 'url': "/Aurora/manager/images/"},
        ]
    }
    try:
        image = Image.objects.get(pk=image_id)
    except Image.DoesNotExist:
        raise Http404
    return render_to_response('images-detail.html', {
        'image': image,
        'view_vars': view_vars,
        'request': request
    })


#Form for new Image creation
class ImageForm(forms.Form):
    action = "/Aurora/manager/images/new/"
    name = forms.CharField(max_length=200)
    path = forms.CharField(max_length=200)
    file_format = forms.ChoiceField(choices=IMG_FORMATS)
    target_dev = forms.ChoiceField(choices=IMG_TARGETS)
    description = forms.CharField(widget=forms.Textarea)


@login_required
def new(request):
    if request.method == 'POST':  # If the form has been submitted...
        form = ImageForm(request.POST)  # A form bound to the POST data
        if form.is_valid():  # All validation rules pass
            # Process the data in form.cleaned_data

            img = Image()
            img.name = form.cleaned_data['name']
            img.path = form.cleaned_data['path']
            img.file_format = form.cleaned_data['file_format']
            img.target_dev = form.cleaned_data['target_dev']
            img.description = form.cleaned_data['description']

            # Save to get an ID
            img.save()

            session_flash.set_flash(request, "New Image successfully created")
            return redirect('manager-images-index')  # Redirect after POST
    else:
        form = ImageForm()  # An unbound form

    view_vars = {
        'active_menu': active_menu,
        'title': "New Image",
        'actions': [
            {'name': "Back to List", 'url': "/Aurora/manager/images/"},
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
def delete(request, image_id):
    try:
        img = Image.objects.get(pk=image_id)
    except Image.DoesNotExist:
        raise Http404

    img.delete()
    session_flash.set_flash(
        request,
        "Image %s was successfully deleted!" % str(img)
    )
    logger.debug("Host %s was successfully deleted!" % str(img))

    return redirect('manager-images-index')

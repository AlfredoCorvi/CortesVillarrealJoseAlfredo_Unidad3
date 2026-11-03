from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from .forms import RegistrationForm
from .planets import PLANETS
from .nasa import TOPICS, NasaUnavailable, images_for


@require_http_methods(['GET'])
def nasa_gallery(request):
    topic = request.GET.get('tema', 'nebulosas')
    if topic not in TOPICS:
        topic = 'nebulosas'
    context = {'topics': TOPICS, 'selected_topic': topic}
    try:
        context['images'] = images_for(topic)
    except NasaUnavailable:
        context['unavailable'] = True
    return render(request, 'universe/nasa.html', context,
                  status=503 if context.get('unavailable') else 200)


@sensitive_post_parameters('password1', 'password2')
@never_cache
@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = RegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Tu cuenta está lista. ¡Bienvenido a Cosmoz!')
        return redirect('home')
    return render(request, 'universe/auth/register.html', {'form': form})


def index(request):
    context = {
        'title': 'Cosmoz | Tu viaje al universo',
        'planets': PLANETS,
    }

    return render(request, 'universe/index.html', context)

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from .forms import RegistrationForm
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
        'planets': [
            {'name': 'Mercurio', 'slug': 'mercurio', 'group': 'rocosos', 'kind': 'Planeta rocoso', 'description': 'El mundo más cercano al Sol. Su superficie rocosa está cubierta de cráteres y su atmósfera es casi inexistente.'},
            {'name': 'Venus', 'slug': 'venus', 'group': 'rocosos', 'kind': 'Planeta rocoso', 'description': 'Envuelto en espesas nubes, Venus es el planeta más caliente del sistema solar. Su atmósfera retiene el calor en un intenso efecto invernadero.'},
            {'name': 'Tierra', 'slug': 'tierra', 'group': 'rocosos', 'kind': 'Planeta rocoso', 'description': 'Nuestro hogar en el universo. Sus océanos de agua líquida y su atmósfera hacen posible la vida que conocemos.'},
            {'name': 'Marte', 'slug': 'marte', 'group': 'rocosos', 'kind': 'Planeta rocoso', 'description': 'El planeta rojo debe su color al óxido de hierro. Sus valles, volcanes y casquetes polares guardan pistas sobre su pasado.'},
            {'name': 'Júpiter', 'slug': 'jupiter', 'group': 'gigantes', 'kind': 'Gigante gaseoso', 'description': 'El planeta más grande de nuestro sistema solar. Sus bandas de nubes y su Gran Mancha Roja revelan una atmósfera llena de tormentas.'},
            {'name': 'Saturno', 'slug': 'saturno', 'group': 'gigantes', 'kind': 'Gigante gaseoso', 'description': 'Sus espectaculares anillos están formados por innumerables fragmentos de hielo y roca. Es el segundo planeta más grande del sistema solar.'},
            {'name': 'Urano', 'slug': 'urano', 'group': 'gigantes', 'kind': 'Gigante helado', 'description': 'Este mundo azul verdoso gira prácticamente de lado. El metano de su atmósfera contribuye a su característico color.'},
            {'name': 'Neptuno', 'slug': 'neptuno', 'group': 'gigantes', 'kind': 'Gigante helado', 'description': 'El más lejano de los ocho planetas. Su atmósfera azul alberga vientos intensos, muy lejos de la luz y el calor del Sol.'},
        ],
    }

    return render(request, 'universe/index.html', context)

"""Public, read-only web service for the Cosmoz planet catalog."""
from django.http import JsonResponse
from django.views.decorators.http import require_safe

from .planets import PLANETS


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False})


@require_safe
def planet_list(request):
    group = request.GET.get('grupo')
    if group is not None and group not in ('rocosos', 'gigantes'):
        return json_response({'error': {
            'code': 'invalid_group',
            'message': 'El grupo debe ser rocosos o gigantes.',
        }}, status=400)
    planets = [planet for planet in PLANETS if group is None or planet['group'] == group]
    return json_response({'count': len(planets), 'results': planets})


@require_safe
def planet_detail(request, slug):
    planet = next((planet for planet in PLANETS if planet['slug'] == slug), None)
    if planet is None:
        return json_response({'error': {
            'code': 'planet_not_found',
            'message': 'No se encontró el planeta solicitado.',
        }}, status=404)
    return json_response(planet)

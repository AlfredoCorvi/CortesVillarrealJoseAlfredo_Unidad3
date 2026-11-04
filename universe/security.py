import time
import unicodedata

from django.conf import settings
from django.db.models import F
from django.http import HttpResponse
from django.utils.crypto import salted_hmac
from django.utils.deprecation import MiddlewareMixin

from .models import AuthRequestBucket


class SecurityMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        route = request.resolver_match.view_name
        if request.method != 'POST' or route not in ('login', 'register', 'admin:login'):
            return None
        now = int(time.time())
        window = settings.AUTH_RATE_WINDOW_SECONDS
        bucket = now // window
        expires = (bucket + 1) * window
        # REMOTE_ADDR is supplied by the server. Never trust client forwarding headers.
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        scope = 'register' if route == 'register' else 'login'
        limits = [(f'{scope}:ip:{ip}', settings.AUTH_RATE_IP_LIMIT)]
        if scope == 'login':
            username = unicodedata.normalize('NFKC', request.POST.get('username', '')).strip().casefold()
            limits.append((f'login:account:{username}', settings.AUTH_RATE_ACCOUNT_LIMIT))
        AuthRequestBucket.objects.filter(expires_at__lte=now).delete()
        for identity, limit in limits:
            key = salted_hmac('cosmoz.auth-rate', f'{bucket}:{identity}', algorithm='sha256').hexdigest()
            AuthRequestBucket.objects.get_or_create(key=key, defaults={'expires_at': expires})
            # Conditional SQL increment keeps the limit atomic across workers.
            accepted = AuthRequestBucket.objects.filter(key=key, attempts__lt=limit).update(attempts=F('attempts') + 1)
            if not accepted:
                response = HttpResponse(
                    'Demasiados intentos. Espera unos minutos antes de volver a intentarlo.',
                    status=429, content_type='text/plain; charset=utf-8',
                )
                response['Retry-After'] = str(expires - now)
                response['Cache-Control'] = 'no-store'
                return response

    def process_response(self, request, response):
        match = getattr(request, 'resolver_match', None)
        # Admin uses Django's own templates, which have separate styling requirements.
        if not match or match.app_name != 'admin':
            response['Content-Security-Policy'] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' https://images-assets.nasa.gov; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response

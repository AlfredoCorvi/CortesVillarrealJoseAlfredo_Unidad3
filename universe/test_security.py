from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from .models import AuthRequestBucket


@override_settings(
    AUTH_RATE_ACCOUNT_LIMIT=2, AUTH_RATE_IP_LIMIT=3, AUTH_RATE_WINDOW_SECONDS=600,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class SecurityTests(TestCase):
    def test_account_limit_is_shared_with_admin_and_across_ips(self):
        self.client.post('/universe/login/', {'username': 'Explorer'})
        self.client.post('/admin/login/', {'username': 'explorer'}, REMOTE_ADDR='192.0.2.2')
        response = self.client.post('/universe/login/', {'username': 'EXPLORER'}, REMOTE_ADDR='192.0.2.3')
        self.assertEqual(response.status_code, 429)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertTrue(1 <= int(response['Retry-After']) <= 600)
        self.assertFalse(any('explorer' in key for key in AuthRequestBucket.objects.values_list('key', flat=True)))

    def test_ip_limit_blocks_rotating_usernames_and_ignores_forwarded_headers(self):
        for i in range(3):
            self.assertEqual(self.client.post('/universe/login/', {'username': f'user{i}'}).status_code, 200)
        response = self.client.post('/universe/login/', {'username': 'new'}, HTTP_X_FORWARDED_FOR='192.0.2.99')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(self.client.post('/universe/login/', {'username': 'new'}, REMOTE_ADDR='192.0.2.99').status_code, 200)

    def test_registration_limit(self):
        for _ in range(3):
            self.assertEqual(self.client.post('/universe/registro/', {}).status_code, 200)
        self.assertEqual(self.client.post('/universe/registro/', {}).status_code, 429)
        self.assertEqual(self.client.get('/universe/registro/').status_code, 200)

    def test_window_expires_and_old_counters_are_removed(self):
        with patch('universe.security.time.time', return_value=1201):
            for _ in range(2):
                self.client.post('/universe/login/', {'username': 'test'})
            self.assertEqual(self.client.post('/universe/login/', {'username': 'test'}).status_code, 429)
        with patch('universe.security.time.time', return_value=1801):
            self.assertEqual(self.client.post('/universe/login/', {'username': 'test'}).status_code, 200)
        self.assertFalse(AuthRequestBucket.objects.filter(expires_at__lte=1801).exists())

    def test_csrf_is_checked_before_counting(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/universe/login/', {'username': 'test'}).status_code, 403)
        self.assertFalse(AuthRequestBucket.objects.exists())
        client.get('/universe/login/')
        self.assertEqual(client.post('/universe/login/', {
            'username': 'test', 'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        }).status_code, 200)
        self.assertTrue(AuthRequestBucket.objects.exists())

    def test_public_security_headers_and_admin_compatibility(self):
        for path in ('/', '/universe/login/', '/api/planetas/'):
            response = self.client.get(path)
            self.assertEqual(response['X-Frame-Options'], 'DENY')
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
            self.assertEqual(response['Referrer-Policy'], 'same-origin')
            policy = response['Content-Security-Policy']
            self.assertIn("script-src 'self'", policy)
            self.assertIn('https://images-assets.nasa.gov', policy)
            self.assertNotIn('unsafe-inline', policy)
            self.assertIn('camera=()', response['Permissions-Policy'])
        self.assertNotIn('Content-Security-Policy', self.client.get('/admin/login/'))

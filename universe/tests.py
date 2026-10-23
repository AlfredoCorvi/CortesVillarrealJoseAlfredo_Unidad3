from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class AuthenticationTests(TestCase):
    def test_login_errors_do_not_reveal_account_status(self):
        get_user_model().objects.create_user(username='active', password='Secret!7392')
        get_user_model().objects.create_user(
            username='inactive', password='Secret!7392', is_active=False,
        )
        errors = []
        for username, password in [('missing', 'Secret!7392'), ('active', 'wrong'), ('inactive', 'Secret!7392')]:
            response = self.client.post(reverse('login'), {'username': username, 'password': password})
            errors.append(list(response.context['form'].non_field_errors()))
            self.assertNotIn('_auth_user_id', self.client.session)
            self.assertNotContains(response, 'value="' + password + '"')
        self.assertTrue(errors[0])
        self.assertEqual(errors[0], errors[1])
        self.assertEqual(errors[1], errors[2])

    def test_login_rotates_session_and_expires_without_sliding(self):
        get_user_model().objects.create_user(username='active', password='Secret!7392')
        session = self.client.session
        session['visit'] = 'before-login'
        session.save()
        old_key = session.session_key
        response = self.client.post(reverse('login'), {'username': 'active', 'password': 'Secret!7392'})
        self.assertNotEqual(old_key, self.client.session.session_key)
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')
        self.assertEqual(cookie['expires'], '')
        stored = Session.objects.get(session_key=self.client.session.session_key)
        self.assertAlmostEqual((stored.expire_date - timezone.now()).total_seconds(), 3600, delta=10)
        session_expiry = stored.expire_date
        self.client.get(reverse('home'))
        stored.refresh_from_db()
        self.assertEqual(stored.expire_date, session_expiry)
        Session.objects.filter(pk=stored.pk).update(expire_date=timezone.now() - timedelta(seconds=1))
        response = self.client.get(reverse('home'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_response_is_not_cached_and_supports_password_managers(self):
        response = self.client.get(reverse('login'))
        self.assertIn('no-store', response.headers['Cache-Control'])
        for attribute in ['autocomplete="username"', 'autocomplete="current-password"', 'autocapitalize="none"', 'spellcheck="false"']:
            self.assertContains(response, attribute)

    def registration_data(self, **changes):
        data = {
            'username': 'explorador',
            'email': 'explorador@example.com',
            'password1': 'Nebulosa!7392-cielo',
            'password2': 'Nebulosa!7392-cielo',
        }
        data.update(changes)
        return data

    def test_registration_persists_hashed_password_and_logs_in(self):
        response = self.client.post(reverse('register'), self.registration_data())
        self.assertRedirects(response, reverse('home'))
        user = get_user_model().objects.get(username='explorador')
        self.assertEqual(user.email, 'explorador@example.com')
        self.assertNotEqual(user.password, self.registration_data()['password1'])
        self.assertTrue(user.check_password(self.registration_data()['password1']))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))
        self.assertContains(self.client.get(reverse('home')), 'Cerrar sesión')

    def test_invalid_registration_does_not_create_user(self):
        for changes in [
            {'password2': 'different'},
            {'password1': '123', 'password2': '123'},
            {'email': 'invalid'},
            {'email': ''},
            {'username': ''},
        ]:
            with self.subTest(changes=changes):
                response = self.client.post(reverse('register'), self.registration_data(**changes))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
                self.assertFalse(get_user_model().objects.exists())

    def test_duplicate_username_is_rejected(self):
        get_user_model().objects.create_user(username='Explorador', password='Original!7392')
        response = self.client.post(reverse('register'), self.registration_data())
        self.assertIn('username', response.context['form'].errors)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_login_and_post_logout(self):
        user = get_user_model().objects.create_user(username='explorador', password='Nebulosa!7392-cielo')
        response = self.client.post(reverse('login'), {'username': user.username, 'password': 'Nebulosa!7392-cielo'})
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_password_and_inactive_account_cannot_login(self):
        user = get_user_model().objects.create_user(username='explorador', password='Nebulosa!7392-cielo')
        for active, password in [(True, 'wrong'), (False, 'Nebulosa!7392-cielo')]:
            with self.subTest(active=active):
                user.is_active = active
                user.save()
                response = self.client.post(reverse('login'), {'username': user.username, 'password': password})
                self.assertTrue(response.context['form'].non_field_errors())
                self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_redirects_only_to_local_urls(self):
        get_user_model().objects.create_user(username='explorador', password='Nebulosa!7392-cielo')
        for next_url, expected in [('https://example.com/', reverse('home')), ('/universe/', '/universe/')]:
            with self.subTest(next_url=next_url):
                self.client.logout()
                response = self.client.post(reverse('login'), {
                    'username': 'explorador', 'password': 'Nebulosa!7392-cielo', 'next': next_url,
                })
                self.assertRedirects(response, expected)

    def test_authenticated_users_skip_login_and_registration(self):
        user = get_user_model().objects.create_user(username='explorador', password='Nebulosa!7392-cielo')
        self.client.force_login(user)
        for route in ['login', 'register']:
            self.assertRedirects(self.client.get(reverse(route)), reverse('home'))

    def test_csrf_protects_all_authentication_posts(self):
        client = Client(enforce_csrf_checks=True)
        for route in ['login', 'register', 'logout']:
            self.assertEqual(client.post(reverse(route), self.registration_data()).status_code, 403)
        response = client.get(reverse('register'))
        self.assertContains(response, 'csrfmiddlewaretoken')
        data = self.registration_data()
        data['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        self.assertRedirects(client.post(reverse('register'), data), reverse('home'))
        self.assertRedirects(client.post(reverse('logout'), {
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        }), reverse('home'))

    def test_public_pages_show_authentication_links(self):
        for path in [reverse('home'), reverse('index')]:
            self.assertContains(self.client.get(path), reverse('register'))
        for route in ['login', 'register']:
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'name="csrfmiddlewaretoken"')

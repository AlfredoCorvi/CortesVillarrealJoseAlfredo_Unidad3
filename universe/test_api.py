from django.test import SimpleTestCase, override_settings
from django.urls import reverse


class PlanetApiTests(SimpleTestCase):
    def test_public_catalog_and_detail(self):
        response = self.client.get('/api/planetas/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        catalog = response.json()
        self.assertEqual(catalog['count'], 8)
        self.assertEqual([p['slug'] for p in catalog['results']], [
            'mercurio', 'venus', 'tierra', 'marte', 'jupiter', 'saturno', 'urano', 'neptuno',
        ])
        for planet in catalog['results']:
            with self.subTest(planet=planet['slug']):
                self.assertEqual(set(planet), {'name', 'slug', 'group', 'kind', 'description'})
                detail = self.client.get(reverse('api:planet_detail', args=[planet['slug']]))
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(detail.json(), planet)

    def test_filter_does_not_change_catalog(self):
        for group in ('rocosos', 'gigantes'):
            response = self.client.get(reverse('api:planet_list'), {'grupo': group})
            self.assertEqual(response.json()['count'], 4)
            self.assertTrue(all(p['group'] == group for p in response.json()['results']))
        self.assertEqual(self.client.get('/api/planetas/').json()['count'], 8)

    def test_invalid_filter_and_missing_planet(self):
        for group in ('', 'otro'):
            response = self.client.get('/api/planetas/', {'grupo': group})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error']['code'], 'invalid_group')
        response = self.client.get('/api/planetas/pluton/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error']['code'], 'planet_not_found')

    def test_read_only_and_head(self):
        for url in ('/api/planetas/', '/api/planetas/tierra/'):
            for method in ('post', 'put', 'patch', 'delete'):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response['Allow'], 'GET, HEAD')
            response = self.client.head(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b'')

    @override_settings(STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    })
    def test_home_and_api_share_catalog(self):
        home = self.client.get(reverse('home'))
        self.assertEqual(home.context['planets'], self.client.get('/api/planetas/').json()['results'])

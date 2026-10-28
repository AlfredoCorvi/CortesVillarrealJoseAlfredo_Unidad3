import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from .nasa import NasaUnavailable, images_for


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class NasaTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.payload = {'collection': {'items': [{
            'data': [{'nasa_id': 'test/id', 'title': '<script>alert(1)</script>',
                      'description': '<b>Nebula</b>', 'center': 'JPL'}],
            'links': [{'rel': 'preview', 'href': 'https://images-assets.nasa.gov/image/test.jpg'}],
        }]}}

    def mock_response(self, mock, payload):
        mock.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()

    @patch('universe.nasa.urlopen')
    def test_contract_cache_and_safe_rendering(self, mock):
        self.mock_response(mock, self.payload)
        response = self.client.get(reverse('nasa_gallery'), {'tema': 'marte'})
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>')
        self.assertContains(response, 'https://images.nasa.gov/details/test%2Fid')
        self.assertEqual(images_for('marte')[0]['description'], 'Nebula')
        mock.assert_called_once()
        self.assertIn('q=Mars', mock.call_args.args[0].full_url)
        self.assertEqual(mock.call_args.kwargs['timeout'], 8)

    @patch('universe.nasa.urlopen')
    def test_failures_show_retry_and_are_not_cached(self, mock):
        for error in [TimeoutError(), URLError('offline'),
                      HTTPError('https://images-api.nasa.gov', 429, 'Limited', {}, None)]:
            with self.subTest(error=error):
                mock.side_effect = error
                response = self.client.get(reverse('nasa_gallery'))
                self.assertContains(response, 'Reintentar', status_code=503)
        mock.side_effect = None
        self.mock_response(mock, self.payload)
        self.assertEqual(self.client.get(reverse('nasa_gallery')).status_code, 200)

    @patch('universe.nasa.urlopen')
    def test_empty_results_and_unknown_topic(self, mock):
        self.mock_response(mock, {'collection': {'items': []}})
        response = self.client.get(reverse('nasa_gallery'), {'tema': 'https://evil.example'})
        self.assertContains(response, 'No se encontraron imágenes')
        self.assertIn('q=nebula', mock.call_args.args[0].full_url)
        self.assertEqual(self.client.post(reverse('nasa_gallery')).status_code, 405)

    @patch('universe.nasa.urlopen')
    def test_malformed_response_and_untrusted_image(self, mock):
        for payload in [None, {}, {'collection': {'items': None}}, {'collection': {'items': [None]}}]:
            self.mock_response(mock, payload)
            with self.assertRaises(NasaUnavailable):
                images_for('saturno')
        mock.return_value.__enter__.return_value.read.return_value = b'not json'
        with self.assertRaises(NasaUnavailable):
            images_for('saturno')
        self.payload['collection']['items'][0]['links'][0]['href'] = 'https://evil.example/image.jpg'
        self.mock_response(mock, self.payload)
        with self.assertRaises(NasaUnavailable):
            images_for('saturno')

"""Small client for NASA Image and Video Library (no API key required)."""
import json
from urllib.error import URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.utils.html import strip_tags

TOPICS = {'nebulosas': ('Nebulosas', 'nebula'), 'marte': ('Marte', 'Mars'),
          'saturno': ('Saturno', 'Saturn')}


class NasaUnavailable(Exception):
    pass


def images_for(topic):
    query = TOPICS[topic][1]
    key = f'nasa-images-v1:{topic}'
    cached = cache.get(key)
    if cached is not None:
        return cached
    url = 'https://images-api.nasa.gov/search?' + urlencode({
        'q': query, 'media_type': 'image', 'page_size': 6,
    })
    try:
        request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'Cosmoz/1.0'})
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read(1_000_001))
        items = payload['collection']['items']
        if not isinstance(items, list):
            raise ValueError('Invalid items')
        images = []
        for item in items[:6]:
            try:
                data = item['data'][0]
                preview = next(link['href'] for link in item['links']
                               if link.get('rel') == 'preview')
                parsed = urlsplit(preview)
                if parsed.scheme != 'https' or parsed.hostname != 'images-assets.nasa.gov':
                    continue
                nasa_id = data['nasa_id']
                title = data['title']
                if not isinstance(nasa_id, str) or not isinstance(title, str):
                    continue
                images.append({
                    'title': title, 'image_url': preview,
                    'description': strip_tags(str(data.get('description', '')))[:500],
                    'credit': str(data.get('photographer') or data.get('center') or 'NASA'),
                    'source_url': 'https://images.nasa.gov/details/' + quote(nasa_id, safe=''),
                })
            except (KeyError, IndexError, TypeError, AttributeError, StopIteration, ValueError):
                continue
        if items and not images:
            raise ValueError('No usable images')
    except (URLError, OSError, ValueError, KeyError, TypeError) as exc:
        raise NasaUnavailable from exc
    cache.set(key, images, 60 * 15)
    return images

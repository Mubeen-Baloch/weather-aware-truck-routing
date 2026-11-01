from django.test import SimpleTestCase

from routing.providers.cache import TtlCache


class TtlCacheTests(SimpleTestCase):
    def test_returns_a_copy_of_cached_data(self):
        cache = TtlCache(ttl_seconds=60)
        cache.set('route', {'routes': [1]})

        result = cache.get('route')
        result['routes'].append(2)

        self.assertEqual(cache.get('route'), {'routes': [1]})

    def test_zero_ttl_expires_immediately(self):
        cache = TtlCache(ttl_seconds=0)
        cache.set('route', {'routes': [1]})

        self.assertIsNone(cache.get('route'))

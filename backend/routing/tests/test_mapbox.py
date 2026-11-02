from django.test import SimpleTestCase

from routing.providers.cache import TtlCache
from routing.providers.errors import ProviderConfigurationError
from routing.providers.http import JsonHttpClient
from routing.providers.mapbox import MapboxClient


class RecordingHttp:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return {'type': 'FeatureCollection', 'features': []}


class MapboxClientTests(SimpleTestCase):
    def test_fixture_geocode_and_directions_are_deterministic(self):
        client = MapboxClient('fixture', 'standard', '', TtlCache(60), JsonHttpClient(1))

        geocode = client.geocode('Austin, TX')
        directions = client.directions((-97.7431, 30.2672), (-96.7970, 32.7767))

        self.assertEqual(geocode['features'][0]['properties']['name'], 'Austin')
        self.assertEqual(len(directions['routes']), 3)
        self.assertIn('annotation', directions['routes'][0]['legs'][0])

    def test_each_supported_scenario_selects_its_expected_route_fixture(self):
        expected_route_counts = {
            'standard': 3,
            'fewer_routes': 1,
            'missing_weather': 3,
            'unsafe_weather': 3,
            'tied_recommendations': 2,
            'forecast_gap': 3,
        }

        for scenario, expected_count in expected_route_counts.items():
            with self.subTest(scenario=scenario):
                client = MapboxClient('fixture', scenario, '', TtlCache(60), JsonHttpClient(1))
                self.assertEqual(len(client.directions((0.0, 0.0), (1.0, 1.0))['routes']), expected_count)

    def test_fixture_client_rejects_unsupported_scenario_during_initialization(self):
        with self.assertRaisesRegex(ProviderConfigurationError, "Unsupported ROUTING_FIXTURE_SCENARIO 'unknown'"):
            MapboxClient('fixture', 'unknown', '', TtlCache(60), JsonHttpClient(1))

    def test_live_mode_requires_a_token(self):
        client = MapboxClient('live', 'standard', '', TtlCache(60), JsonHttpClient(1))

        with self.assertRaises(ProviderConfigurationError):
            client.geocode('Austin, TX')

    def test_live_directions_requests_required_geometry_and_duration_metadata(self):
        http = RecordingHttp()
        client = MapboxClient('live', 'standard', 'test-token', TtlCache(60), http)

        client.directions((-97.7431, 30.2672), (-96.7970, 32.7767))

        url = http.urls[0]
        self.assertIn('alternatives=true', url)
        self.assertIn('steps=true', url)
        self.assertIn('geometries=geojson', url)
        self.assertIn('overview=full', url)
        self.assertIn('annotations=distance%2Cduration', url)

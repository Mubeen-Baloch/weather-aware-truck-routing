from django.test import SimpleTestCase

from routing.providers.cache import TtlCache
from routing.providers.errors import ProviderConfigurationError
from routing.providers.http import JsonHttpClient
from routing.providers.weather import OpenMeteoClient


class RecordingHttp:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return {'hourly': {}}


class OpenMeteoClientTests(SimpleTestCase):
    def test_each_supported_scenario_selects_its_expected_weather_fixture(self):
        expected_snowfall = {
            'standard': True,
            'fewer_routes': True,
            'missing_weather': False,
            'unsafe_weather': True,
            'tied_recommendations': True,
            'forecast_gap': True,
        }

        for scenario, has_snowfall in expected_snowfall.items():
            with self.subTest(scenario=scenario):
                client = OpenMeteoClient('fixture', scenario, TtlCache(60), JsonHttpClient(1))
                response = client.hourly_forecast([(30.2672, -97.7431)])

                self.assertEqual(response[0]['timezone'], 'UTC')
                self.assertEqual('snowfall' in response[0]['hourly'], has_snowfall)

    def test_standard_fixture_has_explicit_forty_nine_hour_coverage(self):
        client = OpenMeteoClient('fixture', 'standard', TtlCache(60), JsonHttpClient(1))

        response = client.hourly_forecast([(30.2672, -97.7431)])

        self.assertEqual(len(response[0]['hourly']['time']), 49)

    def test_forecast_gap_fixture_does_not_fabricate_the_missing_hour(self):
        client = OpenMeteoClient('fixture', 'forecast_gap', TtlCache(60), JsonHttpClient(1))

        response = client.hourly_forecast([(30.2672, -97.7431)])

        self.assertNotIn('2026-11-02T12:00', response[0]['hourly']['time'])

    def test_unsafe_weather_fixture_has_explicit_no_travel_winds(self):
        client = OpenMeteoClient('fixture', 'unsafe_weather', TtlCache(60), JsonHttpClient(1))

        response = client.hourly_forecast([(30.2672, -97.7431)])

        self.assertEqual(len(response[0]['hourly']['time']), 49)
        self.assertEqual(set(response[0]['hourly']['wind_speed_10m']), {60})

    def test_fixture_client_rejects_unsupported_scenario_during_initialization(self):
        with self.assertRaisesRegex(ProviderConfigurationError, "Unsupported ROUTING_FIXTURE_SCENARIO 'unknown'"):
            OpenMeteoClient('fixture', 'unknown', TtlCache(60), JsonHttpClient(1))

    def test_live_request_uses_utc_hourly_weather_and_declared_units(self):
        http = RecordingHttp()
        client = OpenMeteoClient('live', 'standard', TtlCache(60), http)

        client.hourly_forecast([(30.2672, -97.7431), (32.7767, -96.7970)])

        url = http.urls[0]
        self.assertIn('hourly=wind_speed_10m%2Crain%2Csnowfall', url)
        self.assertIn('wind_speed_unit=mph', url)
        self.assertIn('precipitation_unit=inch', url)
        self.assertIn('timezone=UTC', url)

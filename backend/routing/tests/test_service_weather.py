from datetime import datetime, timezone

from django.test import SimpleTestCase

from routing.services.weather import hourly_observation_at_eta


class HourlyWeatherMatchingTests(SimpleTestCase):
    def payload(self):
        return {
            'timezone': 'UTC',
            'hourly_units': {'wind_speed_10m': 'km/h', 'rain': 'mm', 'snowfall': 'cm'},
            'hourly': {
                'time': ['2026-11-01T12:00', '2026-11-01T13:00'],
                'wind_speed_10m': [40, 50],
                'rain': [2.54, 0],
                'snowfall': [2.54, 0],
            },
        }

    def test_matches_nearest_utc_hour_within_thirty_minutes_and_converts_units(self):
        observation = hourly_observation_at_eta(self.payload(), datetime(2026, 11, 1, 12, 29, tzinfo=timezone.utc))

        self.assertTrue(observation.available)
        self.assertEqual(observation.timestamp_utc, datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc))
        self.assertAlmostEqual(observation.wind_mph, 24.85484, places=4)
        self.assertAlmostEqual(observation.rain_inches_per_hour, 0.1, places=5)
        self.assertAlmostEqual(observation.snow_inches_per_hour, 1.0, places=4)

    def test_marks_weather_unavailable_when_nearest_hour_is_more_than_thirty_minutes_away(self):
        observation = hourly_observation_at_eta(self.payload(), datetime(2026, 11, 1, 13, 31, tzinfo=timezone.utc))

        self.assertFalse(observation.available)

    def test_marks_weather_unavailable_when_a_required_metric_is_missing(self):
        payload = self.payload()
        del payload['hourly']['snowfall']

        observation = hourly_observation_at_eta(payload, datetime(2026, 11, 1, 12, tzinfo=timezone.utc))

        self.assertFalse(observation.available)

    def test_marks_weather_unavailable_when_provider_data_is_not_explicitly_utc(self):
        payload = self.payload()
        payload['timezone'] = 'America/Chicago'

        observation = hourly_observation_at_eta(payload, datetime(2026, 11, 1, 12, tzinfo=timezone.utc))

        self.assertFalse(observation.available)

    def test_marks_weather_unavailable_for_non_finite_or_negative_weather_values(self):
        for value in (float('nan'), float('inf'), -0.1):
            with self.subTest(value=value):
                payload = self.payload()
                payload['hourly']['rain'][0] = value
                observation = hourly_observation_at_eta(payload, datetime(2026, 11, 1, 12, tzinfo=timezone.utc))
                self.assertFalse(observation.available)

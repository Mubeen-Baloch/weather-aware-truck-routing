from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient
from copy import deepcopy
from unittest.mock import patch

from routing.providers.mapbox import MapboxClient


REQUEST = {
    'origin': 'Austin, TX',
    'destination': 'Dallas, TX',
    'departureTime': '2026-11-01T12:00:00Z',
    'loadWeightLbs': 25_000,
    'checkpointIntervalMiles': 25,
}


class RouteAnalysisApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_returns_map_ready_fixture_analysis_with_recommendation_and_heatmap(self):
        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='standard'):
            response = self.client.post('/api/routes/analyze', REQUEST, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['routes']), 3)
        self.assertEqual(response.data['recommendation']['status'], 'recommended')
        first_route = response.data['routes'][0]
        self.assertEqual(first_route['geometry']['type'], 'LineString')
        self.assertGreater(first_route['distanceMeters'], 0)
        self.assertGreater(first_route['durationSeconds'], 0)
        self.assertTrue(first_route['checkpoints'][0]['weather']['available'])
        self.assertIn(first_route['checkpoints'][0]['risk']['level'], ('low', 'moderate', 'high', 'severe', 'no-travel'))
        self.assertEqual(len(first_route['heatmapFrames']), 49)
        self.assertEqual(first_route['heatmapFrames'][0]['offsetHours'], 0)
        self.assertEqual(first_route['heatmapFrames'][-1]['offsetHours'], 48)

    def test_returns_available_routes_without_fabricating_a_third_alternative(self):
        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='fewer_routes'):
            response = self.client.post('/api/routes/analyze', REQUEST, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['routes']), 1)

    def test_marks_missing_weather_unavailable_and_withholds_recommendation(self):
        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='missing_weather'):
            response = self.client.post('/api/routes/analyze', REQUEST, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['recommendation']['status'], 'weather-unavailable')
        self.assertFalse(response.data['routes'][0]['checkpoints'][0]['weather']['available'])
        self.assertFalse(response.data['routes'][0]['summary']['eligible'])

    def test_validates_request_fields(self):
        invalid_request = {**REQUEST, 'loadWeightLbs': -1, 'checkpointIntervalMiles': 15}

        response = self.client.post('/api/routes/analyze', invalid_request, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('loadWeightLbs', response.data)
        self.assertIn('checkpointIntervalMiles', response.data)

    def test_rejects_departure_time_without_timezone_offset(self):
        response = self.client.post(
            '/api/routes/analyze',
            {**REQUEST, 'departureTime': '2026-11-01T12:00:00'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('departureTime', response.data)

    def test_defaults_checkpoint_interval_to_twenty_five_miles(self):
        request = {key: value for key, value in REQUEST.items() if key != 'checkpointIntervalMiles'}
        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='standard'):
            response = self.client.post('/api/routes/analyze', request, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['checkpointIntervalMiles'], 25)

    def test_forecast_gap_marks_the_specific_heatmap_offset_unavailable(self):
        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='forecast_gap'):
            response = self.client.post('/api/routes/analyze', REQUEST, format='json')

        self.assertEqual(response.status_code, 200)
        frame = response.data['routes'][0]['heatmapFrames'][24]
        self.assertEqual(frame['offsetHours'], 24)
        self.assertFalse(frame['available'])
        self.assertFalse(frame['segments'][0]['risk']['available'])

    def test_heatmap_uses_following_segment_distance_and_excludes_destination(self):
        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='standard'):
            response = self.client.post('/api/routes/analyze', REQUEST, format='json')

        route = response.data['routes'][0]
        segments = route['heatmapFrames'][0]['segments']
        self.assertEqual(len(segments), len(route['checkpoints']) - 1)
        self.assertEqual(segments[0]['followingSegmentMeters'], route['checkpoints'][0]['followingSegmentMeters'])
        self.assertNotIn('distanceMeters', segments[0])

    def test_all_no_travel_routes_return_no_safe_route(self):
        class NoTravelWeatherClient:
            def hourly_forecast(self, coordinates):
                hourly = {
                    'time': [f'2026-11-{day:02d}T{hour:02d}:00' for day in (1, 2) for hour in range(24)] + ['2026-11-03T00:00'],
                    'wind_speed_10m': [60] * 49,
                    'rain': [0] * 49,
                    'snowfall': [0] * 49,
                }
                return [
                    {
                        'latitude': latitude,
                        'longitude': longitude,
                        'timezone': 'UTC',
                        'hourly_units': {'wind_speed_10m': 'mph', 'rain': 'inch', 'snowfall': 'inch'},
                        'hourly': hourly,
                    }
                    for latitude, longitude in coordinates
                ]

        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='standard'):
            with patch('routing.views.OpenMeteoClient.from_settings', return_value=NoTravelWeatherClient()):
                response = self.client.post('/api/routes/analyze', REQUEST, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['recommendation']['status'], 'no-safe-route')
        self.assertGreater(response.data['routes'][0]['summary']['riskMiles']['noTravel'], 0)

    def test_route_index_breaks_a_complete_risk_and_duration_tie(self):
        class TieMapboxClient:
            def __init__(self):
                self.client = MapboxClient.from_settings()

            def geocode(self, query):
                return self.client.geocode(query)

            def directions(self, origin, destination):
                response = self.client.directions(origin, destination)
                first_route = deepcopy(response['routes'][0])
                response['routes'] = [
                    first_route,
                    deepcopy(first_route),
                ]
                return response

        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='standard'):
            with patch('routing.views.MapboxClient.from_settings', return_value=TieMapboxClient()):
                response = self.client.post('/api/routes/analyze', REQUEST, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['routes']), 2)
        self.assertEqual(response.data['recommendation']['status'], 'recommended')
        first, second = response.data['routes'][:2]
        self.assertEqual(first['geometry'], second['geometry'])
        self.assertEqual(first['distanceMeters'], second['distanceMeters'])
        self.assertEqual(first['durationSeconds'], second['durationSeconds'])
        self.assertEqual(first['summary'], second['summary'])
        self.assertEqual(response.data['recommendation']['routeIndex'], 0)

from django.test import SimpleTestCase

from routing.services.risk import RiskLevel, classify_weather_risk, recommend_route, summarize_route
from routing.services.weather import WeatherObservation


def weather(wind: float, rain: float = 0, snow: float = 0) -> WeatherObservation:
    return WeatherObservation(True, None, wind, rain, snow)


class RiskRuleTests(SimpleTestCase):
    def test_ordinal_values_and_weather_boundaries(self):
        self.assertEqual([level.value for level in RiskLevel], [1, 2, 3, 4, 5])
        cases = (
            (weather(24.9), RiskLevel.LOW), (weather(25), RiskLevel.MODERATE),
            (weather(34), RiskLevel.MODERATE), (weather(35), RiskLevel.HIGH),
            (weather(44), RiskLevel.HIGH), (weather(45), RiskLevel.SEVERE),
            (weather(54), RiskLevel.SEVERE), (weather(55), RiskLevel.NO_TRAVEL),
            (weather(0, rain=0.09), RiskLevel.LOW), (weather(0, rain=0.10), RiskLevel.MODERATE),
            (weather(0, rain=0.25), RiskLevel.MODERATE), (weather(0, rain=0.26), RiskLevel.HIGH),
            (weather(0, rain=0.50), RiskLevel.HIGH), (weather(0, rain=0.51), RiskLevel.SEVERE),
            (weather(0, rain=1.00), RiskLevel.SEVERE), (weather(0, rain=1.01), RiskLevel.NO_TRAVEL),
            (weather(0, snow=0.49), RiskLevel.LOW), (weather(0, snow=0.5), RiskLevel.MODERATE),
            (weather(0, snow=1.0), RiskLevel.MODERATE), (weather(0, snow=1.01), RiskLevel.HIGH),
            (weather(0, snow=2.0), RiskLevel.HIGH), (weather(0, snow=2.01), RiskLevel.SEVERE),
            (weather(0, snow=3.0), RiskLevel.SEVERE), (weather(0, snow=3.01), RiskLevel.NO_TRAVEL),
        )
        for observation, expected in cases:
            with self.subTest(observation=observation, expected=expected):
                self.assertEqual(classify_weather_risk(observation, 1).level, expected)

    def test_load_overrides_and_missing_weather(self):
        self.assertEqual(classify_weather_risk(weather(45), 30_000).level, RiskLevel.SEVERE)
        self.assertEqual(classify_weather_risk(weather(45), 30_001).level, RiskLevel.NO_TRAVEL)
        self.assertEqual(classify_weather_risk(weather(35), 40_000).level, RiskLevel.HIGH)
        self.assertEqual(classify_weather_risk(weather(35), 40_001).level, RiskLevel.SEVERE)
        unavailable = WeatherObservation(False, None, None, None, None)
        self.assertFalse(classify_weather_risk(unavailable, 1).available)

    def test_invalid_weather_is_unavailable_and_invalid_load_is_rejected(self):
        for value in (float('nan'), float('inf'), -1):
            with self.subTest(weather_value=value):
                self.assertFalse(classify_weather_risk(weather(value), 1).available)
            with self.subTest(load_value=value):
                with self.assertRaisesRegex(ValueError, 'Load weight'):
                    classify_weather_risk(weather(10), value)


class RouteRecommendationTests(SimpleTestCase):
    def test_uses_checkpoint_following_segment_including_final_partial_and_destination_zero_distance(self):
        low = classify_weather_risk(weather(10), 1)
        high = classify_weather_risk(weather(36), 1)
        destination = classify_weather_risk(weather(55), 1)

        summary = summarize_route(0, [(low, 10 * 1609.344), (high, 2.5 * 1609.344), (destination, 0)], 100)

        self.assertAlmostEqual(summary.low_miles, 10)
        self.assertAlmostEqual(summary.high_miles, 2.5)
        self.assertEqual(summary.no_travel_miles, 0)
        self.assertAlmostEqual(summary.average_risk, (10 * 1 + 2.5 * 3) / 12.5)

    def test_excludes_unavailable_weather_from_recommendation(self):
        low = classify_weather_risk(weather(10), 1)
        unavailable = classify_weather_risk(WeatherObservation(False, None, None, None, None), 1)
        complete = summarize_route(0, [(low, 20 * 1609.344)], 200)
        incomplete = summarize_route(1, [(unavailable, 20 * 1609.344)], 1)

        self.assertEqual(recommend_route([complete, incomplete]), complete)
        self.assertIsNone(recommend_route([incomplete]))

    def test_recommendation_prioritizes_fewest_severe_miles(self):
        low = classify_weather_risk(weather(10), 1)
        severe = classify_weather_risk(weather(46), 1)
        fewer_severe = summarize_route(0, [(severe, 1 * 1609.344), (low, 9 * 1609.344)], 999)
        more_severe = summarize_route(1, [(severe, 2 * 1609.344), (low, 8 * 1609.344)], 1)

        self.assertEqual(recommend_route([more_severe, fewer_severe]), fewer_severe)

    def test_recommendation_prioritizes_fewest_high_miles_after_severe_miles(self):
        low = classify_weather_risk(weather(10), 1)
        high = classify_weather_risk(weather(36), 1)
        fewer_high = summarize_route(0, [(high, 1 * 1609.344), (low, 9 * 1609.344)], 999)
        more_high = summarize_route(1, [(high, 2 * 1609.344), (low, 8 * 1609.344)], 1)

        self.assertEqual(recommend_route([more_high, fewer_high]), fewer_high)

    def test_recommendation_prioritizes_lower_average_risk_after_severe_and_high_miles(self):
        low = classify_weather_risk(weather(10), 1)
        moderate = classify_weather_risk(weather(26), 1)
        lower_average = summarize_route(0, [(low, 9 * 1609.344), (moderate, 1 * 1609.344)], 999)
        higher_average = summarize_route(1, [(low, 8 * 1609.344), (moderate, 2 * 1609.344)], 1)

        self.assertEqual(recommend_route([higher_average, lower_average]), lower_average)

    def test_recommendation_prioritizes_shorter_duration_after_risk_ties(self):
        low = classify_weather_risk(weather(10), 1)
        slower = summarize_route(0, [(low, 10 * 1609.344)], 200)
        faster = summarize_route(1, [(low, 10 * 1609.344)], 100)

        self.assertEqual(recommend_route([slower, faster]), faster)

    def test_recommendation_uses_route_index_as_stable_final_tie_breaker(self):
        low = classify_weather_risk(weather(10), 1)
        first = summarize_route(3, [(low, 10 * 1609.344)], 100)
        second = summarize_route(1, [(low, 10 * 1609.344)], 100)

        self.assertEqual(recommend_route([first, second]), second)

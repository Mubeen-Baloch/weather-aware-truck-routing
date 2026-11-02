from django.test import SimpleTestCase

import json
from pathlib import Path

from routing.services.checkpoints import haversine_meters
from routing.services.eta import (
    DurationSegment,
    duration_distance_at_geometry_distance,
    eta_seconds_at_distance,
    route_duration_segments,
)


class EtaTests(SimpleTestCase):
    def test_interpolates_eta_inside_the_relevant_annotation_segment(self):
        segments = [DurationSegment(1000, 100), DurationSegment(2000, 400)]

        self.assertEqual(eta_seconds_at_distance(500, segments), 50)
        self.assertEqual(eta_seconds_at_distance(2000, segments), 300)

    def test_prefers_annotation_durations_and_falls_back_to_steps(self):
        annotated = {'legs': [{'annotation': {'distance': [1000], 'duration': [120]}, 'steps': [{'distance': 1000, 'duration': 999}]}]}
        step_only = {'legs': [{'steps': [{'distance': 1000, 'duration': 120}, {'distance': 500, 'duration': 30}]}]}

        self.assertEqual(route_duration_segments(annotated), [DurationSegment(1000, 120)])
        self.assertEqual(route_duration_segments(step_only), [DurationSegment(1000, 120), DurationSegment(500, 30)])

    def test_selects_annotations_or_step_fallback_independently_for_each_leg_in_order(self):
        route = {
            'legs': [
                {'annotation': {'distance': [1000], 'duration': [100]}},
                {'annotation': {'distance': [500], 'duration': []}, 'steps': [{'distance': 600, 'duration': 90}]},
                {'annotation': {'distance': [200], 'duration': [30]}},
            ],
        }

        self.assertEqual(
            route_duration_segments(route),
            [DurationSegment(1000, 100), DurationSegment(600, 90), DurationSegment(200, 30)],
        )

    def test_rejects_distance_materially_beyond_duration_segments_but_tolerates_rounding(self):
        segments = [DurationSegment(1000, 100)]

        self.assertEqual(eta_seconds_at_distance(1000.005, segments), 100)
        with self.assertRaisesRegex(ValueError, 'exceeds available route duration segments'):
            eta_seconds_at_distance(1000.02, segments)

    def test_maps_fixture_geometry_progress_to_the_complete_mapbox_duration_domain(self):
        fixture_path = Path(__file__).resolve().parent.parent / 'fixtures' / 'mapbox' / 'directions_standard.json'
        fixture = json.loads(fixture_path.read_text(encoding='utf-8'))

        for route in fixture['routes']:
            with self.subTest(route_distance=route['distance']):
                coordinates = [tuple(coordinate) for coordinate in route['geometry']['coordinates']]
                geometry_total = sum(haversine_meters(start, end) for start, end in zip(coordinates, coordinates[1:]))
                duration_segments = route_duration_segments(route)
                duration_total = sum(segment.distance_meters for segment in duration_segments)

                self.assertGreater(abs(geometry_total - duration_total), 0.01)
                self.assertEqual(
                    duration_distance_at_geometry_distance(
                        geometry_total,
                        geometry_total,
                        route['distance'],
                        duration_segments,
                    ),
                    duration_total,
                )
                halfway = duration_distance_at_geometry_distance(
                    geometry_total / 2,
                    geometry_total,
                    route['distance'],
                    duration_segments,
                )
                self.assertAlmostEqual(halfway, duration_total / 2)
                self.assertLessEqual(eta_seconds_at_distance(halfway, duration_segments), route['duration'])

    def test_rejects_materially_incomplete_duration_data_before_mapping_geometry_progress(self):
        incomplete_segments = [DurationSegment(800, 100)]

        with self.assertRaisesRegex(ValueError, 'do not cover the reported route distance'):
            duration_distance_at_geometry_distance(500, 1_000, 1_000, incomplete_segments)

    def test_accepts_small_route_distance_coverage_rounding_but_rejects_larger_gap(self):
        accepted_segments = [DurationSegment(315_354.300, 100)]

        self.assertAlmostEqual(
            duration_distance_at_geometry_distance(
                157_677.1875,
                315_354.375,
                315_354.375,
                accepted_segments,
            ),
            157_677.15,
        )

        rejected_segments = [DurationSegment(1_000.051, 100)]
        with self.assertRaisesRegex(ValueError, 'do not cover the reported route distance'):
            duration_distance_at_geometry_distance(500, 1_000, 1_000, rejected_segments)

    def test_rejects_materially_incomplete_duration_data_for_a_long_route(self):
        incomplete_segments = [DurationSegment(999_999, 100)]

        with self.assertRaisesRegex(ValueError, 'do not cover the reported route distance'):
            duration_distance_at_geometry_distance(500_000, 1_000_000, 1_000_000, incomplete_segments)

    def test_maps_small_geometry_representation_difference_without_relaxing_duration_coverage(self):
        segments = [DurationSegment(1_000, 100)]

        duration_distance = duration_distance_at_geometry_distance(500.1, 1_000.2, 1_000, segments)

        self.assertAlmostEqual(duration_distance, 500)
        self.assertEqual(eta_seconds_at_distance(duration_distance, segments), 50)

    def test_rejects_non_finite_geometry_checkpoint_distance(self):
        segments = [DurationSegment(1_000, 100)]

        for distance in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(distance=distance):
                with self.assertRaisesRegex(ValueError, 'Geometry and route distances'):
                    duration_distance_at_geometry_distance(distance, 1_000, 1_000, segments)

    def test_rejects_zero_or_negative_geometry_total_distance(self):
        segments = [DurationSegment(1_000, 100)]

        for total_distance in (0, -1):
            with self.subTest(total_distance=total_distance):
                with self.assertRaisesRegex(ValueError, 'Geometry and route distances'):
                    duration_distance_at_geometry_distance(500, total_distance, 1_000, segments)

    def test_rejects_zero_or_negative_reported_route_distance(self):
        segments = [DurationSegment(1_000, 100)]

        for route_distance in (0, -1):
            with self.subTest(route_distance=route_distance):
                with self.assertRaisesRegex(ValueError, 'Geometry and route distances'):
                    duration_distance_at_geometry_distance(500, 1_000, route_distance, segments)

    def test_rejects_checkpoint_materially_beyond_geometry_distance(self):
        segments = [DurationSegment(1_000, 100)]

        with self.assertRaisesRegex(ValueError, 'exceeds route geometry distance'):
            duration_distance_at_geometry_distance(1_000.02, 1_000, 1_000, segments)

    def test_rejects_negative_or_non_finite_duration_segment_distances(self):
        invalid_distances = (-1, float('nan'), float('inf'), float('-inf'))

        for invalid_distance in invalid_distances:
            with self.subTest(invalid_distance=invalid_distance):
                segments = [DurationSegment(invalid_distance, 100)]
                with self.assertRaisesRegex(ValueError, 'segment distances'):
                    duration_distance_at_geometry_distance(500, 1_000, 1_000, segments)

    def test_destination_maps_to_complete_duration_distance_and_final_eta(self):
        segments = [DurationSegment(400, 40), DurationSegment(600, 90)]

        mapped_destination = duration_distance_at_geometry_distance(1_200, 1_200, 1_000, segments)

        self.assertEqual(mapped_destination, 1_000)
        self.assertEqual(eta_seconds_at_distance(mapped_destination, segments), 130)

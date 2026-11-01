from django.test import SimpleTestCase

from routing.services.checkpoints import checkpoint_coordinates


class CheckpointGeometryTests(SimpleTestCase):
    def test_places_checkpoints_along_curved_geometry_and_assigns_following_segments(self):
        geometry = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]

        checkpoints = checkpoint_coordinates(geometry, 50)

        self.assertEqual(len(checkpoints), 4)
        self.assertAlmostEqual(checkpoints[0].distance_meters / 1609.344, 0, places=4)
        self.assertAlmostEqual(checkpoints[1].distance_meters / 1609.344, 50, places=4)
        self.assertAlmostEqual(checkpoints[2].distance_meters / 1609.344, 100, places=4)
        self.assertGreater(checkpoints[1].coordinate[1], 0.70)
        self.assertAlmostEqual(checkpoints[0].following_segment_meters / 1609.344, 50, places=4)
        self.assertAlmostEqual(checkpoints[1].following_segment_meters / 1609.344, 50, places=4)
        self.assertGreater(checkpoints[2].following_segment_meters, 0)
        self.assertEqual(checkpoints[-1].following_segment_meters, 0)

    def test_rejects_unsupported_checkpoint_interval(self):
        with self.assertRaisesRegex(ValueError, '10, 25, or 50'):
            checkpoint_coordinates([(0.0, 0.0), (1.0, 1.0)], 20)

    def test_rejects_invalid_or_degenerate_geometry(self):
        invalid_geometries = (
            [(0.0, 0.0)],
            [(181.0, 0.0), (0.0, 0.0)],
            [(0.0, 91.0), (0.0, 0.0)],
            [(float('nan'), 0.0), (0.0, 0.0)],
            [(0.0, 0.0), (0.0, 0.0)],
        )
        for geometry in invalid_geometries:
            with self.subTest(geometry=geometry):
                with self.assertRaises(ValueError):
                    checkpoint_coordinates(geometry, 10)

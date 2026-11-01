from dataclasses import dataclass
from math import asin, cos, isfinite, radians, sin, sqrt


EARTH_RADIUS_METERS = 6_371_008.8
MIN_ROUTE_DISTANCE_METERS = 0.01


@dataclass(frozen=True)
class Checkpoint:
    coordinate: tuple[float, float]
    distance_meters: float
    following_segment_meters: float


def haversine_meters(start: tuple[float, float], end: tuple[float, float]) -> float:
    """Return the ground distance between Mapbox-style (longitude, latitude) coordinates."""
    longitude_a, latitude_a = map(radians, start)
    longitude_b, latitude_b = map(radians, end)
    delta_longitude = longitude_b - longitude_a
    delta_latitude = latitude_b - latitude_a
    value = sin(delta_latitude / 2) ** 2 + cos(latitude_a) * cos(latitude_b) * sin(delta_longitude / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(value))


def _interpolate(start: tuple[float, float], end: tuple[float, float], fraction: float) -> tuple[float, float]:
    return (
        start[0] + (end[0] - start[0]) * fraction,
        start[1] + (end[1] - start[1]) * fraction,
    )


def geometry_distance_meters(coordinates: list[tuple[float, float]]) -> float:
    return sum(haversine_meters(start, end) for start, end in zip(coordinates, coordinates[1:]))


def checkpoint_coordinates(
    coordinates: list[tuple[float, float]],
    interval_miles: int,
    distance_domain_meters: float | None = None,
) -> list[Checkpoint]:
    """Place checkpoints on geometry while reporting distances in the selected domain."""
    if interval_miles not in (10, 25, 50):
        raise ValueError('Checkpoint interval must be 10, 25, or 50 miles.')
    if len(coordinates) < 2:
        raise ValueError('Route geometry must contain at least two coordinates.')
    for coordinate in coordinates:
        if not isinstance(coordinate, (tuple, list)) or len(coordinate) != 2:
            raise ValueError('Route coordinates must contain longitude and latitude.')
        longitude, latitude = coordinate
        if (
            isinstance(longitude, bool)
            or isinstance(latitude, bool)
            or not isinstance(longitude, (int, float))
            or not isinstance(latitude, (int, float))
            or not isfinite(longitude)
            or not isfinite(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            raise ValueError('Route coordinates must be finite valid longitude/latitude values.')

    interval_meters = interval_miles * 1609.344
    geometry_segments = [(coordinates[index], coordinates[index + 1]) for index in range(len(coordinates) - 1)]
    segment_lengths = [haversine_meters(start, end) for start, end in geometry_segments]
    geometry_total_meters = sum(segment_lengths)
    if geometry_total_meters <= MIN_ROUTE_DISTANCE_METERS:
        raise ValueError('Route geometry must have a non-zero distance.')
    if distance_domain_meters is None:
        distance_domain_meters = geometry_total_meters
    if not isfinite(distance_domain_meters) or distance_domain_meters <= MIN_ROUTE_DISTANCE_METERS:
        raise ValueError('Checkpoint distance domain must be a finite non-zero distance.')

    targets = [0.0]
    next_distance = interval_meters
    while next_distance < distance_domain_meters:
        targets.append(next_distance)
        next_distance += interval_meters
    targets.append(distance_domain_meters)

    checkpoints: list[Checkpoint] = []
    segment_index = 0
    segment_start_distance = 0.0
    for target in targets:
        geometry_target = target / distance_domain_meters * geometry_total_meters
        while segment_index < len(segment_lengths) - 1 and geometry_target > segment_start_distance + segment_lengths[segment_index]:
            segment_start_distance += segment_lengths[segment_index]
            segment_index += 1
        start, end = geometry_segments[segment_index]
        segment_length = segment_lengths[segment_index]
        fraction = 0.0 if segment_length == 0 else (geometry_target - segment_start_distance) / segment_length
        checkpoints.append(Checkpoint(_interpolate(start, end, min(1.0, max(0.0, fraction))), target, 0.0))

    return [
        Checkpoint(checkpoint.coordinate, checkpoint.distance_meters, checkpoints[index + 1].distance_meters - checkpoint.distance_meters)
        if index < len(checkpoints) - 1
        else Checkpoint(checkpoint.coordinate, checkpoint.distance_meters, 0.0)
        for index, checkpoint in enumerate(checkpoints)
    ]

from datetime import timedelta, timezone
from typing import Any

from routing.providers.errors import ProviderError
from routing.services.checkpoints import Checkpoint, checkpoint_coordinates, geometry_distance_meters
from routing.services.eta import (
    duration_distance_at_geometry_distance,
    eta_seconds_at_distance,
    route_duration_segments,
)
from routing.services.risk import CheckpointRisk, RiskLevel, classify_weather_risk, recommend_route, summarize_route
from routing.services.weather import WeatherObservation, hourly_observation_at_eta


def analyze_routes(
    origin_query: str,
    destination_query: str,
    departure_time,
    load_weight_lbs: float,
    checkpoint_interval_miles: int,
    mapbox_client,
    weather_client,
) -> dict[str, Any]:
    origin = _location_from_geocode(mapbox_client.geocode(origin_query), 'Origin')
    destination = _location_from_geocode(mapbox_client.geocode(destination_query), 'Destination')
    directions = mapbox_client.directions(origin['coordinate'], destination['coordinate'])
    source_routes = directions.get('routes', [])[:3]
    if not source_routes:
        raise ProviderError('Mapbox returned no routes for the selected locations.')

    departure_utc = departure_time.astimezone(timezone.utc)
    analyzed_routes = [
        _analyze_route(
            route_index,
            route,
            departure_utc,
            load_weight_lbs,
            checkpoint_interval_miles,
            weather_client,
        )
        for route_index, route in enumerate(source_routes)
    ]
    summaries = [route['_summary'] for route in analyzed_routes]
    has_unavailable_weather = any(summary.unavailable_miles > 0 for summary in summaries)
    recommendation = None if has_unavailable_weather else recommend_route(summaries)
    for route in analyzed_routes:
        route.pop('_summary')

    return {
        'origin': origin,
        'destination': destination,
        'departureTimeUtc': _timestamp(departure_utc),
        'loadWeightLbs': load_weight_lbs,
        'checkpointIntervalMiles': checkpoint_interval_miles,
        'routes': analyzed_routes,
        'recommendation': (
            {
                'status': 'recommended',
                'routeIndex': recommendation.route_index,
                'criteria': ['fewest-severe-miles', 'fewest-high-miles', 'lowest-average-risk', 'shortest-duration'],
            }
            if recommendation
            else {
                'status': 'weather-unavailable' if has_unavailable_weather else 'no-safe-route',
                'routeIndex': None,
                'criteria': [],
            }
        ),
    }


def _location_from_geocode(response: dict[str, Any], label: str) -> dict[str, Any]:
    features = response.get('features', [])
    if not features:
        raise ProviderError(f'{label} could not be resolved.')
    feature = features[0]
    coordinates = feature.get('geometry', {}).get('coordinates', [])
    if not isinstance(coordinates, list) or len(coordinates) != 2:
        raise ProviderError(f'{label} did not include usable coordinates.')
    properties = feature.get('properties', {})
    name = properties.get('full_address') or properties.get('name') or label
    place = properties.get('place_formatted')
    return {
        'label': f'{name}, {place}' if place else name,
        'coordinate': (float(coordinates[0]), float(coordinates[1])),
    }


def _analyze_route(
    route_index: int,
    route: dict[str, Any],
    departure_utc,
    load_weight_lbs: float,
    checkpoint_interval_miles: int,
    weather_client,
) -> dict[str, Any]:
    geometry = route.get('geometry', {})
    coordinates = [tuple(coordinate) for coordinate in geometry.get('coordinates', [])]
    route_distance_meters = float(route['distance'])
    checkpoints = checkpoint_coordinates(coordinates, checkpoint_interval_miles, route_distance_meters)
    duration_segments = route_duration_segments(route)
    route_duration_seconds = float(route['duration'])
    geometry_total_meters = geometry_distance_meters(coordinates)
    weather_payloads = _weather_payloads(weather_client.hourly_forecast([(coordinate[1], coordinate[0]) for coordinate in (checkpoint.coordinate for checkpoint in checkpoints)]), len(checkpoints))

    checkpoint_records: list[dict[str, Any]] = []
    segment_risks: list[tuple[CheckpointRisk, float]] = []
    for checkpoint, payload in zip(checkpoints, weather_payloads):
        eta_seconds = eta_seconds_at_distance(
            duration_distance_at_geometry_distance(
                checkpoint.distance_meters / route_distance_meters * geometry_total_meters,
                geometry_total_meters,
                route_distance_meters,
                duration_segments,
            ),
            duration_segments,
        )
        eta_utc = departure_utc + timedelta(seconds=eta_seconds)
        observation = hourly_observation_at_eta(payload, eta_utc)
        risk = classify_weather_risk(observation, load_weight_lbs)
        checkpoint_records.append(_checkpoint_record(checkpoint, eta_utc, observation, risk))
        segment_risks.append((risk, checkpoint.following_segment_meters))

    summary = summarize_route(route_index, segment_risks, route_duration_seconds)
    return {
        'index': route_index,
        'geometry': geometry,
        'distanceMeters': route_distance_meters,
        'durationSeconds': route_duration_seconds,
        'checkpoints': checkpoint_records,
        'summary': _summary_record(summary),
        'heatmapFrames': _heatmap_frames(checkpoints, weather_payloads, departure_utc, load_weight_lbs),
        '_summary': summary,
    }


def _weather_payloads(response: dict[str, Any] | list[dict[str, Any]], expected_count: int) -> list[dict[str, Any]]:
    payloads = response if isinstance(response, list) else [response]
    if len(payloads) != expected_count:
        raise ProviderError('Weather provider did not return data for every checkpoint.')
    return payloads


def _checkpoint_record(checkpoint: Checkpoint, eta_utc, observation: WeatherObservation, risk: CheckpointRisk) -> dict[str, Any]:
    return {
        'coordinate': list(checkpoint.coordinate),
        'distanceMeters': checkpoint.distance_meters,
        'followingSegmentMeters': checkpoint.following_segment_meters,
        'etaUtc': _timestamp(eta_utc),
        'weather': {
            'available': observation.available,
            'timestampUtc': _timestamp(observation.timestamp_utc) if observation.timestamp_utc else None,
            'windMph': observation.wind_mph,
            'rainInchesPerHour': observation.rain_inches_per_hour,
            'snowInchesPerHour': observation.snow_inches_per_hour,
        },
        'risk': _risk_record(risk),
    }


def _heatmap_frames(checkpoints, weather_payloads, departure_utc, load_weight_lbs: float) -> list[dict[str, Any]]:
    frames = []
    for offset in range(49):
        frame_time = departure_utc + timedelta(hours=offset)
        segments = []
        for checkpoint, payload in zip(checkpoints[:-1], weather_payloads[:-1]):
            risk = classify_weather_risk(hourly_observation_at_eta(payload, frame_time), load_weight_lbs)
            segments.append({'followingSegmentMeters': checkpoint.following_segment_meters, 'risk': _risk_record(risk)})
        frames.append({'offsetHours': offset, 'timeUtc': _timestamp(frame_time), 'available': all(segment['risk']['available'] for segment in segments), 'segments': segments})
    return frames


def _summary_record(summary) -> dict[str, Any]:
    return {
        'eligible': summary.eligible,
        'riskMiles': {
            'low': summary.low_miles,
            'moderate': summary.moderate_miles,
            'high': summary.high_miles,
            'severe': summary.severe_miles,
            'noTravel': summary.no_travel_miles,
            'unavailable': summary.unavailable_miles,
        },
        'averageRisk': summary.average_risk,
    }


def _risk_record(risk: CheckpointRisk) -> dict[str, Any]:
    return {'available': risk.available, 'level': risk.level.name.lower().replace('_', '-') if risk.level else None, 'ordinal': risk.level.value if risk.level else None}


def _timestamp(value) -> str:
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

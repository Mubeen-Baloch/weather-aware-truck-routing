from copy import deepcopy
from typing import Any
from urllib.parse import urlencode

from django.conf import settings

from .cache import TtlCache
from .errors import ProviderConfigurationError, ProviderError
from .fixtures import load_fixture, validate_fixture_scenario
from .http import JsonHttpClient


class OpenMeteoClient:
    HOURLY_VARIABLES = 'wind_speed_10m,rain,snowfall'

    def __init__(self, mode: str, fixture_scenario: str, cache: TtlCache, http: JsonHttpClient) -> None:
        validate_fixture_scenario(mode, fixture_scenario)
        self.mode = mode
        self.fixture_scenario = fixture_scenario
        self.cache = cache
        self.http = http

    @classmethod
    def from_settings(cls) -> 'OpenMeteoClient':
        return cls(
            settings.ROUTING_DATA_MODE,
            settings.ROUTING_FIXTURE_SCENARIO,
            TtlCache(settings.PROVIDER_CACHE_TTL_SECONDS),
            JsonHttpClient(settings.PROVIDER_REQUEST_TIMEOUT_SECONDS),
        )

    def hourly_forecast(self, coordinates: list[tuple[float, float]]) -> dict[str, Any] | list[dict[str, Any]]:
        if not coordinates:
            raise ProviderError('At least one weather coordinate is required.')
        cache_key = f'weather:hourly:{coordinates}:{self.fixture_scenario}'
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if self.mode == 'fixture':
            fixture_name = {
                'missing_weather': 'hourly_incomplete.json',
                'unsafe_weather': 'hourly_unsafe_weather.json',
                'forecast_gap': 'hourly_forecast_gap.json',
            }.get(self.fixture_scenario, 'hourly_complete_49h.json')
            response = self._fixture_responses(coordinates, load_fixture('weather', fixture_name))
        elif self.mode == 'live':
            params = urlencode({
                'latitude': ','.join(str(latitude) for latitude, _longitude in coordinates),
                'longitude': ','.join(str(longitude) for _latitude, longitude in coordinates),
                'hourly': self.HOURLY_VARIABLES,
                'wind_speed_unit': 'mph',
                'precipitation_unit': 'inch',
                'timezone': 'UTC',
                'forecast_days': 16,
            })
            response = self.http.get(f'https://api.open-meteo.com/v1/forecast?{params}')
        else:
            raise ProviderConfigurationError('ROUTING_DATA_MODE must be fixture or live.')

        self.cache.set(cache_key, response)
        return response

    @staticmethod
    def _fixture_responses(
        coordinates: list[tuple[float, float]],
        fixture: dict[str, Any] | list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        templates = fixture if isinstance(fixture, list) else [fixture]
        responses: list[dict[str, Any]] = []
        for index, (latitude, longitude) in enumerate(coordinates):
            response = deepcopy(templates[index % len(templates)])
            response['latitude'] = latitude
            response['longitude'] = longitude
            responses.append(response)
        return responses

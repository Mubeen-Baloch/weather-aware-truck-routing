from typing import Any
from urllib.parse import urlencode

from django.conf import settings

from .cache import TtlCache
from .errors import ProviderConfigurationError, ProviderError
from .fixtures import load_fixture, validate_fixture_scenario
from .http import JsonHttpClient


class MapboxClient:
    def __init__(self, mode: str, fixture_scenario: str, access_token: str, cache: TtlCache, http: JsonHttpClient) -> None:
        validate_fixture_scenario(mode, fixture_scenario)
        self.mode = mode
        self.fixture_scenario = fixture_scenario
        self.access_token = access_token
        self.cache = cache
        self.http = http

    @classmethod
    def from_settings(cls) -> 'MapboxClient':
        return cls(
            settings.ROUTING_DATA_MODE,
            settings.ROUTING_FIXTURE_SCENARIO,
            settings.MAPBOX_ACCESS_TOKEN,
            TtlCache(settings.PROVIDER_CACHE_TTL_SECONDS),
            JsonHttpClient(settings.PROVIDER_REQUEST_TIMEOUT_SECONDS),
        )

    def geocode(self, query: str) -> dict[str, Any]:
        normalized = query.strip().casefold()
        if not normalized:
            raise ProviderError('A location query is required.')
        cache_key = f'mapbox:geocode:{normalized}'
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if self.mode == 'fixture':
            payload = load_fixture('mapbox', 'geocoding.json')
            response = payload['queries'].get(normalized, {'type': 'FeatureCollection', 'features': []})
        elif self.mode == 'live':
            self._require_token()
            params = urlencode({'q': query, 'limit': 1, 'access_token': self.access_token})
            response = self.http.get(f'https://api.mapbox.com/search/geocode/v6/forward?{params}')
        else:
            raise ProviderConfigurationError('ROUTING_DATA_MODE must be fixture or live.')

        if not isinstance(response, dict):
            raise ProviderError('Mapbox geocoding returned an unexpected response.')
        self.cache.set(cache_key, response)
        return response

    def directions(self, origin: tuple[float, float], destination: tuple[float, float]) -> dict[str, Any]:
        cache_key = f'mapbox:directions:{origin}:{destination}:{self.fixture_scenario}'
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if self.mode == 'fixture':
            fixture_name = 'directions_fewer_routes.json' if self.fixture_scenario == 'fewer_routes' else 'directions_standard.json'
            response = load_fixture('mapbox', fixture_name)
        elif self.mode == 'live':
            self._require_token()
            coordinates = f'{origin[0]},{origin[1]};{destination[0]},{destination[1]}'
            params = urlencode({
                'alternatives': 'true',
                'steps': 'true',
                'geometries': 'geojson',
                'overview': 'full',
                'annotations': 'distance,duration',
                'access_token': self.access_token,
            })
            response = self.http.get(f'https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates}?{params}')
        else:
            raise ProviderConfigurationError('ROUTING_DATA_MODE must be fixture or live.')

        if not isinstance(response, dict):
            raise ProviderError('Mapbox directions returned an unexpected response.')
        self.cache.set(cache_key, response)
        return response

    def _require_token(self) -> None:
        if not self.access_token:
            raise ProviderConfigurationError('MAPBOX_ACCESS_TOKEN is required in live mode.')

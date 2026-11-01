import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import ProviderError


class JsonHttpClient:
    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds

    def get(self, url: str) -> dict[str, Any] | list[dict[str, Any]]:
        request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'weather-aware-truck-routing/0.1'})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError('Provider request failed.') from exc

        if not isinstance(payload, (dict, list)):
            raise ProviderError('Provider returned an unexpected response.')
        return payload

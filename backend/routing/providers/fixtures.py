import json
from pathlib import Path
from typing import Any

from .errors import ProviderConfigurationError, ProviderError


FIXTURES_DIR = Path(__file__).resolve().parent.parent / 'fixtures'
SUPPORTED_FIXTURE_SCENARIOS = ('standard', 'fewer_routes', 'missing_weather')


def validate_fixture_scenario(mode: str, scenario: str) -> None:
    if mode == 'fixture' and scenario not in SUPPORTED_FIXTURE_SCENARIOS:
        supported = ', '.join(SUPPORTED_FIXTURE_SCENARIOS)
        raise ProviderConfigurationError(
            f"Unsupported ROUTING_FIXTURE_SCENARIO '{scenario}'. Supported scenarios: {supported}."
        )


def load_fixture(provider: str, filename: str) -> dict[str, Any] | list[dict[str, Any]]:
    path = FIXTURES_DIR / provider / filename
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderError(f'Fixture data is unavailable: {provider}/{filename}') from exc

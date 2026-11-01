from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings

from .providers.errors import ProviderConfigurationError
from .providers.fixtures import validate_fixture_scenario


@api_view(['GET'])
@permission_classes([AllowAny])
def health(_request):
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([AllowAny])
def provider_status(_request):
    """Expose the configured source without leaking credentials."""
    try:
        validate_fixture_scenario(settings.ROUTING_DATA_MODE, settings.ROUTING_FIXTURE_SCENARIO)
    except ProviderConfigurationError as exc:
        return Response({'detail': str(exc)}, status=400)

    return Response({
        'mode': settings.ROUTING_DATA_MODE,
        'fixtureScenario': settings.ROUTING_FIXTURE_SCENARIO if settings.ROUTING_DATA_MODE == 'fixture' else None,
        'providers': {'mapbox': settings.ROUTING_DATA_MODE, 'weather': settings.ROUTING_DATA_MODE},
    })

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient


class ProviderStatusTests(SimpleTestCase):
    def test_browsable_api_templates_render_for_health_and_provider_status(self):
        client = APIClient()

        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='standard'):
            health = client.get('/api/health', HTTP_ACCEPT='text/html')
            provider_status = client.get('/api/providers/status', HTTP_ACCEPT='text/html')

        self.assertEqual(health.status_code, 200)
        self.assertEqual(provider_status.status_code, 200)
        self.assertContains(health, 'GET')
        self.assertContains(provider_status, 'fixture')

    def test_fixture_status_does_not_expose_secrets(self):
        client = APIClient()

        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='standard'):
            response = client.get('/api/providers/status')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['mode'], 'fixture')
        self.assertEqual(response.data['fixtureScenario'], 'standard')

    def test_fixture_status_rejects_an_unsupported_scenario(self):
        client = APIClient()

        with override_settings(ROUTING_DATA_MODE='fixture', ROUTING_FIXTURE_SCENARIO='unknown'):
            response = client.get('/api/providers/status')

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported ROUTING_FIXTURE_SCENARIO 'unknown'", response.data['detail'])

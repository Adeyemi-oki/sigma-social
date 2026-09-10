from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    """Phase 10: /health/ must be public, lightweight, and safe."""

    def test_health_check_returns_200(self):
        resp = self.client.get(reverse("health"))
        self.assertEqual(resp.status_code, 200)

    def test_health_check_does_not_require_authentication(self):
        # No login() call here on purpose -- this must work logged out.
        resp = self.client.get(reverse("health"))
        self.assertEqual(resp.status_code, 200)

    def test_health_check_does_not_expose_secrets(self):
        resp = self.client.get(reverse("health"))
        body = resp.content.decode().lower()
        self.assertNotIn("secret", body)
        self.assertNotIn("password", body)
        self.assertNotIn("database", body)

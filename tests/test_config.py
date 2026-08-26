"""Production-safety tests for application configuration."""

import os
import unittest
from unittest.mock import patch

from backend.core.config import DEVELOPMENT_JWT_SECRET, get_settings, reset_settings_cache


class SettingsTests(unittest.TestCase):
    def tearDown(self):
        reset_settings_cache()

    def test_development_uses_explicit_local_origins(self):
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=True):
            reset_settings_cache()
            settings = get_settings()
            self.assertNotIn("*", settings.cors_allowed_origins)
            self.assertIn("http://localhost:3000", settings.cors_allowed_origins)

    def test_production_rejects_development_defaults(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "JWT_SECRET_KEY": DEVELOPMENT_JWT_SECRET,
                "CORS_ALLOWED_ORIGINS": "*",
            },
            clear=True,
        ):
            reset_settings_cache()
            with self.assertRaisesRegex(RuntimeError, "Invalid application configuration"):
                get_settings()

    def test_production_accepts_complete_configuration(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "JWT_SECRET_KEY": "a-unique-production-secret-with-sufficient-entropy",
                "GOOGLE_CLIENT_IDS": "web-client.apps.googleusercontent.com",
                "CORS_ALLOWED_ORIGINS": "https://app.example.com",
            },
            clear=True,
        ):
            reset_settings_cache()
            settings = get_settings()
            self.assertTrue(settings.is_production_like)
            self.assertEqual(settings.cors_allowed_origins, ("https://app.example.com",))


if __name__ == "__main__":
    unittest.main()

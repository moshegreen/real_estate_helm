from pathlib import Path
from unittest import TestCase

from real_estate_helm.settings import Settings


class SettingsTests(TestCase):
    def test_settings_load_from_environment_mapping(self) -> None:
        settings = Settings.from_env(
            {
                "REAL_ESTATE_HELM_DATA_DIR": "/tmp/reh",
                "REAL_ESTATE_HELM_AUTH_SECRET": "0123456789abcdef",
                "POSTGRES_DSN": "postgresql://example",
                "REDIS_URL": "redis://example",
                "S3_ENDPOINT": "http://minio:9000",
                "S3_BUCKET": "real-estate-helm",
                "S3_ACCESS_KEY": "minio",
                "S3_SECRET_KEY": "secret",
                "S3_REGION": "us-west-2",
                "GEOCODER_API_KEY": "geo",
                "LLM_API_KEY": "llm",
            }
        )

        self.assertEqual(settings.data_dir, Path("/tmp/reh"))
        self.assertTrue(settings.storage.configured)
        self.assertEqual(settings.storage.bucket, "real-estate-helm")
        self.assertEqual(settings.storage.region, "us-west-2")
        self.assertEqual(settings.providers.configured_providers, ("geocoder", "llm"))
        self.assertEqual(settings.validate(), [])

    def test_settings_validate_partial_storage_and_short_secret(self) -> None:
        settings = Settings.from_env(
            {
                "REAL_ESTATE_HELM_AUTH_SECRET": "short",
                "S3_ENDPOINT": "http://minio:9000",
                "S3_BUCKET": "real-estate-helm",
            }
        )

        self.assertIn("REAL_ESTATE_HELM_AUTH_SECRET must be at least 16 bytes", settings.validate())
        self.assertIn(
            "S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, and S3_SECRET_KEY must be set together",
            settings.validate(),
        )

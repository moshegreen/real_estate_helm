import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class DeploymentPackagingTests(TestCase):
    def test_docker_compose_declares_architecture_services(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text()

        self.assertIn("api:", compose)
        self.assertIn("postgis/postgis", compose)
        self.assertIn("minio/minio", compose)
        self.assertIn("redis:7-alpine", compose)
        self.assertIn("./schema/postgres.sql", compose)

    def test_env_example_lists_required_integration_settings(self) -> None:
        env = (ROOT / ".env.example").read_text()

        for key in [
            "POSTGRES_DSN",
            "S3_ENDPOINT",
            "REDIS_URL",
            "GEOCODER_API_KEY",
            "OCR_API_KEY",
            "LLM_API_KEY",
            "REAL_ESTATE_HELM_AUTH_SECRET",
        ]:
            self.assertIn(key, env)

    def test_tauri_windows_config_targets_desktop_bundle(self) -> None:
        config = json.loads((ROOT / "apps" / "windows" / "src-tauri" / "tauri.conf.json").read_text())

        self.assertEqual(config["productName"], "Real Estate Helm")
        self.assertIn("msi", config["bundle"]["targets"])
        self.assertIn("nsis", config["bundle"]["targets"])

    def test_android_manifest_declares_internet_permission_and_launcher(self) -> None:
        manifest = (ROOT / "apps" / "android" / "android" / "app" / "src" / "main" / "AndroidManifest.xml").read_text()
        gradle = (ROOT / "apps" / "android" / "android" / "app" / "build.gradle").read_text()

        self.assertIn("android.permission.INTERNET", manifest)
        self.assertIn("Real Estate Helm", manifest)
        self.assertIn("android.intent.action.MAIN", manifest)
        self.assertIn("signingConfigs", gradle)
        self.assertIn("ANDROID_KEYSTORE_PASSWORD", gradle)

    def test_ci_workflow_runs_python_suite_and_compile_check(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

        self.assertIn("python3 -m unittest discover -s tests", workflow)
        self.assertIn("python3 -m compileall src tests", workflow)
        self.assertIn("docker build", workflow)

    def test_release_workflow_contains_desktop_mobile_and_container_jobs(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()

        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("docker-build", workflow)
        self.assertIn("windows-desktop", workflow)
        self.assertIn("android-mobile", workflow)
        self.assertIn("TAURI_PRIVATE_KEY", workflow)
        self.assertIn("ANDROID_KEYSTORE_BASE64", workflow)
        self.assertIn("actions/upload-artifact", workflow)
        self.assertIn("npm run bundle", workflow)
        self.assertIn("npm run build:android", workflow)

    def test_release_documentation_lists_signing_secrets(self) -> None:
        release_doc = (ROOT / "docs" / "release.md").read_text()

        self.assertIn("TAURI_PRIVATE_KEY", release_doc)
        self.assertIn("ANDROID_KEYSTORE_BASE64", release_doc)

import json
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class ClientScaffoldTests(TestCase):
    def test_windows_scaffold_uses_react_typescript_and_api_views(self) -> None:
        package = json.loads((ROOT / "apps" / "windows" / "package.json").read_text())
        app_source = (ROOT / "apps" / "windows" / "src" / "App.tsx").read_text()

        self.assertIn("react", package["dependencies"])
        self.assertIn("typescript", package["dependencies"])
        self.assertIn("/api", app_source)
        self.assertIn("Deal Pipeline", app_source)
        self.assertIn("Monitoring Center", app_source)

    def test_android_scaffold_is_companion_focused(self) -> None:
        package = json.loads((ROOT / "apps" / "android" / "package.json").read_text())
        app_source = (ROOT / "apps" / "android" / "src" / "App.tsx").read_text()

        self.assertIn("react-native", package["dependencies"])
        self.assertIn("Alerts", app_source)
        self.assertIn("watchlist review", app_source)
        self.assertIn("Document Preview", app_source)
        self.assertIn("geo:", app_source)
        self.assertIn("Linking.openURL", app_source)
        self.assertIn("10.0.2.2:8765/api", app_source)

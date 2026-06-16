from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm.api import ApiRouter
from real_estate_helm.repository import JsonDealRepository


class ServerSurfaceTests(TestCase):
    def test_static_assets_exist_for_dashboard(self) -> None:
        root = Path(__file__).resolve().parents[1] / "web"

        self.assertTrue((root / "index.html").exists())
        self.assertTrue((root / "styles.css").exists())
        self.assertTrue((root / "app.js").exists())

    def test_dashboard_contains_plan_aligned_workflow_panels(self) -> None:
        root = Path(__file__).resolve().parents[1] / "web"
        html = (root / "index.html").read_text()
        script = (root / "app.js").read_text()

        self.assertIn("Document Review", html)
        self.assertIn("Financial Model", html)
        self.assertIn("Map and Market Context", html)
        self.assertIn("renderDocuments", script)
        self.assertIn("renderFinancialModel", script)
        self.assertIn("renderMarketContext", script)
        self.assertIn("pipeline-column", script)
        self.assertIn("investment_committee", script)
        self.assertIn("Top risk", script)
        self.assertIn("scenarioOutput", script)
        self.assertIn("/portfolio/summary", script)
        self.assertIn("Portfolio value", script)
        self.assertIn("google.com/maps/search", script)
        self.assertIn("location_context", script)
        self.assertIn("rent_roll", script)
        self.assertIn("rentRollRow", script)

    def test_api_router_contract_used_by_server_routes(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))
            response = router.handle("POST", "/deals", {"name": "Server Deal"})

            self.assertEqual(response.status, HTTPStatus.CREATED)
            self.assertEqual(response.body["identity"]["name"], "Server Deal")

import re
from pathlib import Path
from unittest import TestCase


class PostgresSchemaTests(TestCase):
    def test_plan_core_tables_are_present(self) -> None:
        schema = (Path(__file__).resolve().parents[1] / "schema" / "postgres.sql").read_text()
        tables = set(re.findall(r"CREATE TABLE ([a-z_]+)", schema))

        required = {
            "deals",
            "deal_status_history",
            "assets",
            "addresses",
            "parcels",
            "documents",
            "document_pages",
            "extracted_facts",
            "fact_sources",
            "spreadsheets",
            "spreadsheet_cells",
            "assumptions",
            "scenarios",
            "scenario_outputs",
            "cash_flows_projected",
            "cash_flows_actual",
            "debt_terms",
            "tenants",
            "leases",
            "rent_rolls",
            "capex_items",
            "development_budgets",
            "development_milestones",
            "market_comps",
            "property_records",
            "location_context",
            "permit_events",
            "web_sources",
            "news_events",
            "imagery_snapshots",
            "alerts",
            "tasks",
            "obligations",
            "comments",
            "approval_requests",
            "notifications",
            "investment_decisions",
            "audit_log",
        }

        self.assertEqual(required - tables, set())

    def test_postgis_and_geospatial_indexes_are_present(self) -> None:
        schema = (Path(__file__).resolve().parents[1] / "schema" / "postgres.sql").read_text()

        self.assertIn("CREATE EXTENSION IF NOT EXISTS postgis", schema)
        self.assertIn("geography(Point, 4326)", schema)
        self.assertIn("USING gist(location)", schema)

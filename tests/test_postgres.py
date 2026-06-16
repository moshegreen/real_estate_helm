from decimal import Decimal
from unittest import TestCase

from real_estate_helm import (
    Alert,
    AlertSeverity,
    Assumption,
    Deal,
    DealIdentity,
    DocumentReference,
    DocumentType,
    RentRollEntry,
    Scenario,
    ScenarioType,
    SourceKind,
    UploadedDocument,
)
from real_estate_helm.postgres import PostgresDealSqlMapper


class PostgresDealSqlMapperTests(TestCase):
    def test_upsert_deal_emits_statements_for_core_tables(self) -> None:
        deal = Deal(DealIdentity("SQL Deal", asset_type="office"))
        deal.documents.append(UploadedDocument("om.pdf", DocumentType.PDF, "s3://bucket/om.pdf", "analyst"))
        deal.rent_roll.append(
            RentRollEntry(
                "2027-01-31",
                "101",
                tenant_name="Tenant",
                monthly_rent=Decimal("2000"),
                market_rent=Decimal("2200"),
                source=DocumentReference(SourceKind.SPREADSHEET, "rent-roll.xlsx", sheet="Rent Roll", cell="B2"),
            )
        )
        deal.assumptions.append(Assumption("purchase_price", Decimal("10000000"), "Reviewed OM"))
        scenario = Scenario("Base", ScenarioType.ANALYST_BASE_CASE)
        scenario.outputs["irr"] = Decimal("0.14")
        deal.scenarios.append(scenario)
        deal.alerts.append(Alert("DSCR watch", AlertSeverity.HIGH, "debt", "model", "Near covenant"))

        statements = PostgresDealSqlMapper().upsert_deal(deal)
        sql = "\n".join(statement.sql for statement in statements)

        self.assertIn("INSERT INTO deals", sql)
        self.assertIn("INSERT INTO documents", sql)
        self.assertIn("INSERT INTO assumptions", sql)
        self.assertIn("INSERT INTO scenarios", sql)
        self.assertIn("INSERT INTO scenario_outputs", sql)
        self.assertIn("INSERT INTO rent_rolls", sql)
        self.assertIn("INSERT INTO alerts", sql)
        self.assertEqual(statements[0].params[1], "SQL Deal")

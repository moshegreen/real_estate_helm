from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import Address, CashFlowType, DealIdentity, DocumentReference, DocumentType, SourceKind, SpreadsheetCell
from real_estate_helm.domain import Deal
from real_estate_helm.intake import IntakeService
from real_estate_helm.repository import JsonDealRepository


class IntakeServiceTests(TestCase):
    def test_asset_document_spreadsheet_and_cash_flow_intake_persist(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("River Apartments"))
            repository.save(deal)
            service = IntakeService(repository)

            service.add_asset(
                deal.id,
                "River Apartments",
                address=Address("1 River Road", city="Nashville"),
                asset_type="multifamily",
                unit_count=120,
            )
            deal = service.add_document(
                deal.id,
                name="underwriting.xlsx",
                document_type=DocumentType.EXCEL,
                storage_uri="local://underwriting.xlsx",
                uploaded_by="analyst",
            )
            document_id = deal.documents[0].id
            service.add_document_page(
                deal.id,
                document_id=document_id,
                page_number=1,
                text_content="NOI table",
                extracted_tables=[{"name": "NOI", "rows": [["Year 1", "100"]]}],
            )
            service.add_spreadsheet_model(
                deal.id,
                name="Sponsor Model",
                document_id=document_id,
                cells=[SpreadsheetCell("Summary", "B4", Decimal("0.145"), mapped_field="irr")],
            )
            service.add_cash_flow(
                deal.id,
                period="2027-01",
                amount=Decimal("100000"),
                cash_flow_type=CashFlowType.PROJECTED,
                category="noi",
            )
            service.add_rent_roll_entry(
                deal.id,
                as_of_date="2027-01-31",
                unit="101",
                tenant_name="Anchor Tenant",
                monthly_rent=Decimal("2000"),
                market_rent=Decimal("2200"),
                source=DocumentReference(SourceKind.SPREADSHEET, "rent-roll.xlsx", sheet="Rent Roll", cell="B2"),
            )

            restored = repository.get(deal.id)
            self.assertEqual(restored.assets[0].unit_count, 120)
            self.assertEqual(restored.documents[0].document_type, DocumentType.EXCEL)
            self.assertEqual(restored.document_pages[0].extracted_tables[0]["name"], "NOI")
            self.assertEqual(restored.spreadsheets[0].cells[0].mapped_field, "irr")
            self.assertEqual(restored.projected_cash_flows[0].amount, Decimal("100000"))
            self.assertEqual(restored.rent_roll[0].tenant_name, "Anchor Tenant")
            self.assertEqual(restored.rent_roll[0].source.cell, "B2")

    def test_document_page_rejects_unknown_document_id(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Document Page Deal"))
            repository.save(deal)

            with self.assertRaises(ValueError):
                IntakeService(repository).add_document_page(deal.id, document_id="missing", page_number=1)

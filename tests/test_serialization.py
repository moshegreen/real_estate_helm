from decimal import Decimal
from unittest import TestCase

from real_estate_helm import (
    Address,
    Alert,
    AlertSeverity,
    Asset,
    CashFlowRecord,
    CashFlowType,
    Coordinates,
    Assumption,
    CapexItem,
    Deal,
    DealIdentity,
    DealStatus,
    DebtTerms,
    DevelopmentBudget,
    DevelopmentMilestone,
    DocumentPage,
    DocumentType,
    DocumentReference,
    ExtractedFact,
    FactReviewStatus,
    ImagerySnapshot,
    InvestmentDecision,
    Lease,
    LocationContextItem,
    LocationContextType,
    MarketComp,
    MilestoneStatus,
    NewsClassification,
    NewsEvent,
    Obligation,
    ObligationType,
    PermitEvent,
    PropertyRecord,
    RentRollEntry,
    Scenario,
    ScenarioType,
    SourceKind,
    SpreadsheetCell,
    SpreadsheetModel,
    Task,
    Tenant,
    UploadedDocument,
    WebSource,
)
from real_estate_helm.serialization import deal_from_dict, deal_to_dict


class SerializationTests(TestCase):
    def test_deal_round_trip_preserves_reviewed_facts_and_decisions(self) -> None:
        deal = Deal(DealIdentity(name="Pine Logistics", sponsor="SponsorCo"))
        fact = ExtractedFact(
            field_name="purchase_price",
            value=Decimal("21000000"),
            confidence=0.9,
            source=DocumentReference(SourceKind.DOCUMENT, "om.pdf", page=4),
        )
        deal.add_extracted_fact(fact)
        deal.review_fact(
            fact.id,
            FactReviewStatus.EDITED,
            reviewer="analyst",
            corrected_value=Decimal("20500000"),
            note="Corrected from rent roll appendix",
        )
        scenario = Scenario("Base case", ScenarioType.ANALYST_BASE_CASE)
        scenario.add_assumption(Assumption("exit_cap_rate", Decimal("0.0575"), "Local comps"))
        scenario.set_output("irr", Decimal("0.142"))
        deal.add_scenario(scenario)
        deal.change_status(DealStatus.UNDERWRITING, "analyst", "Ready for model review")

        restored = deal_from_dict(deal_to_dict(deal))

        self.assertEqual(restored.id, deal.id)
        self.assertEqual(restored.identity.name, "Pine Logistics")
        self.assertEqual(restored.extracted_facts[0].value, Decimal("20500000"))
        self.assertEqual(restored.extracted_facts[0].status, FactReviewStatus.EDITED)
        self.assertEqual(restored.scenarios[0].outputs["irr"], Decimal("0.142"))
        self.assertEqual(restored.decision_history[0].to_status, DealStatus.UNDERWRITING)

    def test_full_deal_state_round_trip_preserves_plan_records(self) -> None:
        deal = Deal(DealIdentity(name="Cedar Mixed Use", address="1 Cedar Road"))
        asset = Asset(
            name="Cedar Mixed Use",
            address=Address("1 Cedar Road", city="Austin", state="TX", country="US"),
            coordinates=Coordinates(30.2672, -97.7431),
            asset_type="mixed_use",
            unit_count=42,
        )
        document = UploadedDocument("offering-memorandum.pdf", DocumentType.PDF, "s3://bucket/om.pdf", "analyst")
        spreadsheet = SpreadsheetModel(
            "sponsor model",
            document.id,
            cells=[SpreadsheetCell("Summary", "B12", Decimal("0.16"), formula="=IRR(C10:C20)", mapped_field="irr")],
        )

        deal.assets.append(asset)
        deal.documents.append(document)
        deal.document_pages.append(
            DocumentPage(document.id, 1, text_content="Executive summary", extracted_tables=[{"name": "pricing"}])
        )
        deal.spreadsheets.append(spreadsheet)
        deal.projected_cash_flows.append(
            CashFlowRecord("2027-01", Decimal("120000"), CashFlowType.PROJECTED, "noi")
        )
        deal.actual_cash_flows.append(CashFlowRecord("2027-01", Decimal("110000"), CashFlowType.ACTUAL, "noi"))
        deal.debt_terms.append(DebtTerms(lender="Bank", debt_amount=Decimal("7000000"), covenant_dscr=Decimal("1.2")))
        tenant = Tenant("Anchor Tenant")
        deal.tenants.append(tenant)
        deal.leases.append(Lease(tenant.id, unit="A", annual_rent=Decimal("250000")))
        deal.rent_roll.append(
            RentRollEntry(
                "2027-01-31",
                "A",
                tenant_name="Anchor Tenant",
                monthly_rent=Decimal("20000"),
                market_rent=Decimal("22000"),
                source=DocumentReference(SourceKind.SPREADSHEET, "rent-roll.xlsx", sheet="Rent Roll", cell="B2"),
            )
        )
        deal.capex_items.append(CapexItem("Roof", Decimal("500000"), Decimal("525000"), "maintenance"))
        deal.development_budgets.append(
            DevelopmentBudget(
                "Phase 1",
                hard_costs=Decimal("5000000"),
                soft_costs=Decimal("1200000"),
                contingency=Decimal("400000"),
                land_cost=Decimal("3000000"),
                capex_items=[CapexItem("Site work", Decimal("800000"))],
            )
        )
        deal.development_milestones.append(
            DevelopmentMilestone("Permit approval", "2027-03-31", MilestoneStatus.ON_TRACK)
        )
        deal.market_comps.append(MarketComp("Nearby sale", "sale", Decimal("22500000"), distance_miles=0.8))
        deal.property_records.append(PropertyRecord("assessor", parcel_id="123-abc", zoning="TOD"))
        deal.location_context.append(
            LocationContextItem(
                LocationContextType.TRANSIT,
                "Central Station",
                0.4,
                "maps",
                coordinates=Coordinates(30.27, -97.74),
            )
        )
        deal.permit_events.append(PermitEvent("P-1", "building", "issued", issued_date="2027-01-02"))
        deal.web_sources.append(WebSource("Planning board agenda", "https://example.test/agenda", "permit"))
        deal.news_events.append(
            NewsEvent(
                "Transit extension approved",
                "https://example.test/news",
                NewsClassification.MATERIAL_POSITIVE,
            )
        )
        deal.imagery_snapshots.append(ImagerySnapshot("2027-01-15", "s3://bucket/snapshot.jpg", "sentinel"))
        deal.alerts.append(Alert("NOI below budget", AlertSeverity.HIGH, "cash_flow", "monthly import", "NOI is 8% low"))
        deal.tasks.append(Task("Review lender covenant", owner="analyst", due_date="2027-02-01"))
        deal.obligations.append(
            Obligation("Capital call funding", "2027-02-15", ObligationType.CAPITAL_CALL, amount=Decimal("250000"))
        )
        deal.investment_decisions.append(InvestmentDecision("watchlist", "principal", "Revisit after permits"))
        deal.change_status(DealStatus.WATCHLIST, "principal", "Need permit clarity")

        restored = deal_from_dict(deal_to_dict(deal))

        self.assertEqual(restored.assets[0].coordinates.latitude, 30.2672)
        self.assertEqual(restored.documents[0].document_type, DocumentType.PDF)
        self.assertEqual(restored.document_pages[0].text_content, "Executive summary")
        self.assertEqual(restored.spreadsheets[0].cells[0].value, Decimal("0.16"))
        self.assertEqual(restored.projected_cash_flows[0].cash_flow_type, CashFlowType.PROJECTED)
        self.assertEqual(restored.actual_cash_flows[0].amount, Decimal("110000"))
        self.assertEqual(restored.debt_terms[0].covenant_dscr, Decimal("1.2"))
        self.assertEqual(restored.leases[0].annual_rent, Decimal("250000"))
        self.assertEqual(restored.rent_roll[0].market_rent, Decimal("22000"))
        self.assertEqual(restored.rent_roll[0].source.sheet, "Rent Roll")
        self.assertEqual(restored.development_milestones[0].status, MilestoneStatus.ON_TRACK)
        self.assertEqual(restored.property_records[0].parcel_id, "123-abc")
        self.assertEqual(restored.location_context[0].item_type, LocationContextType.TRANSIT)
        self.assertEqual(restored.location_context[0].coordinates.longitude, -97.74)
        self.assertEqual(restored.permit_events[0].status, "issued")
        self.assertEqual(restored.news_events[0].classification, NewsClassification.MATERIAL_POSITIVE)
        self.assertEqual(restored.alerts[0].severity, AlertSeverity.HIGH)
        self.assertEqual(restored.obligations[0].obligation_type, ObligationType.CAPITAL_CALL)
        self.assertEqual(restored.obligations[0].amount, Decimal("250000"))
        self.assertEqual(restored.audit_log[0].action, "change_status")

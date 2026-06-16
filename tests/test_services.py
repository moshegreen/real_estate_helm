from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import Assumption, DealStatus, DocumentReference, FactReviewStatus, Scenario, ScenarioType, SourceKind
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.services import DealService


class DealServiceTests(TestCase):
    def test_intake_review_and_rejection_are_persisted(self) -> None:
        with TemporaryDirectory() as directory:
            service = DealService(JsonDealRepository(directory))
            deal = service.create_deal(
                "Harbor Apartments",
                address="10 Harbor Way",
                asset_type="multifamily",
                broker="Metro Capital",
                owner="analyst",
            )

            deal = service.add_extracted_fact(
                deal.id,
                field_name="current_noi",
                value=Decimal("1180000"),
                confidence=0.87,
                source=DocumentReference(SourceKind.DOCUMENT, "broker-om.pdf", page=9),
            )
            fact_id = deal.extracted_facts[0].id

            deal = service.review_fact(
                deal.id,
                fact_id,
                FactReviewStatus.ASSUMPTION,
                "analyst",
                corrected_value=Decimal("1165000"),
                note="Adjusted for non-recurring income",
                promote_to_assumption=True,
            )
            deal = service.change_status(deal.id, DealStatus.UNDERWRITING, "analyst", "Ready for model")
            deal = service.reject_deal(deal.id, "principal", "Downside DSCR is too weak")

            self.assertEqual(deal.status, DealStatus.REJECTED)
            self.assertEqual(deal.assumptions[0].value, Decimal("1165000"))
            self.assertEqual(len(deal.decision_history), 2)

            restored = service.repository.get(deal.id)
            self.assertEqual(restored.identity.address, "10 Harbor Way")
            self.assertEqual(restored.extracted_facts[0].reviewer, "analyst")
            self.assertEqual(restored.decision_history[-1].reason, "Downside DSCR is too weak")

    def test_update_scenario_assumption_records_audit_and_output_changes(self) -> None:
        with TemporaryDirectory() as directory:
            service = DealService(JsonDealRepository(directory))
            deal = service.create_deal("Scenario Audit Deal")
            scenario = Scenario("IC Case", ScenarioType.INVESTMENT_COMMITTEE_CASE)
            scenario.assumptions.append(Assumption("rent_growth", Decimal("0.03"), "Original IC case"))
            scenario.outputs["irr"] = Decimal("0.14")
            deal.scenarios.append(scenario)
            service.repository.save(deal)

            updated = service.update_scenario_assumption(
                deal.id,
                scenario.id,
                name="rent_growth",
                value=Decimal("0.025"),
                actor="analyst",
                rationale="Revised after rent roll update",
                revised_outputs={"irr": Decimal("0.12")},
            )

            self.assertEqual(updated.scenarios[0].assumptions[0].value, Decimal("0.025"))
            self.assertEqual(updated.scenarios[0].outputs["irr"], Decimal("0.12"))
            self.assertEqual(updated.audit_log[-1].action, "update_scenario_assumption")
            self.assertIn("IC-approved scenario modified", updated.audit_log[-1].reason)
            self.assertIn("outputs changed: irr: 0.14 -> 0.12", updated.audit_log[-1].reason)

    def test_request_fact_reextraction_creates_task_and_audit_entry(self) -> None:
        with TemporaryDirectory() as directory:
            service = DealService(JsonDealRepository(directory))
            deal = service.create_deal("Reextract Deal")
            deal = service.add_extracted_fact(
                deal.id,
                field_name="purchase_price",
                value=Decimal("21000000"),
                confidence=0.42,
                source=DocumentReference(SourceKind.DOCUMENT, "om.pdf", page=4),
            )
            fact_id = deal.extracted_facts[0].id

            updated = service.request_fact_reextraction(
                deal.id,
                fact_id,
                reviewer="analyst",
                note="Confidence too low; rerun with table extraction.",
                owner="document-ai",
                due_date="2027-01-15",
            )

            self.assertEqual(updated.extracted_facts[0].status, FactReviewStatus.NEEDS_REEXTRACTION)
            self.assertEqual(updated.extracted_facts[0].review_note, "Confidence too low; rerun with table extraction.")
            self.assertEqual(updated.tasks[0].title, "Re-extract purchase_price from om.pdf")
            self.assertEqual(updated.tasks[0].owner, "document-ai")
            self.assertEqual(updated.tasks[0].due_date, "2027-01-15")
            self.assertEqual(updated.audit_log[-1].action, "request_fact_reextraction")

            restored = service.repository.get(deal.id)
            self.assertEqual(restored.extracted_facts[0].status, FactReviewStatus.NEEDS_REEXTRACTION)
            self.assertEqual(restored.tasks[0].owner, "document-ai")

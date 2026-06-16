from decimal import Decimal
from unittest import TestCase

from real_estate_helm import (
    Assumption,
    Deal,
    DealIdentity,
    DealStatus,
    DocumentReference,
    ExtractedFact,
    FactReviewStatus,
    Scenario,
    ScenarioType,
    SourceKind,
)


class DealDomainTests(TestCase):
    def test_rejected_deal_preserves_decision_history(self) -> None:
        deal = Deal(DealIdentity(name="Main Street Apartments", asset_type="multifamily"))

        deal.change_status(DealStatus.SCREENING, actor="analyst", reason="Initial review started")
        deal.reject(actor="portfolio manager", reason="Sponsor NOI bridge is not supportable")

        self.assertEqual(deal.status, DealStatus.REJECTED)
        self.assertEqual(len(deal.decision_history), 2)
        self.assertEqual(deal.decision_history[-1].from_status, DealStatus.SCREENING)
        self.assertEqual(deal.decision_history[-1].to_status, DealStatus.REJECTED)
        self.assertEqual(deal.decision_history[-1].reason, "Sponsor NOI bridge is not supportable")

    def test_reviewed_extracted_fact_can_be_promoted_to_assumption(self) -> None:
        deal = Deal(DealIdentity(name="Industrial Flex Portfolio"))
        fact = ExtractedFact(
            field_name="stabilized_noi",
            value=Decimal("1450000"),
            confidence=0.82,
            source=DocumentReference(
                source_kind=SourceKind.DOCUMENT,
                name="offering-memorandum.pdf",
                page=12,
                context="Sponsor stabilized NOI summary",
            ),
        )
        deal.add_extracted_fact(fact)

        assumption = deal.review_fact(
            fact.id,
            FactReviewStatus.ASSUMPTION,
            reviewer="analyst",
            note="Used as base-case underwriting assumption after review",
            promote_to_assumption=True,
        )

        self.assertIsNotNone(assumption)
        self.assertEqual(assumption.source_fact_id, fact.id)
        self.assertEqual(deal.assumptions[0].name, "stabilized_noi")
        self.assertEqual(fact.status, FactReviewStatus.ASSUMPTION)

    def test_scenarios_preserve_independent_assumptions_and_outputs(self) -> None:
        base_case = Scenario("Analyst base case", ScenarioType.ANALYST_BASE_CASE)
        downside = Scenario("Downside case", ScenarioType.DOWNSIDE_CASE)

        base_case.add_assumption(Assumption("exit_cap_rate", Decimal("0.055"), "Market comps"))
        downside.add_assumption(Assumption("exit_cap_rate", Decimal("0.065"), "Stress case"))
        base_case.set_output("irr", Decimal("0.148"))
        downside.set_output("irr", Decimal("0.091"))

        self.assertEqual(base_case.assumptions[0].value, Decimal("0.055"))
        self.assertEqual(downside.assumptions[0].value, Decimal("0.065"))
        self.assertEqual(base_case.outputs["irr"], Decimal("0.148"))
        self.assertEqual(downside.outputs["irr"], Decimal("0.091"))

    def test_invalid_confidence_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ExtractedFact(
                field_name="purchase_price",
                value=Decimal("20000000"),
                confidence=1.1,
                source=DocumentReference(SourceKind.DOCUMENT, "memo.pdf"),
            )

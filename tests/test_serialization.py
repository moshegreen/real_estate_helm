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

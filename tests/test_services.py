from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import DealStatus, DocumentReference, FactReviewStatus, SourceKind
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

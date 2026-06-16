from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import Assumption, Deal, DealIdentity, FactReviewStatus
from real_estate_helm.extraction import (
    compare_spreadsheet_to_canonical,
    ExtractionService,
    interpret_spreadsheet_cells,
    proposals_from_spreadsheet,
)
from real_estate_helm.repository import JsonDealRepository


class ExtractionTests(TestCase):
    def test_spreadsheet_interpretation_creates_sourced_fact_proposals(self) -> None:
        model = interpret_spreadsheet_cells(
            "Sponsor Model",
            "doc-1",
            [
                {"sheet": "Summary", "cell": "B4", "value": Decimal("0.145"), "formula": "=IRR(C10:C20)", "mapped_field": "irr"},
                {"sheet": "Summary", "cell": "B8", "value": "#REF!", "formula": "#REF!", "mapped_field": "exit_value"},
            ],
        )

        proposals = proposals_from_spreadsheet(model)

        self.assertEqual(len(proposals), 2)
        self.assertEqual(proposals[0].source.sheet, "Summary")
        self.assertEqual(model.cells[1].warning, "broken_formula")
        self.assertEqual(proposals[1].confidence, 0.5)

    def test_spreadsheet_comparison_flags_sponsor_vs_canonical_deltas(self) -> None:
        model = interpret_spreadsheet_cells(
            "Sponsor Model",
            "doc-1",
            [
                {"sheet": "Summary", "cell": "B4", "value": Decimal("0.145"), "formula": "=IRR(C10:C20)", "mapped_field": "irr"},
                {"sheet": "Summary", "cell": "B8", "value": Decimal("100"), "formula": "=ExitValue", "mapped_field": "exit_value"},
            ],
        )

        rows = compare_spreadsheet_to_canonical(
            model,
            [Assumption("irr", Decimal("0.140"), "Internal base case")],
        )

        self.assertEqual(rows[0].mapped_field, "irr")
        self.assertEqual(rows[0].delta, Decimal("0.005"))
        self.assertEqual(rows[0].delta_percent, Decimal("0.03571428571428571428571428571"))
        self.assertEqual(rows[1].warning, "missing_canonical_value")

    def test_extraction_service_requires_review_before_assumption_mapping(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Extraction Deal"))
            repository.save(deal)
            service = ExtractionService(repository)
            model = interpret_spreadsheet_cells(
                "Sponsor Model",
                "doc-1",
                [{"sheet": "Summary", "cell": "B4", "value": Decimal("0.145"), "formula": "=IRR(C10:C20)", "mapped_field": "irr"}],
            )

            self.assertEqual(service.add_proposals(deal.id, proposals_from_spreadsheet(model)), 1)
            self.assertEqual(service.map_reviewed_facts_to_assumptions(deal.id, reviewer="analyst", rationale="Reviewed"), 0)

            deal = repository.get(deal.id)
            fact_id = deal.extracted_facts[0].id
            deal.review_fact(fact_id, FactReviewStatus.ACCEPTED, "analyst")
            repository.save(deal)

            self.assertEqual(service.map_reviewed_facts_to_assumptions(deal.id, reviewer="analyst", rationale="Reviewed"), 1)
            restored = repository.get(deal.id)
            self.assertEqual(restored.assumptions[0].name, "irr")

from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import ObligationType
from real_estate_helm.obligation_import import ObligationImportService
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.services import DealService


class ObligationImportServiceTests(TestCase):
    def test_import_csv_adds_deadlines_expirations_and_capital_calls(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = DealService(repository).create_deal("Obligation Import Deal")

            result = ObligationImportService(repository).import_csv(
                deal.id,
                "\n".join(
                    [
                        "title,due_date,obligation_type,amount,source,owner",
                        "File zoning appeal,2027-01-10,legal_deadline,,legal tracker,counsel",
                        "Insurance certificate,2027-01-20,document_expiration,,data room,analyst",
                        "Fund draw 3,2027-02-01,capital_call,250000,fund notice,principal",
                        "Broken row,,capital_call,100,fund notice,principal",
                    ]
                ),
            )

            restored = repository.get(deal.id)
            self.assertEqual(result.imported_rows, 3)
            self.assertEqual(len(result.skipped_rows), 1)
            self.assertEqual(restored.obligations[0].obligation_type, ObligationType.LEGAL_DEADLINE)
            self.assertEqual(restored.obligations[2].amount, Decimal("250000"))
            self.assertEqual(restored.obligations[2].owner, "principal")

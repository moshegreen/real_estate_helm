from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import CashFlowType
from real_estate_helm.cash_flow_import import CashFlowImportService
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.services import DealService


class CashFlowImportServiceTests(TestCase):
    def test_import_csv_adds_actual_and_projected_cash_flows(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = DealService(repository).create_deal("Cash Flow Import Deal")

            result = CashFlowImportService(repository).import_csv(
                deal.id,
                "\n".join(
                    [
                        "period,category,amount,cash_flow_type",
                        "2027-01,noi,90000,actual",
                        "2027-01,noi,100000,projected",
                        "2027-02,noi,not-a-number,actual",
                    ]
                ),
                default_type=CashFlowType.ACTUAL,
            )

            restored = repository.get(deal.id)
            self.assertEqual(result.imported_rows, 2)
            self.assertEqual(len(result.skipped_rows), 1)
            self.assertEqual(restored.actual_cash_flows[0].amount, Decimal("90000"))
            self.assertEqual(restored.projected_cash_flows[0].amount, Decimal("100000"))

    def test_import_csv_uses_default_type_when_row_type_is_missing(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = DealService(repository).create_deal("Default Type Deal")

            result = CashFlowImportService(repository).import_csv(
                deal.id,
                "period,category,amount\n2027-01,insurance,25000\n",
            )

            restored = repository.get(deal.id)
            self.assertEqual(result.imported_rows, 1)
            self.assertEqual(restored.actual_cash_flows[0].category, "insurance")

    def test_import_bank_statement_csv_maps_transactions_to_actual_cash_flows(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = DealService(repository).create_deal("Bank Statement Deal")

            result = CashFlowImportService(repository).import_bank_statement_csv(
                deal.id,
                "\n".join(
                    [
                        "date,description,deposit,withdrawal",
                        "2027-01-05,Rent collection,142000,",
                        "2027-01-06,Repair invoice,,25000",
                        ",Missing date,100,",
                    ]
                ),
            )

            restored = repository.get(deal.id)
            self.assertEqual(result.imported_rows, 2)
            self.assertEqual(len(result.skipped_rows), 1)
            self.assertEqual(restored.actual_cash_flows[0].period, "2027-01")
            self.assertEqual(restored.actual_cash_flows[0].amount, Decimal("142000"))
            self.assertEqual(restored.actual_cash_flows[1].amount, Decimal("-25000"))

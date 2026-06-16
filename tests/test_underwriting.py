from decimal import Decimal
from unittest import TestCase

from real_estate_helm.underwriting import cap_rate, cash_on_cash_return, debt_yield, loan_to_value


class UnderwritingTests(TestCase):
    def test_core_ratio_metrics(self) -> None:
        self.assertEqual(loan_to_value(7000000, 10000000), Decimal("0.7"))
        self.assertEqual(cap_rate(600000, 10000000), Decimal("0.06"))
        self.assertEqual(debt_yield(600000, 7000000), Decimal("0.08571428571428571428571428571"))
        self.assertEqual(cash_on_cash_return(250000, 3000000), Decimal("0.08333333333333333333333333333"))

    def test_zero_denominator_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            cap_rate(100000, 0)

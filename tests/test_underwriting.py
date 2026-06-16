from decimal import Decimal
from unittest import TestCase

from real_estate_helm.underwriting import (
    break_even_occupancy,
    cap_rate,
    cash_on_cash_return,
    cost_overrun_percent,
    debt_yield,
    development_spread,
    downside_loss_exposure,
    exit_value,
    hold_period_return,
    inflation_adjusted_amount,
    internal_rate_of_return,
    loan_to_cost,
    loan_to_value,
    margin_on_cost,
    maintenance_reserve,
    net_present_value,
    payback_period,
    property_tax_expense,
    refinance_proceeds,
    sensitivity_table,
    yield_on_cost,
)


class UnderwritingTests(TestCase):
    def test_core_ratio_metrics(self) -> None:
        self.assertEqual(loan_to_value(7000000, 10000000), Decimal("0.7"))
        self.assertEqual(loan_to_cost(7000000, 12000000), Decimal("0.5833333333333333333333333333"))
        self.assertEqual(cap_rate(600000, 10000000), Decimal("0.06"))
        self.assertEqual(debt_yield(600000, 7000000), Decimal("0.08571428571428571428571428571"))
        self.assertEqual(cash_on_cash_return(250000, 3000000), Decimal("0.08333333333333333333333333333"))
        self.assertEqual(break_even_occupancy(400000, 300000, 1000000), Decimal("0.7"))

    def test_development_and_exit_metrics(self) -> None:
        self.assertEqual(exit_value(600000, Decimal("0.06")), Decimal("10000000"))
        self.assertEqual(yield_on_cost(900000, 12000000), Decimal("0.075"))
        self.assertEqual(margin_on_cost(15000000, 12000000), Decimal("0.25"))
        self.assertEqual(development_spread(Decimal("0.075"), Decimal("0.06")), Decimal("0.015"))
        self.assertEqual(cost_overrun_percent(1100000, 1000000), Decimal("0.1"))

    def test_zero_denominator_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            cap_rate(100000, 0)

    def test_return_metrics_and_sensitivity(self) -> None:
        cash_flows = [Decimal("-100"), Decimal("40"), Decimal("40"), Decimal("40")]

        self.assertEqual(net_present_value(Decimal("0"), cash_flows), Decimal("20"))
        self.assertAlmostEqual(float(internal_rate_of_return(cash_flows)), 0.097, places=3)
        self.assertEqual(payback_period(cash_flows), Decimal("2.5"))
        self.assertEqual(hold_period_return(120, 30, 100), Decimal("0.5"))
        self.assertEqual(refinance_proceeds(900000, Decimal("0.09"), 7000000, 150000), Decimal("2850000"))
        self.assertEqual(downside_loss_exposure(3000000, 8500000, 6500000, 250000), Decimal("1250000"))
        self.assertEqual(
            sensitivity_table(Decimal("100"), [Decimal("-0.1"), Decimal("0"), Decimal("0.1")]),
            {"-0.1": Decimal("90.0"), "0": Decimal("100"), "0.1": Decimal("110.0")},
        )

    def test_tax_inflation_and_reserve_assumptions(self) -> None:
        self.assertEqual(inflation_adjusted_amount(100000, Decimal("0.03"), 2), Decimal("106090.0000"))
        self.assertEqual(property_tax_expense(10000000, Decimal("0.025"), Decimal("0.10")), Decimal("225000.000"))
        self.assertEqual(
            maintenance_reserve(
                unit_count=100,
                reserve_per_unit=Decimal("350"),
                square_feet=25000,
                reserve_per_square_foot=Decimal("0.40"),
            ),
            Decimal("45000.00"),
        )

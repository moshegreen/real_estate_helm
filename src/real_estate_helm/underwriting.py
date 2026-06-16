"""Small underwriting calculations used by the first domain slice."""

from __future__ import annotations

from decimal import Decimal


def _decimal(value: Decimal | int | float | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def loan_to_value(debt_amount: Decimal | int | float | str, asset_value: Decimal | int | float | str) -> Decimal:
    return _ratio(debt_amount, asset_value)


def loan_to_cost(debt_amount: Decimal | int | float | str, total_project_cost: Decimal | int | float | str) -> Decimal:
    return _ratio(debt_amount, total_project_cost)


def cap_rate(net_operating_income: Decimal | int | float | str, purchase_price: Decimal | int | float | str) -> Decimal:
    return _ratio(net_operating_income, purchase_price)


def debt_yield(net_operating_income: Decimal | int | float | str, debt_amount: Decimal | int | float | str) -> Decimal:
    return _ratio(net_operating_income, debt_amount)


def cash_on_cash_return(
    annual_cash_flow: Decimal | int | float | str,
    equity_invested: Decimal | int | float | str,
) -> Decimal:
    return _ratio(annual_cash_flow, equity_invested)


def break_even_occupancy(
    operating_expenses: Decimal | int | float | str,
    annual_debt_service: Decimal | int | float | str,
    gross_potential_income: Decimal | int | float | str,
) -> Decimal:
    return _ratio(_decimal(operating_expenses) + _decimal(annual_debt_service), gross_potential_income)


def debt_service_coverage_ratio(
    net_operating_income: Decimal | int | float | str,
    annual_debt_service: Decimal | int | float | str,
) -> Decimal:
    return _ratio(net_operating_income, annual_debt_service)


def equity_multiple(
    total_distributions: Decimal | int | float | str,
    equity_invested: Decimal | int | float | str,
) -> Decimal:
    return _ratio(total_distributions, equity_invested)


def total_profit(
    total_distributions: Decimal | int | float | str,
    equity_invested: Decimal | int | float | str,
) -> Decimal:
    return _decimal(total_distributions) - _decimal(equity_invested)


def variance(
    actual: Decimal | int | float | str,
    projected: Decimal | int | float | str,
) -> Decimal:
    return _decimal(actual) - _decimal(projected)


def variance_percent(
    actual: Decimal | int | float | str,
    projected: Decimal | int | float | str,
) -> Decimal:
    return _ratio(variance(actual, projected), projected)


def development_budget_total(
    *,
    land_cost: Decimal | int | float | str = 0,
    hard_costs: Decimal | int | float | str = 0,
    soft_costs: Decimal | int | float | str = 0,
    contingency: Decimal | int | float | str = 0,
) -> Decimal:
    return _decimal(land_cost) + _decimal(hard_costs) + _decimal(soft_costs) + _decimal(contingency)


def exit_value(stabilized_noi: Decimal | int | float | str, exit_cap_rate: Decimal | int | float | str) -> Decimal:
    return _ratio(stabilized_noi, exit_cap_rate)


def yield_on_cost(stabilized_noi: Decimal | int | float | str, total_project_cost: Decimal | int | float | str) -> Decimal:
    return _ratio(stabilized_noi, total_project_cost)


def margin_on_cost(
    projected_completion_value: Decimal | int | float | str,
    total_project_cost: Decimal | int | float | str,
) -> Decimal:
    return _ratio(_decimal(projected_completion_value) - _decimal(total_project_cost), total_project_cost)


def development_spread(
    stabilized_yield_on_cost: Decimal | int | float | str,
    market_cap_rate: Decimal | int | float | str,
) -> Decimal:
    return _decimal(stabilized_yield_on_cost) - _decimal(market_cap_rate)


def cost_overrun_percent(
    actual_cost: Decimal | int | float | str,
    budgeted_cost: Decimal | int | float | str,
) -> Decimal:
    return variance_percent(actual_cost, budgeted_cost)


def net_present_value(discount_rate: Decimal | int | float | str, cash_flows: list[Decimal | int | float | str]) -> Decimal:
    rate = _decimal(discount_rate)
    return sum(_decimal(cash_flow) / ((Decimal("1") + rate) ** period) for period, cash_flow in enumerate(cash_flows))


def internal_rate_of_return(
    cash_flows: list[Decimal | int | float | str],
    *,
    guess_low: Decimal | int | float | str = "-0.99",
    guess_high: Decimal | int | float | str = "10",
    iterations: int = 100,
) -> Decimal:
    flows = [_decimal(cash_flow) for cash_flow in cash_flows]
    low = _decimal(guess_low)
    high = _decimal(guess_high)
    for _ in range(iterations):
        mid = (low + high) / Decimal("2")
        value = net_present_value(mid, flows)
        if value > 0:
            low = mid
        else:
            high = mid
    return (low + high) / Decimal("2")


def payback_period(cash_flows: list[Decimal | int | float | str]) -> Decimal | None:
    cumulative = Decimal("0")
    previous = Decimal("0")
    for index, cash_flow in enumerate(cash_flows):
        previous = cumulative
        cumulative += _decimal(cash_flow)
        if cumulative >= 0:
            if index == 0:
                return Decimal("0")
            period_cash_flow = cumulative - previous
            if period_cash_flow == 0:
                return Decimal(index)
            fraction = abs(previous) / period_cash_flow
            return Decimal(index - 1) + fraction
    return None


def sensitivity_table(
    base_value: Decimal | int | float | str,
    changes: list[Decimal | int | float | str],
) -> dict[str, Decimal]:
    base = _decimal(base_value)
    return {str(change): base * (Decimal("1") + _decimal(change)) for change in changes}


def _ratio(numerator: Decimal | int | float | str, denominator: Decimal | int | float | str) -> Decimal:
    denominator_decimal = _decimal(denominator)
    if denominator_decimal == 0:
        raise ValueError("denominator must not be zero")
    return _decimal(numerator) / denominator_decimal

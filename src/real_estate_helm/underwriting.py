"""Small underwriting calculations used by the first domain slice."""

from __future__ import annotations

from decimal import Decimal


def _decimal(value: Decimal | int | float | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def loan_to_value(debt_amount: Decimal | int | float | str, asset_value: Decimal | int | float | str) -> Decimal:
    return _ratio(debt_amount, asset_value)


def cap_rate(net_operating_income: Decimal | int | float | str, purchase_price: Decimal | int | float | str) -> Decimal:
    return _ratio(net_operating_income, purchase_price)


def debt_yield(net_operating_income: Decimal | int | float | str, debt_amount: Decimal | int | float | str) -> Decimal:
    return _ratio(net_operating_income, debt_amount)


def cash_on_cash_return(
    annual_cash_flow: Decimal | int | float | str,
    equity_invested: Decimal | int | float | str,
) -> Decimal:
    return _ratio(annual_cash_flow, equity_invested)


def _ratio(numerator: Decimal | int | float | str, denominator: Decimal | int | float | str) -> Decimal:
    denominator_decimal = _decimal(denominator)
    if denominator_decimal == 0:
        raise ValueError("denominator must not be zero")
    return _decimal(numerator) / denominator_decimal

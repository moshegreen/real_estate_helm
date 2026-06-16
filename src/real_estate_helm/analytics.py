"""Deterministic portfolio and deal analytics."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt
from typing import Any

from real_estate_helm.domain import AlertStatus, Asset, CashFlowRecord, Coordinates, Deal, DealStatus, ObligationType
from real_estate_helm.underwriting import variance, variance_percent


def cash_flow_variances(deal: Deal, category: str | None = None) -> list[dict[str, Any]]:
    projected = _cash_flow_index(deal.projected_cash_flows, category)
    actual = _cash_flow_index(deal.actual_cash_flows, category)
    rows = []
    for key, projected_amount in projected.items():
        actual_amount = actual.get(key, Decimal("0"))
        rows.append(
            {
                "period": key[0],
                "category": key[1],
                "projected": projected_amount,
                "actual": actual_amount,
                "variance": variance(actual_amount, projected_amount),
                "variance_percent": variance_percent(actual_amount, projected_amount)
                if projected_amount != 0
                else None,
            }
        )
    return rows


def status_counts(deals: list[Deal]) -> dict[DealStatus, int]:
    return dict(Counter(deal.status for deal in deals))


def exposure_by_asset_type(deals: list[Deal]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for deal in deals:
        asset_types = {asset.asset_type for asset in deal.assets if asset.asset_type}
        if not asset_types and deal.identity.asset_type:
            asset_types = {deal.identity.asset_type}
        for asset_type in asset_types:
            counts[asset_type] += 1
    return dict(counts)


def exposure_by_geography(deals: list[Deal]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for deal in deals:
        for asset in deal.assets:
            if asset.address and asset.address.state:
                counts[asset.address.state] += 1
            elif deal.identity.address:
                counts["unknown"] += 1
    return dict(counts)


def exposure_by_sponsor(deals: list[Deal]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for deal in deals:
        counts[deal.identity.sponsor or "unknown"] += 1
    return dict(counts)


def debt_maturity_schedule(deals: list[Deal]) -> list[dict[str, Any]]:
    rows = []
    for deal in deals:
        for terms in deal.debt_terms:
            if terms.maturity_date:
                rows.append(
                    {
                        "deal_id": deal.id,
                        "deal_name": deal.identity.name,
                        "lender": terms.lender,
                        "maturity_date": terms.maturity_date,
                        "debt_amount": terms.debt_amount,
                    }
                )
    return sorted(rows, key=lambda row: row["maturity_date"])


def upcoming_capital_calls(
    deals: list[Deal],
    *,
    today: date | None = None,
    window_days: int = 180,
) -> list[dict[str, Any]]:
    today = today or date.today()
    rows = []
    for deal in deals:
        for obligation in deal.obligations:
            if obligation.obligation_type != ObligationType.CAPITAL_CALL:
                continue
            due_date = date.fromisoformat(obligation.due_date)
            days_until = (due_date - today).days
            if 0 <= days_until <= window_days:
                rows.append(
                    {
                        "deal_id": deal.id,
                        "deal_name": deal.identity.name,
                        "title": obligation.title,
                        "due_date": obligation.due_date,
                        "amount": obligation.amount,
                        "days_until": days_until,
                    }
                )
    return sorted(rows, key=lambda row: row["due_date"])


def portfolio_dashboard_metrics(deals: list[Deal]) -> dict[str, Any]:
    alerts = open_alerts(deals)
    return {
        "deal_count": len(deals),
        "status_counts": {status.value: count for status, count in status_counts(deals).items()},
        "current_portfolio_value": _sum_deal_values(deals, {"current_value", "portfolio_value", "asset_value", "purchase_price"}),
        "equity_invested": _sum_deal_values(deals, {"equity_invested", "equity_required"}),
        "realized_gains": _sum_deal_values(deals, {"realized_gain", "realized_gains"}),
        "unrealized_gains": _sum_deal_values(deals, {"unrealized_gain", "unrealized_gains"}),
        "projected_irr_by_deal": _scenario_metric_by_deal(deals, "irr"),
        "equity_multiple_by_deal": _scenario_metric_by_deal(deals, "equity_multiple"),
        "exposure_by_asset_type": exposure_by_asset_type(deals),
        "exposure_by_geography": exposure_by_geography(deals),
        "exposure_by_sponsor": exposure_by_sponsor(deals),
        "debt_maturity_schedule": debt_maturity_schedule(deals),
        "upcoming_capital_calls": upcoming_capital_calls(deals),
        "covenant_watch_count": len([item for item in alerts if item[1].category in {"debt", "cash_flow"}]),
        "open_alert_count": len(alerts),
    }


def assets_within_radius(
    deals: list[Deal],
    center: Coordinates,
    radius_km: float,
) -> list[tuple[Deal, Asset, float]]:
    matches = []
    for deal in deals:
        for asset in deal.assets:
            if asset.coordinates is None:
                continue
            distance = distance_km(center, asset.coordinates)
            if distance <= radius_km:
                matches.append((deal, asset, distance))
    return sorted(matches, key=lambda item: item[2])


def distance_km(left: Coordinates, right: Coordinates) -> float:
    earth_radius_km = 6371.0088
    lat1 = radians(left.latitude)
    lat2 = radians(right.latitude)
    delta_lat = radians(right.latitude - left.latitude)
    delta_lon = radians(right.longitude - left.longitude)
    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(a))


def open_alerts(deals: list[Deal]) -> list[tuple[Deal, Any]]:
    alerts = []
    for deal in deals:
        for alert in deal.alerts:
            if alert.status in {AlertStatus.OPEN, AlertStatus.ESCALATED}:
                alerts.append((deal, alert))
    return alerts


def rejected_deals(deals: list[Deal]) -> list[Deal]:
    return [deal for deal in deals if deal.status == DealStatus.REJECTED]


def rejected_deal_hindsight(deals: list[Deal]) -> list[dict[str, Any]]:
    rows = []
    for deal in rejected_deals(deals):
        later_sale = _first_comp_value(deal, {"sale", "later_sale"})
        proposed_price = _first_assumption_value(deal, {"purchase_price", "proposed_price"})
        rows.append(
            {
                "deal_id": deal.id,
                "name": deal.identity.name,
                "rejection_reason": deal.decision_history[-1].reason if deal.decision_history else None,
                "proposed_price": proposed_price,
                "later_sale_price": later_sale,
                "missed_gain": later_sale - proposed_price
                if later_sale is not None and proposed_price is not None
                else None,
            }
        )
    return rows


def actual_vs_underwritten(deal: Deal, metric_name: str) -> dict[str, Any]:
    underwritten = None
    actual = None
    for scenario in deal.scenarios:
        if scenario.outputs.get(metric_name) is None:
            continue
        if scenario.scenario_type.value in {"analyst_base_case", "acquisition_case"} and underwritten is None:
            underwritten = Decimal(str(scenario.outputs[metric_name]))
        if scenario.scenario_type.value == "actuals":
            actual = Decimal(str(scenario.outputs[metric_name]))
    return {
        "metric": metric_name,
        "underwritten": underwritten,
        "actual": actual,
        "variance": variance(actual, underwritten) if actual is not None and underwritten is not None else None,
        "variance_percent": variance_percent(actual, underwritten)
        if actual is not None and underwritten not in {None, Decimal("0")}
        else None,
    }


def forecast_vs_actual_learning(
    deals: list[Deal],
    metrics: list[str] | None = None,
    *,
    materiality_threshold: Decimal = Decimal("0.05"),
) -> list[dict[str, Any]]:
    metrics = metrics or ["noi", "irr", "equity_multiple", "cash_on_cash", "dscr"]
    rows = []
    for metric in metrics:
        comparisons = [
            (deal, actual_vs_underwritten(deal, metric))
            for deal in deals
        ]
        complete = [
            (deal, comparison)
            for deal, comparison in comparisons
            if comparison["underwritten"] is not None and comparison["actual"] is not None
        ]
        if not complete:
            continue
        variances = [comparison["variance"] for _, comparison in complete if comparison["variance"] is not None]
        variance_percents = [
            comparison["variance_percent"]
            for _, comparison in complete
            if comparison["variance_percent"] is not None
        ]
        average_variance = sum(variances, Decimal("0")) / Decimal(len(variances)) if variances else None
        average_variance_percent = (
            sum(variance_percents, Decimal("0")) / Decimal(len(variance_percents))
            if variance_percents
            else None
        )
        if average_variance_percent is None:
            direction = "insufficient_data"
        elif average_variance_percent >= materiality_threshold:
            direction = "underwritten_conservative"
        elif average_variance_percent <= -materiality_threshold:
            direction = "underwritten_aggressive"
        else:
            direction = "near_underwriting"
        rows.append(
            {
                "metric": metric,
                "deal_count": len(complete),
                "average_variance": average_variance,
                "average_variance_percent": average_variance_percent,
                "direction": direction,
            }
        )
    return rows


def occupancy_rate(deal: Deal) -> Decimal | None:
    rent_roll_rate = rent_roll_occupancy_rate(deal)
    if rent_roll_rate is not None:
        return rent_roll_rate
    total_units = sum(asset.unit_count or 0 for asset in deal.assets)
    if total_units == 0:
        return None
    leased_units = len({lease.unit for lease in deal.leases if lease.unit})
    return Decimal(leased_units) / Decimal(total_units)


def rent_roll_occupancy_rate(deal: Deal, *, as_of_date: str | None = None) -> Decimal | None:
    rows = _rent_roll_rows(deal, as_of_date)
    if not rows:
        return None
    occupied = len([row for row in rows if row.occupied])
    return Decimal(occupied) / Decimal(len(rows))


def vacancy_rate(deal: Deal, *, as_of_date: str | None = None) -> Decimal | None:
    occupancy = rent_roll_occupancy_rate(deal, as_of_date=as_of_date)
    return Decimal("1") - occupancy if occupancy is not None else None


def market_rent_gap(deal: Deal, *, as_of_date: str | None = None) -> dict[str, Any]:
    rows = _rent_roll_rows(deal, as_of_date)
    actual = sum((Decimal(str(row.monthly_rent)) for row in rows if row.monthly_rent is not None), Decimal("0"))
    market = sum((Decimal(str(row.market_rent)) for row in rows if row.market_rent is not None), Decimal("0"))
    return {
        "actual_monthly_rent": actual,
        "market_monthly_rent": market,
        "gap": market - actual if market else None,
        "gap_percent": ((market - actual) / market) if market else None,
    }


def concessions_total(deal: Deal, *, as_of_date: str | None = None) -> Decimal:
    return sum(
        (Decimal(str(row.concessions)) for row in _rent_roll_rows(deal, as_of_date) if row.concessions is not None),
        Decimal("0"),
    )


def bad_debt_total(deal: Deal, *, as_of_date: str | None = None) -> Decimal:
    return sum(
        (Decimal(str(row.bad_debt)) for row in _rent_roll_rows(deal, as_of_date) if row.bad_debt is not None),
        Decimal("0"),
    )


def lease_expiry_schedule(deal: Deal) -> dict[str, int]:
    schedule: dict[str, int] = defaultdict(int)
    for lease in deal.leases:
        if lease.end_date:
            schedule[lease.end_date[:4]] += 1
    return dict(sorted(schedule.items()))


def tenant_concentration(deal: Deal) -> list[dict[str, Any]]:
    names_by_id = {tenant.id: tenant.name for tenant in deal.tenants}
    rent_by_tenant: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for lease in deal.leases:
        if lease.annual_rent is not None:
            rent_by_tenant[lease.tenant_id] += Decimal(str(lease.annual_rent))
    total_rent = sum(rent_by_tenant.values(), Decimal("0"))
    rows = []
    for tenant_id, annual_rent in rent_by_tenant.items():
        rows.append(
            {
                "tenant_id": tenant_id,
                "tenant_name": names_by_id.get(tenant_id),
                "annual_rent": annual_rent,
                "percent_of_rent": annual_rent / total_rent if total_rent else None,
            }
        )
    return sorted(rows, key=lambda row: row["annual_rent"], reverse=True)


def weighted_renewal_probability(deal: Deal) -> Decimal | None:
    weighted_probability = Decimal("0")
    total_weight = Decimal("0")
    for lease in deal.leases:
        if lease.renewal_probability is None:
            continue
        weight = Decimal(str(lease.annual_rent)) if lease.annual_rent is not None else Decimal("1")
        weighted_probability += Decimal(str(lease.renewal_probability)) * weight
        total_weight += weight
    if total_weight == 0:
        return None
    return weighted_probability / total_weight


def renewal_probability_by_tenant(deal: Deal) -> list[dict[str, Any]]:
    names_by_id = {tenant.id: tenant.name for tenant in deal.tenants}
    rows = []
    for lease in deal.leases:
        if lease.renewal_probability is None:
            continue
        rows.append(
            {
                "tenant_id": lease.tenant_id,
                "tenant_name": names_by_id.get(lease.tenant_id),
                "unit": lease.unit,
                "end_date": lease.end_date,
                "annual_rent": lease.annual_rent,
                "renewal_probability": Decimal(str(lease.renewal_probability)),
            }
        )
    return sorted(rows, key=lambda row: (row["end_date"] or "", row["tenant_name"] or ""))


def weighted_average_lease_term(deal: Deal, *, as_of: date | None = None) -> Decimal | None:
    as_of = as_of or date.today()
    weighted_days = Decimal("0")
    total_weight = Decimal("0")
    for lease in deal.leases:
        if lease.end_date is None or lease.annual_rent is None:
            continue
        days_remaining = max((date.fromisoformat(lease.end_date) - as_of).days, 0)
        weight = Decimal(str(lease.annual_rent))
        weighted_days += Decimal(days_remaining) * weight
        total_weight += weight
    if total_weight == 0:
        return None
    return (weighted_days / total_weight) / Decimal("365")


def _cash_flow_index(records: list[CashFlowRecord], category: str | None) -> dict[tuple[str, str], Decimal]:
    index: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for record in records:
        if category is None or record.category == category:
            index[(record.period, record.category)] += Decimal(str(record.amount))
    return dict(index)


def _rent_roll_rows(deal: Deal, as_of_date: str | None = None) -> list[Any]:
    if as_of_date is None:
        return list(deal.rent_roll)
    return [row for row in deal.rent_roll if row.as_of_date == as_of_date]


def _first_assumption_value(deal: Deal, names: set[str]) -> Decimal | None:
    for assumption in deal.assumptions:
        if assumption.name in names:
            return Decimal(str(assumption.value))
    return None


def _first_comp_value(deal: Deal, comp_types: set[str]) -> Decimal | None:
    for comp in deal.market_comps:
        if comp.comp_type in comp_types:
            return Decimal(str(comp.value))
    return None


def _sum_deal_values(deals: list[Deal], names: set[str]) -> Decimal:
    total = Decimal("0")
    for deal in deals:
        value = _first_assumption_value(deal, names)
        if value is not None:
            total += value
    return total


def _scenario_metric_by_deal(deals: list[Deal], metric: str) -> list[dict[str, Any]]:
    rows = []
    preferred = {"current_reforecast", "acquisition_case", "analyst_base_case", "investment_committee_case"}
    for deal in deals:
        for scenario in deal.scenarios:
            if scenario.outputs.get(metric) is None or scenario.scenario_type.value not in preferred:
                continue
            rows.append(
                {
                    "deal_id": deal.id,
                    "deal_name": deal.identity.name,
                    "scenario": scenario.name,
                    "value": scenario.outputs[metric],
                }
            )
            break
    return rows

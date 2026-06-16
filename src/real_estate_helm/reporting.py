"""Report generators for deal review artifacts."""

from __future__ import annotations

import csv
import io
import json
from decimal import Decimal

from real_estate_helm.analytics import (
    cash_flow_variances,
    exposure_by_asset_type,
    exposure_by_geography,
    open_alerts,
    rejected_deal_hindsight,
    status_counts,
)
from real_estate_helm.domain import Deal, FactReviewStatus
from real_estate_helm.export_controls import redacted_deal_export
from real_estate_helm.serialization import deal_to_dict
from real_estate_helm.underwriting import debt_service_coverage_ratio, development_budget_total, variance


def generate_ic_memo_markdown(deal: Deal) -> str:
    assumption_values = {assumption.name: assumption.value for assumption in deal.assumptions}
    lines = [
        f"# Investment Committee Memo: {deal.identity.name}",
        "",
        "## Deal Summary",
        f"- Status: {deal.status.value}",
        f"- Asset type: {deal.identity.asset_type or 'Not specified'}",
        f"- Address: {deal.identity.address or 'Not specified'}",
        f"- Sponsor: {deal.identity.sponsor or 'Not specified'}",
        f"- Broker: {deal.identity.broker or 'Not specified'}",
        f"- Seller: {deal.identity.seller or 'Not specified'}",
        f"- Source: {deal.identity.source or 'Not specified'}",
        "",
        "## Investment Thesis",
        f"- {assumption_values.get('investment_thesis', 'No investment thesis recorded.')}",
        "",
        "## Property Details",
    ]
    if deal.assets:
        for asset in deal.assets:
            address = asset.address.line1 if asset.address else deal.identity.address or "Not specified"
            lines.append(
                f"- {asset.name}: {asset.asset_type or deal.identity.asset_type or 'asset type not specified'}, "
                f"{address}, units {asset.unit_count or 'n/a'}, building size {asset.building_size or 'n/a'}"
            )
    else:
        lines.append("- No asset records.")
    lines.extend(
        [
            "",
            "## Sponsor Details",
            f"- Sponsor: {deal.identity.sponsor or 'Not specified'}",
            f"- Broker: {deal.identity.broker or 'Not specified'}",
            f"- Seller: {deal.identity.seller or 'Not specified'}",
            "",
            "## Sources and Uses",
        ]
    )
    source_use_names = {"purchase_price", "equity_required", "debt_amount", "sources_and_uses", "closing_costs"}
    _append_assumption_subset(lines, deal, source_use_names, "- No sources and uses assumptions recorded.")

    lines.extend(["", "## Debt Terms"])
    if deal.debt_terms:
        for terms in deal.debt_terms:
            lines.append(
                f"- {terms.lender or 'Debt'}: amount {terms.debt_amount or 'not specified'}, "
                f"rate {terms.interest_rate or 'not specified'}, maturity {terms.maturity_date or 'not specified'}, "
                f"DSCR covenant {terms.covenant_dscr or 'not specified'}"
            )
    else:
        lines.append("- No debt terms recorded.")

    lines.extend(["", "## Projected Returns"])
    return_metrics = {"irr", "equity_multiple", "cash_on_cash", "dscr", "exit_value", "total_profit"}
    _append_scenario_metric_subset(lines, deal, return_metrics, "- No projected return outputs recorded.")

    lines.extend(["", "## Scenario Table"])
    if deal.scenarios:
        for scenario in deal.scenarios:
            assumptions = ", ".join(f"{item.name}: {item.value}" for item in scenario.assumptions) or "No scenario assumptions"
            outputs = ", ".join(f"{key}: {value}" for key, value in scenario.outputs.items()) or "No outputs"
            lines.append(f"- {scenario.name} ({scenario.scenario_type.value}) | {assumptions} | {outputs}")
    else:
        lines.append("- No scenarios recorded.")

    lines.extend(["", "## Sensitivity Snapshot"])
    sensitivity_assumptions = [item for item in deal.assumptions if "sensitivity" in item.name or "stress" in item.name]
    if sensitivity_assumptions:
        for assumption in sensitivity_assumptions:
            lines.append(f"- {assumption.name}: {assumption.value}. Rationale: {assumption.rationale}")
    else:
        lines.append("- No sensitivity assumptions recorded.")

    lines.extend(["", "## Comparable Deals"])
    if deal.market_comps:
        for comp in deal.market_comps:
            lines.append(
                f"- {comp.name}: {comp.comp_type}, value {comp.value}, "
                f"distance {comp.distance_miles or 'n/a'}, source {comp.source or 'not specified'}"
            )
    else:
        lines.append("- No comparable deals recorded.")

    lines.extend(["", "## Map and Local Market Context"])
    context_count = 0
    if deal.assets:
        for asset in deal.assets:
            if asset.coordinates:
                lines.append(f"- {asset.name}: coordinates {asset.coordinates.latitude}, {asset.coordinates.longitude}")
                context_count += 1
    if deal.location_context:
        for item in deal.location_context:
            lines.append(
                f"- {item.item_type.value}: {item.name}, distance {item.distance_miles or 'n/a'}, "
                f"source {item.source or 'not specified'}"
            )
            context_count += 1
    if deal.news_events:
        for event in deal.news_events[:5]:
            lines.append(f"- News: {event.classification.value} - {event.title}")
            context_count += 1
    if context_count == 0:
        lines.append("- No map or local market context recorded.")

    lines.extend(
        [
            "",
            "## Recommendation",
        ]
    )
    if deal.investment_decisions:
        for decision in deal.investment_decisions:
            lines.append(f"- {decision.recommendation}: {decision.rationale} ({decision.actor})")
    else:
        lines.append(f"- {assumption_values.get('recommendation', 'No recommendation recorded.')}")

    lines.extend(
        [
            "",
            "## Reviewed Facts",
        ]
    )
    reviewed = deal.accepted_facts()
    if reviewed:
        for fact in reviewed:
            lines.append(f"- {fact.field_name}: {fact.value} ({_source_label(fact.source)})")
    else:
        lines.append("- No accepted facts yet.")

    lines.extend(["", "## Assumptions"])
    if deal.assumptions:
        for assumption in deal.assumptions:
            lines.append(f"- {assumption.name}: {assumption.value}. Rationale: {assumption.rationale}")
    else:
        lines.append("- No assumptions recorded yet.")

    lines.extend(["", "## Scenario Detail"])
    if deal.scenarios:
        for scenario in deal.scenarios:
            outputs = ", ".join(f"{key}: {value}" for key, value in scenario.outputs.items()) or "No outputs"
            lines.append(f"- {scenario.name} ({scenario.scenario_type.value}): {outputs}")
    else:
        lines.append("- No scenarios recorded yet.")

    lines.extend(["", "## Alerts and Red Flags"])
    open_alerts = deal.open_alerts()
    if open_alerts:
        for alert in open_alerts:
            lines.append(f"- {alert.severity.value.upper()}: {alert.title} - {alert.description}")
    else:
        lines.append("- No open alerts.")

    lines.extend(["", "## Decision History"])
    if deal.decision_history:
        for event in deal.decision_history:
            lines.append(
                f"- {event.occurred_at.date()}: {event.actor} moved {event.from_status.value} "
                f"to {event.to_status.value}. Reason: {event.reason}"
            )
    else:
        lines.append("- No decisions recorded yet.")

    lines.extend(["", "Human approval required before circulation."])
    return "\n".join(lines) + "\n"


def export_deal_json(deal: Deal) -> str:
    return json.dumps(deal_to_dict(deal), indent=2, sort_keys=True)


def export_redacted_deal_json(deal: Deal) -> str:
    return json.dumps(redacted_deal_export(deal), indent=2, sort_keys=True)


def generate_portfolio_report_markdown(deals: list[Deal]) -> str:
    counts = status_counts(deals)
    alerts = open_alerts(deals)
    lines = [
        "# Portfolio Report",
        "",
        "## Summary",
        f"- Deal count: {len(deals)}",
        f"- Open alerts: {len(alerts)}",
        "",
        "## Status Counts",
    ]
    if counts:
        lines.extend(f"- {status.value}: {count}" for status, count in sorted(counts.items(), key=lambda item: item[0].value))
    else:
        lines.append("- None")
    lines.extend(["", "## Exposure by Asset Type"])
    asset_exposure = exposure_by_asset_type(deals)
    lines.extend(f"- {asset_type}: {count}" for asset_type, count in sorted(asset_exposure.items())) if asset_exposure else lines.append("- None")
    lines.extend(["", "## Exposure by Geography"])
    geo_exposure = exposure_by_geography(deals)
    lines.extend(f"- {geography}: {count}" for geography, count in sorted(geo_exposure.items())) if geo_exposure else lines.append("- None")
    lines.extend(["", "## Top Alerts"])
    if alerts:
        for deal, alert in alerts[:10]:
            lines.append(f"- {alert.severity.value.upper()}: {deal.identity.name} - {alert.title}")
    else:
        lines.append("- No open alerts.")
    return "\n".join(lines) + "\n"


def generate_monitoring_report_markdown(deal: Deal) -> str:
    lines = [
        f"# Monitoring Report: {deal.identity.name}",
        "",
        "## Cash-Flow Variance",
    ]
    variances = cash_flow_variances(deal)
    if variances:
        for row in variances:
            lines.append(
                f"- {row['period']} {row['category']}: actual {row['actual']} vs projected {row['projected']} "
                f"({row['variance']} / {row['variance_percent']})"
            )
    else:
        lines.append("- No projected-vs-actual cash-flow rows.")
    lines.extend(["", "## Development Progress"])
    if deal.development_milestones:
        for milestone in deal.development_milestones:
            lines.append(f"- {milestone.name}: {milestone.status.value}, target {milestone.target_date}")
    else:
        lines.append("- No development milestones.")
    lines.extend(["", "## Debt Covenant Watch"])
    if deal.debt_terms:
        for terms in deal.debt_terms:
            lines.append(
                f"- {terms.lender or 'Debt'}: maturity {terms.maturity_date or 'not specified'}, "
                f"DSCR covenant {terms.covenant_dscr or 'not specified'}"
            )
    else:
        lines.append("- No debt terms.")
    lines.extend(["", "## Alerts"])
    if deal.open_alerts():
        for alert in deal.open_alerts():
            lines.append(f"- {alert.severity.value.upper()}: {alert.title} - {alert.recommended_action or alert.description}")
    else:
        lines.append("- No open alerts.")
    return "\n".join(lines) + "\n"


def generate_asset_monitoring_report_markdown(deal: Deal) -> str:
    lines = [
        f"# Asset Monitoring Report: {deal.identity.name}",
        "",
        "## Assets",
    ]
    if deal.assets:
        for asset in deal.assets:
            address = asset.address.line1 if asset.address else deal.identity.address or "not specified"
            coordinates = (
                f"{asset.coordinates.latitude}, {asset.coordinates.longitude}"
                if asset.coordinates
                else "not geocoded"
            )
            lines.append(
                f"- {asset.name}: {asset.asset_type or deal.identity.asset_type or 'asset type not specified'}, "
                f"address {address}, coordinates {coordinates}, units {asset.unit_count or 'n/a'}"
            )
    else:
        lines.append("- No asset records.")

    lines.extend(["", "## Assets Missing Actuals"])
    if deal.assets and not deal.actual_cash_flows:
        for asset in deal.assets:
            lines.append(f"- {asset.name}: no actual cash-flow records imported.")
    elif not deal.assets:
        lines.append("- No asset records to check.")
    else:
        latest_period = max(record.period for record in deal.actual_cash_flows)
        lines.append(f"- Actual cash-flow records present through {latest_period}.")

    lines.extend(["", "## Local Context"])
    context_rows = []
    for item in deal.location_context:
        context_rows.append(
            f"- {item.item_type.value}: {item.name}, distance {item.distance_miles or 'n/a'}, source {item.source or 'not specified'}"
        )
    for permit in deal.permit_events:
        context_rows.append(f"- Permit {permit.permit_number}: {permit.permit_type} is {permit.status}")
    for event in deal.news_events[:5]:
        context_rows.append(f"- News {event.classification.value}: {event.title}")
    lines.extend(context_rows if context_rows else ["- No local context, permit, or news records."])

    lines.extend(["", "## Imagery"])
    if deal.imagery_snapshots:
        for snapshot in sorted(deal.imagery_snapshots, key=lambda item: item.captured_at, reverse=True)[:5]:
            lines.append(
                f"- {snapshot.captured_at}: {snapshot.source}, {snapshot.storage_uri}, notes {snapshot.notes or 'none'}"
            )
    else:
        lines.append("- No imagery snapshots.")

    lines.extend(["", "## Asset Alerts"])
    asset_alerts = [
        alert
        for alert in deal.open_alerts()
        if alert.category
        in {
            "cash_flow",
            "rent_collections",
            "development",
            "development_budget",
            "imagery_progress",
            "permit",
            "local_news",
            "market_supply",
            "property_tax",
        }
    ]
    if asset_alerts:
        for alert in asset_alerts:
            lines.append(f"- {alert.severity.value.upper()}: {alert.title} - {alert.recommended_action or alert.description}")
    else:
        lines.append("- No asset-level open alerts.")
    return "\n".join(lines) + "\n"


def generate_monthly_performance_report_markdown(deal: Deal, *, period: str | None = None) -> str:
    rows = cash_flow_variances(deal)
    if period is not None:
        rows = [row for row in rows if row["period"] == period]
    projected_total = sum((Decimal(str(row["projected"])) for row in rows), Decimal("0"))
    actual_total = sum((Decimal(str(row["actual"])) for row in rows), Decimal("0"))
    report_period = period or "all periods"
    lines = [
        f"# Monthly Performance Report: {deal.identity.name}",
        "",
        "## Summary",
        f"- Period: {report_period}",
        f"- Projected cash flow: {projected_total}",
        f"- Actual cash flow: {actual_total}",
        f"- Variance: {variance(actual_total, projected_total)}",
        "",
        "## Cash-Flow Detail",
    ]
    if rows:
        for row in rows:
            lines.append(
                f"- {row['period']} {row['category']}: projected {row['projected']}, "
                f"actual {row['actual']}, variance {row['variance']}"
            )
    else:
        lines.append("- No projected-vs-actual cash-flow rows.")
    lines.extend(["", "## Open Alerts"])
    alerts = deal.open_alerts()
    if alerts:
        for alert in alerts:
            lines.append(f"- {alert.severity.value.upper()}: {alert.title}")
    else:
        lines.append("- No open alerts.")
    return "\n".join(lines) + "\n"


def generate_development_progress_report_markdown(deal: Deal) -> str:
    lines = [
        f"# Development Progress Report: {deal.identity.name}",
        "",
        "## Budgets",
    ]
    if deal.development_budgets:
        for budget in deal.development_budgets:
            total = development_budget_total(
                land_cost=budget.land_cost,
                hard_costs=budget.hard_costs,
                soft_costs=budget.soft_costs,
                contingency=budget.contingency,
            )
            lines.append(
                f"- {budget.name}: total {total} "
                f"(land {budget.land_cost}, hard {budget.hard_costs}, soft {budget.soft_costs}, contingency {budget.contingency})"
            )
    else:
        lines.append("- No development budgets.")
    lines.extend(["", "## Milestones"])
    if deal.development_milestones:
        for milestone in deal.development_milestones:
            actual = f", actual {milestone.actual_date}" if milestone.actual_date else ""
            lines.append(f"- {milestone.name}: {milestone.status.value}, target {milestone.target_date}{actual}")
    else:
        lines.append("- No development milestones.")
    lines.extend(["", "## Capex Variance"])
    if deal.capex_items:
        for item in deal.capex_items:
            actual = Decimal(str(item.actual_amount)) if item.actual_amount is not None else None
            delta = variance(actual, item.budgeted_amount) if actual is not None else None
            lines.append(f"- {item.name}: budget {item.budgeted_amount}, actual {actual or 'not reported'}, variance {delta or 'n/a'}")
    else:
        lines.append("- No capex items.")
    return "\n".join(lines) + "\n"


def generate_lender_covenant_report_markdown(deal: Deal) -> str:
    noi = _first_numeric_value(deal, {"current_noi", "actual_noi", "noi"})
    annual_debt_service = _first_numeric_value(deal, {"annual_debt_service", "debt_service"})
    lines = [
        f"# Lender Covenant Report: {deal.identity.name}",
        "",
        "## Debt Terms",
    ]
    if deal.debt_terms:
        for terms in deal.debt_terms:
            dscr_text = "not available"
            if noi is not None and annual_debt_service not in {None, Decimal("0")}:
                dscr_text = str(debt_service_coverage_ratio(noi, annual_debt_service))
            lines.append(
                f"- {terms.lender or 'Debt'}: amount {terms.debt_amount or 'not specified'}, "
                f"maturity {terms.maturity_date or 'not specified'}, covenant DSCR {terms.covenant_dscr or 'not specified'}, "
                f"current DSCR {dscr_text}"
            )
    else:
        lines.append("- No debt terms.")
    lines.extend(["", "## Covenant Inputs"])
    lines.append(f"- NOI: {noi if noi is not None else 'not available'}")
    lines.append(f"- Annual debt service: {annual_debt_service if annual_debt_service is not None else 'not available'}")
    lines.extend(["", "## Covenant Alerts"])
    covenant_alerts = [alert for alert in deal.open_alerts() if alert.category in {"debt", "cash_flow"}]
    if covenant_alerts:
        for alert in covenant_alerts:
            lines.append(f"- {alert.severity.value.upper()}: {alert.title}")
    else:
        lines.append("- No open debt or cash-flow covenant alerts.")
    return "\n".join(lines) + "\n"


def generate_rejected_deal_review_markdown(deals: list[Deal]) -> str:
    rows = rejected_deal_hindsight(deals)
    lines = ["# Rejected Deal Review", ""]
    if not rows:
        lines.append("- No rejected deals.")
        return "\n".join(lines) + "\n"
    for row in rows:
        lines.append(
            f"- {row['name']}: reason {row['rejection_reason'] or 'not recorded'}, "
            f"proposed {row['proposed_price']}, later sale {row['later_sale_price']}, missed gain {row['missed_gain']}"
        )
    return "\n".join(lines) + "\n"


def export_cash_flow_variance_csv(rows: list[dict[str, object]]) -> str:
    output = io.StringIO()
    fieldnames = ["period", "category", "projected", "actual", "variance", "variance_percent"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fieldnames})
    return output.getvalue()


def _source_label(source: object) -> str:
    parts = [getattr(source, "name")]
    page = getattr(source, "page")
    sheet = getattr(source, "sheet")
    cell = getattr(source, "cell")
    if page is not None:
        parts.append(f"page {page}")
    if sheet is not None:
        parts.append(f"sheet {sheet}")
    if cell is not None:
        parts.append(f"cell {cell}")
    return ", ".join(parts)


def _append_assumption_subset(lines: list[str], deal: Deal, names: set[str], empty_text: str) -> None:
    rows = [assumption for assumption in deal.assumptions if assumption.name in names]
    if rows:
        for assumption in rows:
            lines.append(f"- {assumption.name}: {assumption.value}. Rationale: {assumption.rationale}")
    else:
        lines.append(empty_text)


def _append_scenario_metric_subset(lines: list[str], deal: Deal, metrics: set[str], empty_text: str) -> None:
    rows = []
    for scenario in deal.scenarios:
        values = {key: value for key, value in scenario.outputs.items() if key in metrics}
        if values:
            rows.append((scenario, values))
    if rows:
        for scenario, values in rows:
            outputs = ", ".join(f"{key}: {value}" for key, value in values.items())
            lines.append(f"- {scenario.name}: {outputs}")
    else:
        lines.append(empty_text)


def _first_numeric_value(deal: Deal, names: set[str]) -> Decimal | None:
    for assumption in deal.assumptions:
        if assumption.name in names:
            return Decimal(str(assumption.value))
    for fact in deal.extracted_facts:
        if fact.field_name in names and fact.status == FactReviewStatus.ACCEPTED:
            return Decimal(str(fact.value))
    return None

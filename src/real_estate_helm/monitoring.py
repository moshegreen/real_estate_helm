"""Monitoring rules that convert deterministic checks into alerts."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from real_estate_helm.analytics import cash_flow_variances
from real_estate_helm.domain import (
    Alert,
    AlertSeverity,
    AlertStatus,
    Deal,
    MilestoneStatus,
    NewsClassification,
    LocationContextType,
    ObligationType,
)
from real_estate_helm.underwriting import debt_service_coverage_ratio


def monitoring_alerts(
    deal: Deal,
    *,
    source_statuses: dict[str, bool] | None = None,
) -> list[Alert]:
    alerts = cash_flow_variance_alerts(deal)
    alerts.extend(rent_collection_alerts(deal))
    alerts.extend(development_delay_alerts(deal))
    alerts.extend(debt_maturity_alerts(deal))
    alerts.extend(local_news_alerts(deal))
    alerts.extend(permit_risk_alerts(deal))
    alerts.extend(property_assessment_alerts(deal))
    alerts.extend(comparable_sale_alerts(deal))
    alerts.extend(obligation_alerts(deal))
    alerts.extend(insurance_cost_alerts(deal))
    alerts.extend(contingency_consumption_alerts(deal))
    alerts.extend(sponsor_litigation_alerts(deal))
    alerts.extend(tenant_credit_alerts(deal))
    alerts.extend(competing_development_alerts(deal))
    alerts.extend(imagery_progress_alerts(deal))
    if source_statuses:
        alerts.extend(source_health_alerts(deal, source_statuses))
    return alerts


def cash_flow_variance_alerts(
    deal: Deal,
    *,
    threshold_percent: Decimal = Decimal("-0.08"),
    category: str | None = None,
) -> list[Alert]:
    alerts = []
    for row in cash_flow_variances(deal, category):
        variance_pct = row["variance_percent"]
        if variance_pct is not None and variance_pct <= threshold_percent:
            alerts.append(
                Alert(
                    title=f"{row['category']} below budget for {row['period']}",
                    severity=AlertSeverity.HIGH,
                    category="cash_flow",
                    source="cash_flow_variance",
                    description=f"Actual {row['category']} is {variance_pct:.2%} versus projection.",
                    financial_impact=row["variance"],
                    recommended_action="Review property management report and update reforecast.",
                )
            )
    return alerts


def rent_collection_alerts(
    deal: Deal,
    *,
    threshold_percent: Decimal = Decimal("-0.08"),
    consecutive_periods: int = 2,
) -> list[Alert]:
    rent_rows = [row for row in cash_flow_variances(deal) if _is_rent_collection_category(row["category"])]
    rent_rows.sort(key=lambda row: row["period"])
    latest_streak: list[dict[str, object]] = []
    current_streak: list[dict[str, object]] = []
    for row in rent_rows:
        variance_pct = row["variance_percent"]
        under_budget = variance_pct is not None and variance_pct <= threshold_percent
        if not under_budget:
            current_streak = []
            continue
        if current_streak and not _is_next_month(str(current_streak[-1]["period"]), str(row["period"])):
            current_streak = []
        current_streak.append(row)
        if len(current_streak) >= consecutive_periods:
            latest_streak = list(current_streak[-consecutive_periods:])
    if not latest_streak:
        return []
    total_variance = sum((row["variance"] for row in latest_streak), Decimal("0"))
    periods = ", ".join(row["period"] for row in latest_streak)
    return [
        Alert(
            title=f"Rent collections below budget for {consecutive_periods} consecutive months",
            severity=AlertSeverity.HIGH,
            category="rent_collections",
            source="cash_flow_variance",
            description=f"Rent collections were at least {abs(threshold_percent):.0%} below budget for {periods}.",
            financial_impact=total_variance,
            recommended_action="Review property management collections, tenant arrears, and bad debt assumptions.",
        )
    ]


def development_delay_alerts(deal: Deal, *, today: date | None = None) -> list[Alert]:
    today = today or date.today()
    alerts = []
    for milestone in deal.development_milestones:
        target_date = date.fromisoformat(milestone.target_date)
        if milestone.status == MilestoneStatus.DELAYED or (
            target_date < today and milestone.status != MilestoneStatus.COMPLETE
        ):
            alerts.append(
                Alert(
                    title=f"Development milestone delayed: {milestone.name}",
                    severity=AlertSeverity.HIGH,
                    category="development",
                    source="milestone_schedule",
                    description=f"{milestone.name} target date was {milestone.target_date}.",
                    recommended_action="Contact sponsor and update delay impact analysis.",
                )
            )
    return alerts


def add_new_alerts(deal: Deal, alerts: list[Alert]) -> int:
    existing_keys = {(alert.title, alert.category, alert.status) for alert in deal.alerts}
    count = 0
    for alert in alerts:
        key = (alert.title, alert.category, AlertStatus.OPEN)
        if key not in existing_keys:
            deal.alerts.append(alert)
            count += 1
    return count


def escalate_stale_alerts(
    deal: Deal,
    *,
    today: date | None = None,
    stale_days: int = 7,
    severities: set[AlertSeverity] | None = None,
) -> list[Alert]:
    today = today or date.today()
    severities = severities or {AlertSeverity.HIGH, AlertSeverity.CRITICAL}
    escalated: list[Alert] = []
    for alert in deal.alerts:
        age_days = _alert_age_days(alert.created_at, today)
        if alert.status == AlertStatus.OPEN and alert.severity in severities and age_days >= stale_days:
            alert.status = AlertStatus.ESCALATED
            escalated.append(alert)
    return escalated


def source_health_alerts(
    deal: Deal,
    source_statuses: dict[str, bool],
) -> list[Alert]:
    alerts = []
    for source_name, healthy in source_statuses.items():
        if not healthy:
            alerts.append(
                Alert(
                    title=f"Source health failure: {source_name}",
                    severity=AlertSeverity.MEDIUM,
                    category="source_health",
                    source=source_name,
                    description=f"{source_name} did not return healthy status.",
                    recommended_action="Check connector credentials, rate limits, and source availability.",
                )
            )
    return alerts


def local_news_alerts(deal: Deal) -> list[Alert]:
    alerts = []
    for event in deal.news_events:
        if event.classification == NewsClassification.MATERIAL_NEGATIVE:
            alerts.append(
                Alert(
                    title=f"Material negative local news: {event.title}",
                    severity=AlertSeverity.HIGH,
                    category="local_news",
                    source="news_events",
                    description=event.summary or event.title,
                    recommended_action="Review local news source and update risk register or underwriting assumptions.",
                )
            )
        elif event.classification == NewsClassification.WATCH:
            alerts.append(
                Alert(
                    title=f"Local news watch item: {event.title}",
                    severity=AlertSeverity.MEDIUM,
                    category="local_news",
                    source="news_events",
                    description=event.summary or event.title,
                    recommended_action="Monitor follow-up coverage and assess whether the event affects the deal.",
                )
            )
    return alerts


def sponsor_litigation_alerts(deal: Deal) -> list[Alert]:
    if not deal.identity.sponsor:
        return []
    sponsor = deal.identity.sponsor.casefold()
    litigation_terms = {"litigation", "lawsuit", "sued", "court", "claim", "fraud", "bankruptcy"}
    alerts = []
    for event in deal.news_events:
        text = " ".join([event.title, event.summary or ""]).casefold()
        if sponsor in text and any(term in text for term in litigation_terms):
            alerts.append(
                Alert(
                    title=f"Sponsor litigation mention: {event.title}",
                    severity=AlertSeverity.HIGH,
                    category="sponsor_risk",
                    source="news_events",
                    description=event.summary or event.title,
                    recommended_action="Review sponsor background, litigation details, and investment committee risk notes.",
                )
            )
    return alerts


def tenant_credit_alerts(deal: Deal) -> list[Alert]:
    risk_terms = {"bankrupt", "default", "insolv", "distress", "going concern", "closure", "watchlist"}
    alerts = []
    for tenant in deal.tenants:
        notes = (tenant.credit_notes or "").casefold()
        if any(term in notes for term in risk_terms):
            alerts.append(
                Alert(
                    title=f"Tenant credit risk: {tenant.name}",
                    severity=AlertSeverity.HIGH,
                    category="tenant_credit",
                    source="tenant_credit_notes",
                    description=tenant.credit_notes or tenant.name,
                    recommended_action="Review lease exposure, rent collection assumptions, and replacement tenant plan.",
                )
            )
            continue
        for event in deal.news_events:
            text = " ".join([event.title, event.summary or ""]).casefold()
            if tenant.name.casefold() in text and any(term in text for term in risk_terms):
                alerts.append(
                    Alert(
                        title=f"Tenant bankruptcy-related news: {tenant.name}",
                        severity=AlertSeverity.HIGH,
                        category="tenant_credit",
                        source="news_events",
                        description=event.summary or event.title,
                        recommended_action="Assess rent exposure and update downside tenant rollover assumptions.",
                    )
                )
                break
    return alerts


def competing_development_alerts(
    deal: Deal,
    *,
    radius_miles: float = 1.0,
) -> list[Alert]:
    alerts = []
    for item in deal.location_context:
        if item.item_type not in {LocationContextType.NEARBY_CONSTRUCTION, LocationContextType.COMPETING_PROPERTY}:
            continue
        if item.distance_miles is not None and item.distance_miles > radius_miles:
            continue
        alerts.append(
            Alert(
                title=f"Nearby competing development: {item.name}",
                severity=AlertSeverity.MEDIUM,
                category="market_supply",
                source=item.source or "location_context",
                description=item.notes or f"{item.name} is within {radius_miles:g} mile(s).",
                recommended_action="Review competing supply, rent growth assumptions, and lease-up sensitivity.",
            )
        )
    return alerts


def imagery_progress_alerts(
    deal: Deal,
    *,
    stalled_days: int = 45,
) -> list[Alert]:
    if not (deal.development_milestones or deal.development_budgets):
        return []
    no_progress = [
        (snapshot_date, snapshot)
        for snapshot in deal.imagery_snapshots
        if (snapshot_date := _snapshot_date(snapshot.captured_at)) is not None
        and _notes_indicate_no_progress(snapshot.notes)
    ]
    if len(no_progress) < 2:
        return []
    no_progress.sort(key=lambda item: item[0])
    first_date, first_snapshot = no_progress[0]
    latest_date, latest_snapshot = no_progress[-1]
    days_without_progress = (latest_date - first_date).days
    if days_without_progress < stalled_days:
        return []
    return [
        Alert(
            title=f"Satellite imagery shows no visible construction progress for {days_without_progress} days",
            severity=AlertSeverity.HIGH,
            category="imagery_progress",
            source=latest_snapshot.source,
            description=(
                f"Imagery notes indicate no visible site progress from {first_snapshot.captured_at} "
                f"through {latest_snapshot.captured_at}."
            ),
            recommended_action="Request sponsor construction update, compare site imagery, and refresh delay impact analysis.",
        )
    ]


def permit_risk_alerts(deal: Deal) -> list[Alert]:
    risky_statuses = {"denied", "expired", "revoked", "stalled", "appealed", "litigation"}
    alerts = []
    for permit in deal.permit_events:
        status = permit.status.casefold()
        if status in risky_statuses:
            alerts.append(
                Alert(
                    title=f"Permit risk: {permit.permit_number}",
                    severity=AlertSeverity.HIGH,
                    category="permit",
                    source="permit_events",
                    description=f"{permit.permit_type} permit is {permit.status}. {permit.description or ''}".strip(),
                    recommended_action="Contact sponsor or permitting counsel and update entitlement risk.",
                )
            )
    return alerts


def property_assessment_alerts(
    deal: Deal,
    *,
    threshold_percent: Decimal = Decimal("0.10"),
) -> list[Alert]:
    assumed = _first_assumption_decimal(deal, {"assessed_value", "tax_assessment", "property_assessment"})
    if assumed in {None, Decimal("0")}:
        return []
    alerts = []
    for record in deal.property_records:
        if record.assessed_value is None:
            continue
        assessed = Decimal(str(record.assessed_value))
        variance = (assessed - assumed) / assumed
        if variance >= threshold_percent:
            alerts.append(
                Alert(
                    title="Property assessment materially above underwriting",
                    severity=AlertSeverity.HIGH,
                    category="property_tax",
                    source=record.source,
                    description=f"Assessed value {assessed} is {variance:.2%} above underwriting assumption {assumed}.",
                    financial_impact=assessed - assumed,
                    recommended_action="Update property tax forecast and review tax appeal options.",
                )
            )
    return alerts


def comparable_sale_alerts(
    deal: Deal,
    *,
    threshold_percent: Decimal = Decimal("-0.10"),
) -> list[Alert]:
    exit_value = _first_assumption_decimal(deal, {"exit_value", "projected_completion_value", "terminal_value"})
    if exit_value in {None, Decimal("0")}:
        return []
    alerts = []
    for comp in deal.market_comps:
        if comp.comp_type not in {"sale", "later_sale", "distressed_sale"}:
            continue
        value = Decimal(str(comp.value))
        variance = (value - exit_value) / exit_value
        if variance <= threshold_percent:
            alerts.append(
                Alert(
                    title=f"Comparable sale below exit assumption: {comp.name}",
                    severity=AlertSeverity.HIGH,
                    category="market_comp",
                    source=comp.source or "market_comps",
                    description=f"Comparable value {value} is {variance:.2%} versus exit assumption {exit_value}.",
                    financial_impact=value - exit_value,
                    recommended_action="Revisit exit cap, terminal value, and downside case assumptions.",
                )
            )
    return alerts


def insurance_cost_alerts(
    deal: Deal,
    *,
    threshold_percent: Decimal = Decimal("0.20"),
) -> list[Alert]:
    budget = _first_assumption_decimal(deal, {"insurance_budget", "insurance_premium_budget"})
    actual = _first_assumption_decimal(deal, {"insurance_premium", "actual_insurance_premium"})
    if actual is None:
        actual = _cash_flow_amount(deal.actual_cash_flows, "insurance")
    if budget is None:
        budget = _cash_flow_amount(deal.projected_cash_flows, "insurance")
    if budget in {None, Decimal("0")} or actual is None:
        return []
    increase = (actual - budget) / budget
    if increase < threshold_percent:
        return []
    return [
        Alert(
            title="Insurance premium materially above budget",
            severity=AlertSeverity.HIGH,
            category="insurance",
            source="insurance_cost",
            description=f"Insurance premium {actual} is {increase:.2%} above budget {budget}.",
            financial_impact=actual - budget,
            recommended_action="Review renewal terms, reserve assumptions, and alternate quotes.",
        )
    ]


def contingency_consumption_alerts(
    deal: Deal,
    *,
    threshold_percent: Decimal = Decimal("0.70"),
) -> list[Alert]:
    alerts = []
    overrun = sum(
        (
            Decimal(str(item.actual_amount)) - Decimal(str(item.budgeted_amount))
            for item in deal.capex_items
            if item.actual_amount is not None and Decimal(str(item.actual_amount)) > Decimal(str(item.budgeted_amount))
        ),
        Decimal("0"),
    )
    if overrun <= 0:
        return alerts
    for budget in deal.development_budgets:
        contingency = Decimal(str(budget.contingency))
        if contingency == 0:
            continue
        consumed = overrun / contingency
        if consumed >= threshold_percent:
            alerts.append(
                Alert(
                    title=f"Development contingency {consumed:.0%} consumed",
                    severity=AlertSeverity.HIGH,
                    category="development_budget",
                    source="capex_actuals",
                    description=f"Capex overruns of {overrun} have consumed {consumed:.2%} of {budget.name} contingency.",
                    financial_impact=overrun,
                    recommended_action="Refresh cost-to-complete and require sponsor variance explanation.",
                )
            )
    return alerts


def _alert_age_days(created_at: datetime, today: date) -> int:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return (today - created_at.date()).days


def debt_maturity_alerts(deal: Deal, *, today: date | None = None, window_days: int = 180) -> list[Alert]:
    today = today or date.today()
    alerts = []
    for terms in deal.debt_terms:
        if terms.maturity_date is None:
            continue
        maturity = date.fromisoformat(terms.maturity_date)
        days_until = (maturity - today).days
        if 0 <= days_until <= window_days:
            alerts.append(
                Alert(
                    title=f"Debt maturity within {window_days} days",
                    severity=AlertSeverity.HIGH,
                    category="debt",
                    source="debt_terms",
                    description=f"{terms.lender or 'Debt'} matures on {terms.maturity_date}.",
                    recommended_action="Start refinance, extension, or payoff planning.",
                )
            )
    return alerts


def dscr_covenant_alerts(
    deal: Deal,
    *,
    annual_debt_service_by_lender: dict[str, Decimal],
    noi_by_lender: dict[str, Decimal],
) -> list[Alert]:
    alerts = []
    for terms in deal.debt_terms:
        if terms.covenant_dscr is None or terms.lender is None:
            continue
        annual_debt_service = annual_debt_service_by_lender.get(terms.lender)
        noi = noi_by_lender.get(terms.lender)
        if annual_debt_service is None or noi is None:
            continue
        dscr = debt_service_coverage_ratio(noi, annual_debt_service)
        covenant = Decimal(str(terms.covenant_dscr))
        if dscr < covenant:
            alerts.append(
                Alert(
                    title=f"DSCR below covenant for {terms.lender}",
                    severity=AlertSeverity.CRITICAL,
                    category="debt",
                    source="debt_terms",
                    description=f"DSCR is {dscr:.2f} versus covenant {covenant:.2f}.",
                    financial_impact=covenant - dscr,
                    recommended_action="Notify lender relationship owner and update downside plan.",
                )
            )
    return alerts


def obligation_alerts(
    deal: Deal,
    *,
    today: date | None = None,
    window_days: int = 45,
) -> list[Alert]:
    today = today or date.today()
    labels = {
        ObligationType.LEGAL_DEADLINE: "Legal deadline",
        ObligationType.DOCUMENT_EXPIRATION: "Document expiration",
        ObligationType.CAPITAL_CALL: "Capital call",
    }
    actions = {
        ObligationType.LEGAL_DEADLINE: "Confirm responsible counsel and required filing steps.",
        ObligationType.DOCUMENT_EXPIRATION: "Refresh the document or verify extension requirements.",
        ObligationType.CAPITAL_CALL: "Confirm funding source, approval status, and wire deadline.",
    }
    alerts = []
    for obligation in deal.obligations:
        due_date = date.fromisoformat(obligation.due_date)
        days_until = (due_date - today).days
        if days_until > window_days:
            continue
        overdue = days_until < 0
        label = labels[obligation.obligation_type]
        amount = f" Amount: {obligation.amount}." if obligation.amount is not None else ""
        alerts.append(
            Alert(
                title=f"{label} {'overdue' if overdue else 'due soon'}: {obligation.title}",
                severity=AlertSeverity.CRITICAL if overdue else AlertSeverity.HIGH,
                category=obligation.obligation_type.value,
                source=obligation.source or "obligations",
                description=f"{obligation.title} is due on {obligation.due_date}.{amount}",
                financial_impact=obligation.amount,
                recommended_action=actions[obligation.obligation_type],
                owner=obligation.owner,
                due_date=obligation.due_date,
            )
        )
    return alerts


def _first_assumption_decimal(deal: Deal, names: set[str]) -> Decimal | None:
    for assumption in deal.assumptions:
        if assumption.name in names:
            return Decimal(str(assumption.value))
    return None


def _cash_flow_amount(records: list[object], category: str) -> Decimal | None:
    total = Decimal("0")
    found = False
    for record in records:
        if getattr(record, "category") == category:
            total += Decimal(str(getattr(record, "amount")))
            found = True
    return total if found else None


def _snapshot_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _notes_indicate_no_progress(notes: str | None) -> bool:
    if not notes:
        return False
    text = notes.casefold()
    terms = {
        "no visible construction progress",
        "no visible progress",
        "no progress",
        "unchanged",
        "stalled",
        "inactive site",
        "no site activity",
    }
    return any(term in text for term in terms)


def _is_rent_collection_category(category: str) -> bool:
    normalized = category.replace("-", "_").replace(" ", "_").casefold()
    return normalized in {"rent", "rent_collection", "rent_collections", "collections"}


def _is_next_month(left: str, right: str) -> bool:
    try:
        left_year, left_month = [int(part) for part in left[:7].split("-")]
        right_year, right_month = [int(part) for part in right[:7].split("-")]
    except ValueError:
        return False
    if left_month == 12:
        return right_year == left_year + 1 and right_month == 1
    return right_year == left_year and right_month == left_month + 1

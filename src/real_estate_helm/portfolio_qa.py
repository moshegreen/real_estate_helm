"""Deterministic portfolio question answering over structured deal state."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from real_estate_helm.analytics import (
    actual_vs_underwritten,
    exposure_by_asset_type,
    exposure_by_geography,
    forecast_vs_actual_learning,
    open_alerts,
    rejected_deal_hindsight,
    status_counts,
)
from real_estate_helm.domain import Deal


@dataclass(frozen=True)
class PortfolioAnswer:
    question: str
    answer_type: str
    summary: str
    rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer_type": self.answer_type,
            "summary": self.summary,
            "rows": [_json_safe(row) for row in self.rows],
        }


class PortfolioQuestionAnswerer:
    def answer(self, deals: list[Deal], question: str) -> PortfolioAnswer:
        normalized = question.casefold()
        if any(term in normalized for term in ["open alert", "top alert", "urgent", "watch"]):
            return _open_alert_answer(deals, question)
        if any(term in normalized for term in ["rejected", "missed", "passed", "re-open", "reopen"]):
            return _rejected_answer(deals, question)
        if "geograph" in normalized or "state" in normalized or "market" in normalized:
            return _exposure_answer(question, "exposure_by_geography", exposure_by_geography(deals))
        if "sponsor" in normalized:
            return _exposure_answer(question, "exposure_by_sponsor", _exposure_by_sponsor(deals))
        if "asset type" in normalized or "asset class" in normalized or "exposure" in normalized:
            return _exposure_answer(question, "exposure_by_asset_type", exposure_by_asset_type(deals))
        if "actual" in normalized and ("underwritten" in normalized or "underwriting" in normalized):
            return _actual_vs_underwritten_answer(deals, question, _metric_from_question(normalized))
        if "forecast" in normalized or "learning" in normalized or "conservative" in normalized:
            return _forecast_learning_answer(deals, question)
        if "status" in normalized or "pipeline" in normalized:
            counts = {status.value: count for status, count in status_counts(deals).items()}
            return _exposure_answer(question, "status_counts", counts)
        return PortfolioAnswer(
            question=question,
            answer_type="unsupported",
            summary="I can answer questions about alerts, rejected deals, exposure, status, and actual-vs-underwritten metrics.",
            rows=[],
        )


def _open_alert_answer(deals: list[Deal], question: str) -> PortfolioAnswer:
    alerts = sorted(
        open_alerts(deals),
        key=lambda item: _severity_rank(item[1].severity.value),
        reverse=True,
    )
    rows = [
        {
            "deal_id": deal.id,
            "deal_name": deal.identity.name,
            "severity": alert.severity.value,
            "category": alert.category,
            "title": alert.title,
            "recommended_action": alert.recommended_action,
        }
        for deal, alert in alerts
    ]
    return PortfolioAnswer(question, "open_alerts", f"{len(rows)} open or escalated alerts.", rows)


def _rejected_answer(deals: list[Deal], question: str) -> PortfolioAnswer:
    rows = rejected_deal_hindsight(deals)
    reopen = [row for row in rows if row.get("missed_gain") is not None and row["missed_gain"] > 0]
    answer_rows = reopen if reopen else rows
    return PortfolioAnswer(
        question,
        "rejected_deal_hindsight",
        f"{len(reopen)} rejected deals show positive missed-gain signals.",
        answer_rows,
    )


def _exposure_answer(question: str, answer_type: str, counts: dict[str, int]) -> PortfolioAnswer:
    rows = [{"name": name, "count": count} for name, count in sorted(counts.items())]
    return PortfolioAnswer(question, answer_type, f"{len(rows)} categories found.", rows)


def _actual_vs_underwritten_answer(deals: list[Deal], question: str, metric: str) -> PortfolioAnswer:
    rows = []
    for deal in deals:
        result = actual_vs_underwritten(deal, metric)
        if result["underwritten"] is None and result["actual"] is None:
            continue
        rows.append({"deal_id": deal.id, "deal_name": deal.identity.name, **result})
    return PortfolioAnswer(question, "actual_vs_underwritten", f"{len(rows)} deals have {metric} comparison data.", rows)


def _forecast_learning_answer(deals: list[Deal], question: str) -> PortfolioAnswer:
    rows = forecast_vs_actual_learning(deals)
    aggressive = [row for row in rows if row["direction"] == "underwritten_aggressive"]
    conservative = [row for row in rows if row["direction"] == "underwritten_conservative"]
    summary = f"{len(aggressive)} aggressive and {len(conservative)} conservative forecast patterns found."
    return PortfolioAnswer(question, "forecast_vs_actual_learning", summary, rows)


def _exposure_by_sponsor(deals: list[Deal]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for deal in deals:
        sponsor = deal.identity.sponsor or "unknown"
        counts[sponsor] = counts.get(sponsor, 0) + 1
    return counts


def _metric_from_question(question: str) -> str:
    for metric in ["noi", "irr", "equity_multiple", "dscr", "cash_on_cash"]:
        if metric in question:
            return metric
    return "noi"


def _severity_rank(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(value, 0)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value

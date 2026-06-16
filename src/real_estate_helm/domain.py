"""Core deal model.

The model intentionally keeps extracted facts, underwriting assumptions, and
scenario outputs as separate records. That mirrors the planning principle that
sponsor claims, analyst assumptions, and calculated results must not collapse
into one generic value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _new_id() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class DealStatus(StrEnum):
    NEW = "new"
    SCREENING = "screening"
    UNDERWRITING = "underwriting"
    INVESTMENT_COMMITTEE = "investment_committee"
    LOI = "loi"
    DILIGENCE = "diligence"
    ACQUIRED = "acquired"
    REJECTED = "rejected"
    WATCHLIST = "watchlist"


class FactReviewStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
    ASSUMPTION = "assumption"
    SPONSOR_CLAIM = "sponsor_claim"
    NEEDS_REEXTRACTION = "needs_reextraction"


class SourceKind(StrEnum):
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    MANUAL = "manual"
    WEB = "web"


class ScenarioType(StrEnum):
    SPONSOR_CASE = "sponsor_case"
    ANALYST_BASE_CASE = "analyst_base_case"
    DOWNSIDE_CASE = "downside_case"
    UPSIDE_CASE = "upside_case"
    INVESTMENT_COMMITTEE_CASE = "investment_committee_case"
    ACQUISITION_CASE = "acquisition_case"
    CURRENT_REFORECAST = "current_reforecast"
    ACTUALS = "actuals"


@dataclass(frozen=True)
class DocumentReference:
    source_kind: SourceKind
    name: str
    page: int | None = None
    sheet: str | None = None
    cell: str | None = None
    context: str | None = None


@dataclass(frozen=True)
class DealIdentity:
    name: str
    address: str | None = None
    parcel: str | None = None
    asset_type: str | None = None
    sponsor: str | None = None
    broker: str | None = None
    seller: str | None = None
    source: str | None = None
    owner: str | None = None


@dataclass
class ExtractedFact:
    field_name: str
    value: Any
    source: DocumentReference
    confidence: float
    id: str = field(default_factory=_new_id)
    status: FactReviewStatus = FactReviewStatus.PENDING
    extracted_at: datetime = field(default_factory=_now)
    reviewed_at: datetime | None = None
    reviewer: str | None = None
    review_note: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

    def review(
        self,
        status: FactReviewStatus,
        reviewer: str,
        *,
        note: str | None = None,
        corrected_value: Any | None = None,
        reviewed_at: datetime | None = None,
    ) -> None:
        self.status = status
        self.reviewer = reviewer
        self.review_note = note
        self.reviewed_at = reviewed_at or _now()
        if corrected_value is not None:
            self.value = corrected_value


@dataclass(frozen=True)
class Assumption:
    name: str
    value: Any
    rationale: str
    source_fact_id: str | None = None
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass
class Scenario:
    name: str
    scenario_type: ScenarioType
    id: str = field(default_factory=_new_id)
    assumptions: list[Assumption] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)

    def add_assumption(self, assumption: Assumption) -> None:
        self.assumptions.append(assumption)

    def set_output(self, metric_name: str, value: Any) -> None:
        self.outputs[metric_name] = value


@dataclass(frozen=True)
class DecisionEvent:
    from_status: DealStatus
    to_status: DealStatus
    actor: str
    reason: str
    occurred_at: datetime = field(default_factory=_now)


@dataclass
class Deal:
    identity: DealIdentity
    status: DealStatus = DealStatus.NEW
    id: str = field(default_factory=_new_id)
    received_at: datetime = field(default_factory=_now)
    extracted_facts: list[ExtractedFact] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    scenarios: list[Scenario] = field(default_factory=list)
    decision_history: list[DecisionEvent] = field(default_factory=list)

    def add_extracted_fact(self, fact: ExtractedFact) -> None:
        self.extracted_facts.append(fact)

    def review_fact(
        self,
        fact_id: str,
        status: FactReviewStatus,
        reviewer: str,
        *,
        note: str | None = None,
        corrected_value: Any | None = None,
        promote_to_assumption: bool = False,
        rationale: str | None = None,
    ) -> Assumption | None:
        fact = self._fact_by_id(fact_id)
        fact.review(status, reviewer, note=note, corrected_value=corrected_value)

        if promote_to_assumption:
            assumption = Assumption(
                name=fact.field_name,
                value=fact.value,
                rationale=rationale or note or "Promoted from reviewed extracted fact.",
                source_fact_id=fact.id,
            )
            self.assumptions.append(assumption)
            return assumption

        return None

    def add_scenario(self, scenario: Scenario) -> None:
        self.scenarios.append(scenario)

    def change_status(self, new_status: DealStatus, actor: str, reason: str) -> None:
        previous_status = self.status
        self.status = new_status
        self.decision_history.append(
            DecisionEvent(
                from_status=previous_status,
                to_status=new_status,
                actor=actor,
                reason=reason,
            )
        )

    def reject(self, actor: str, reason: str) -> None:
        self.change_status(DealStatus.REJECTED, actor, reason)

    def accepted_facts(self) -> list[ExtractedFact]:
        return [
            fact
            for fact in self.extracted_facts
            if fact.status in {FactReviewStatus.ACCEPTED, FactReviewStatus.EDITED}
        ]

    def _fact_by_id(self, fact_id: str) -> ExtractedFact:
        for fact in self.extracted_facts:
            if fact.id == fact_id:
                return fact
        raise ValueError(f"unknown extracted fact id: {fact_id}")

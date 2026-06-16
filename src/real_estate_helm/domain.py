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


class DocumentType(StrEnum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    WORD = "word"
    IMAGE = "image"
    ZIP = "zip"
    OTHER = "other"


class CashFlowType(StrEnum):
    PROJECTED = "projected"
    ACTUAL = "actual"


class MilestoneStatus(StrEnum):
    NOT_STARTED = "not_started"
    ON_TRACK = "on_track"
    DELAYED = "delayed"
    COMPLETE = "complete"


class AlertSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    OPEN = "open"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class NewsClassification(StrEnum):
    MATERIAL_POSITIVE = "material_positive"
    MATERIAL_NEGATIVE = "material_negative"
    WATCH = "watch"
    NOISE = "noise"
    DUPLICATE = "duplicate"


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELED = "canceled"


class UserRole(StrEnum):
    ADMIN = "admin"
    PORTFOLIO_MANAGER = "portfolio_manager"
    ANALYST = "analyst"
    PRINCIPAL = "principal"
    EXTERNAL_ADVISOR = "external_advisor"
    READ_ONLY_VIEWER = "read_only_viewer"


class ApprovalStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"


class NotificationChannel(StrEnum):
    ANDROID_PUSH = "android_push"
    DESKTOP = "desktop"
    EMAIL = "email"


class ObligationType(StrEnum):
    LEGAL_DEADLINE = "legal_deadline"
    DOCUMENT_EXPIRATION = "document_expiration"
    CAPITAL_CALL = "capital_call"


class LocationContextType(StrEnum):
    ROAD = "road"
    TRANSIT = "transit"
    SCHOOL = "school"
    HOSPITAL = "hospital"
    RETAIL_NODE = "retail_node"
    EMPLOYMENT_CENTER = "employment_center"
    INFRASTRUCTURE = "infrastructure"
    ENVIRONMENTAL_RISK = "environmental_risk"
    NEARBY_CONSTRUCTION = "nearby_construction"
    COMPETING_PROPERTY = "competing_property"
    OTHER = "other"


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


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Address:
    line1: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None


@dataclass
class Asset:
    name: str
    address: Address | None = None
    coordinates: Coordinates | None = None
    parcel_id: str | None = None
    asset_type: str | None = None
    unit_count: int | None = None
    building_size: float | None = None
    land_size: float | None = None
    year_built: int | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class UploadedDocument:
    name: str
    document_type: DocumentType
    storage_uri: str
    uploaded_by: str
    id: str = field(default_factory=_new_id)
    uploaded_at: datetime = field(default_factory=_now)
    sha256: str | None = None


@dataclass(frozen=True)
class DocumentPage:
    document_id: str
    page_number: int
    text_content: str | None = None
    image_uri: str | None = None
    extracted_tables: list[dict[str, Any]] = field(default_factory=list)
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class SpreadsheetCell:
    sheet: str
    cell: str
    value: Any
    formula: str | None = None
    mapped_field: str | None = None
    warning: str | None = None


@dataclass
class SpreadsheetModel:
    name: str
    document_id: str
    id: str = field(default_factory=_new_id)
    cells: list[SpreadsheetCell] = field(default_factory=list)


@dataclass(frozen=True)
class CashFlowRecord:
    period: str
    amount: Any
    cash_flow_type: CashFlowType
    category: str
    source: DocumentReference | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class DebtTerms:
    lender: str | None = None
    debt_amount: Any | None = None
    interest_rate: Any | None = None
    maturity_date: str | None = None
    amortization_years: int | None = None
    covenant_dscr: Any | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class Tenant:
    name: str
    credit_notes: str | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class Lease:
    tenant_id: str
    unit: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    annual_rent: Any | None = None
    renewal_probability: Any | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class RentRollEntry:
    as_of_date: str
    unit: str
    tenant_name: str | None = None
    monthly_rent: Any | None = None
    market_rent: Any | None = None
    occupied: bool = True
    concessions: Any | None = None
    bad_debt: Any | None = None
    lease_start: str | None = None
    lease_end: str | None = None
    source: DocumentReference | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class CapexItem:
    name: str
    budgeted_amount: Any
    actual_amount: Any | None = None
    category: str | None = None
    id: str = field(default_factory=_new_id)


@dataclass
class DevelopmentBudget:
    name: str
    hard_costs: Any = 0
    soft_costs: Any = 0
    contingency: Any = 0
    land_cost: Any = 0
    id: str = field(default_factory=_new_id)
    capex_items: list[CapexItem] = field(default_factory=list)


@dataclass(frozen=True)
class DevelopmentMilestone:
    name: str
    target_date: str
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    actual_date: str | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class MarketComp:
    name: str
    comp_type: str
    value: Any
    address: str | None = None
    distance_miles: float | None = None
    source: str | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class PropertyRecord:
    source: str
    parcel_id: str | None = None
    assessed_value: Any | None = None
    owner_name: str | None = None
    zoning: str | None = None
    flood_zone: str | None = None
    year_built: int | None = None
    building_size: float | None = None
    land_size: float | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class LocationContextItem:
    item_type: LocationContextType
    name: str
    distance_miles: float | None = None
    source: str | None = None
    notes: str | None = None
    coordinates: Coordinates | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class PermitEvent:
    permit_number: str
    permit_type: str
    status: str
    filed_date: str | None = None
    issued_date: str | None = None
    description: str | None = None
    source_url: str | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class WebSource:
    title: str
    url: str
    source_type: str
    retrieved_at: datetime = field(default_factory=_now)
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class NewsEvent:
    title: str
    url: str
    classification: NewsClassification
    published_at: str | None = None
    summary: str | None = None
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class ImagerySnapshot:
    captured_at: str
    storage_uri: str
    source: str
    notes: str | None = None
    id: str = field(default_factory=_new_id)


@dataclass
class Alert:
    title: str
    severity: AlertSeverity
    category: str
    source: str
    description: str
    financial_impact: Any | None = None
    recommended_action: str | None = None
    owner: str | None = None
    due_date: str | None = None
    status: AlertStatus = AlertStatus.OPEN
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)
    resolved_at: datetime | None = None

    def resolve(self) -> None:
        self.status = AlertStatus.RESOLVED
        self.resolved_at = _now()


@dataclass
class Task:
    title: str
    owner: str | None = None
    due_date: str | None = None
    status: TaskStatus = TaskStatus.OPEN
    id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class Obligation:
    title: str
    due_date: str
    obligation_type: ObligationType
    amount: Any | None = None
    source: str | None = None
    owner: str | None = None
    id: str = field(default_factory=_new_id)


@dataclass
class Comment:
    author: str
    body: str
    entity_type: str = "deal"
    entity_id: str | None = None
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)
    resolved_at: datetime | None = None

    def resolve(self) -> None:
        self.resolved_at = _now()


@dataclass
class ApprovalRequest:
    title: str
    requested_by: str
    approver: str
    entity_type: str = "deal"
    entity_id: str | None = None
    status: ApprovalStatus = ApprovalStatus.REQUESTED
    id: str = field(default_factory=_new_id)
    requested_at: datetime = field(default_factory=_now)
    decided_at: datetime | None = None
    decision_note: str | None = None

    def approve(self, note: str | None = None) -> None:
        self.status = ApprovalStatus.APPROVED
        self.decision_note = note
        self.decided_at = _now()

    def reject(self, note: str | None = None) -> None:
        self.status = ApprovalStatus.REJECTED
        self.decision_note = note
        self.decided_at = _now()


@dataclass(frozen=True)
class PushNotification:
    channel: NotificationChannel
    recipient: str
    title: str
    body: str
    entity_type: str = "deal"
    entity_id: str | None = None
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass(frozen=True)
class InvestmentDecision:
    recommendation: str
    actor: str
    rationale: str
    id: str = field(default_factory=_new_id)
    decided_at: datetime = field(default_factory=_now)


@dataclass(frozen=True)
class AuditLogEntry:
    actor: str
    action: str
    entity_type: str
    entity_id: str
    reason: str | None = None
    occurred_at: datetime = field(default_factory=_now)


@dataclass(frozen=True)
class User:
    email: str
    role: UserRole
    display_name: str | None = None
    id: str = field(default_factory=_new_id)


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
    assets: list[Asset] = field(default_factory=list)
    documents: list[UploadedDocument] = field(default_factory=list)
    document_pages: list[DocumentPage] = field(default_factory=list)
    spreadsheets: list[SpreadsheetModel] = field(default_factory=list)
    projected_cash_flows: list[CashFlowRecord] = field(default_factory=list)
    actual_cash_flows: list[CashFlowRecord] = field(default_factory=list)
    debt_terms: list[DebtTerms] = field(default_factory=list)
    tenants: list[Tenant] = field(default_factory=list)
    leases: list[Lease] = field(default_factory=list)
    rent_roll: list[RentRollEntry] = field(default_factory=list)
    capex_items: list[CapexItem] = field(default_factory=list)
    development_budgets: list[DevelopmentBudget] = field(default_factory=list)
    development_milestones: list[DevelopmentMilestone] = field(default_factory=list)
    market_comps: list[MarketComp] = field(default_factory=list)
    property_records: list[PropertyRecord] = field(default_factory=list)
    location_context: list[LocationContextItem] = field(default_factory=list)
    permit_events: list[PermitEvent] = field(default_factory=list)
    web_sources: list[WebSource] = field(default_factory=list)
    news_events: list[NewsEvent] = field(default_factory=list)
    imagery_snapshots: list[ImagerySnapshot] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    obligations: list[Obligation] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    approval_requests: list[ApprovalRequest] = field(default_factory=list)
    notifications: list[PushNotification] = field(default_factory=list)
    investment_decisions: list[InvestmentDecision] = field(default_factory=list)
    audit_log: list[AuditLogEntry] = field(default_factory=list)

    def add_extracted_fact(self, fact: ExtractedFact) -> None:
        self.extracted_facts.append(fact)

    def add_asset(self, asset: Asset) -> None:
        self.assets.append(asset)

    def add_document(self, document: UploadedDocument) -> None:
        self.documents.append(document)

    def add_alert(self, alert: Alert) -> None:
        self.alerts.append(alert)

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
        event = DecisionEvent(
            from_status=previous_status,
            to_status=new_status,
            actor=actor,
            reason=reason,
        )
        self.decision_history.append(event)
        self.audit_log.append(
            AuditLogEntry(
                actor=actor,
                action="change_status",
                entity_type="deal",
                entity_id=self.id,
                reason=reason,
                occurred_at=event.occurred_at,
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

    def open_alerts(self) -> list[Alert]:
        return [alert for alert in self.alerts if alert.status in {AlertStatus.OPEN, AlertStatus.ESCALATED}]

    def _fact_by_id(self, fact_id: str) -> ExtractedFact:
        for fact in self.extracted_facts:
            if fact.id == fact_id:
                return fact
        raise ValueError(f"unknown extracted fact id: {fact_id}")

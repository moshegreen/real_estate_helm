"""JSON-safe serialization for deal records."""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Callable

from real_estate_helm.domain import (
    Assumption,
    Address,
    Alert,
    AlertSeverity,
    AlertStatus,
    ApprovalRequest,
    ApprovalStatus,
    Asset,
    AuditLogEntry,
    CapexItem,
    CashFlowRecord,
    CashFlowType,
    Coordinates,
    Comment,
    Deal,
    DealIdentity,
    DealStatus,
    DecisionEvent,
    DebtTerms,
    DevelopmentBudget,
    DevelopmentMilestone,
    DocumentType,
    DocumentPage,
    DocumentReference,
    ExtractedFact,
    FactReviewStatus,
    ImagerySnapshot,
    InvestmentDecision,
    Lease,
    LocationContextItem,
    LocationContextType,
    MarketComp,
    MilestoneStatus,
    NewsClassification,
    NewsEvent,
    NotificationChannel,
    Obligation,
    ObligationType,
    PermitEvent,
    PropertyRecord,
    PushNotification,
    RentRollEntry,
    Scenario,
    ScenarioType,
    SourceKind,
    SpreadsheetCell,
    SpreadsheetModel,
    Task,
    TaskStatus,
    Tenant,
    UploadedDocument,
    WebSource,
)


def deal_to_dict(deal: Deal) -> dict[str, Any]:
    return {
        "id": deal.id,
        "identity": _identity_to_dict(deal.identity),
        "status": deal.status.value,
        "received_at": deal.received_at.isoformat(),
        "extracted_facts": [_fact_to_dict(fact) for fact in deal.extracted_facts],
        "assumptions": [_assumption_to_dict(assumption) for assumption in deal.assumptions],
        "scenarios": [_scenario_to_dict(scenario) for scenario in deal.scenarios],
        "decision_history": [_decision_to_dict(event) for event in deal.decision_history],
        "assets": [_asset_to_dict(asset) for asset in deal.assets],
        "documents": [_uploaded_document_to_dict(document) for document in deal.documents],
        "document_pages": [_simple_to_dict(page) for page in deal.document_pages],
        "spreadsheets": [_spreadsheet_model_to_dict(spreadsheet) for spreadsheet in deal.spreadsheets],
        "projected_cash_flows": [_cash_flow_to_dict(record) for record in deal.projected_cash_flows],
        "actual_cash_flows": [_cash_flow_to_dict(record) for record in deal.actual_cash_flows],
        "debt_terms": [_simple_to_dict(record) for record in deal.debt_terms],
        "tenants": [_simple_to_dict(record) for record in deal.tenants],
        "leases": [_simple_to_dict(record) for record in deal.leases],
        "rent_roll": [_rent_roll_to_dict(record) for record in deal.rent_roll],
        "capex_items": [_simple_to_dict(record) for record in deal.capex_items],
        "development_budgets": [_development_budget_to_dict(record) for record in deal.development_budgets],
        "development_milestones": [_simple_to_dict(record) for record in deal.development_milestones],
        "market_comps": [_simple_to_dict(record) for record in deal.market_comps],
        "property_records": [_simple_to_dict(record) for record in deal.property_records],
        "location_context": [_location_context_to_dict(record) for record in deal.location_context],
        "permit_events": [_simple_to_dict(record) for record in deal.permit_events],
        "web_sources": [_simple_to_dict(record) for record in deal.web_sources],
        "news_events": [_simple_to_dict(record) for record in deal.news_events],
        "imagery_snapshots": [_simple_to_dict(record) for record in deal.imagery_snapshots],
        "alerts": [_alert_to_dict(alert) for alert in deal.alerts],
        "tasks": [_simple_to_dict(task) for task in deal.tasks],
        "obligations": [_simple_to_dict(obligation) for obligation in deal.obligations],
        "comments": [_simple_to_dict(comment) for comment in deal.comments],
        "approval_requests": [_simple_to_dict(request) for request in deal.approval_requests],
        "notifications": [_simple_to_dict(notification) for notification in deal.notifications],
        "investment_decisions": [_simple_to_dict(decision) for decision in deal.investment_decisions],
        "audit_log": [_simple_to_dict(entry) for entry in deal.audit_log],
    }


def deal_from_dict(data: dict[str, Any]) -> Deal:
    return Deal(
        id=data["id"],
        identity=_identity_from_dict(data["identity"]),
        status=DealStatus(data["status"]),
        received_at=datetime.fromisoformat(data["received_at"]),
        extracted_facts=[_fact_from_dict(item) for item in data.get("extracted_facts", [])],
        assumptions=[_assumption_from_dict(item) for item in data.get("assumptions", [])],
        scenarios=[_scenario_from_dict(item) for item in data.get("scenarios", [])],
        decision_history=[_decision_from_dict(item) for item in data.get("decision_history", [])],
        assets=[_asset_from_dict(item) for item in data.get("assets", [])],
        documents=[_uploaded_document_from_dict(item) for item in data.get("documents", [])],
        document_pages=[_simple_from_dict(DocumentPage, item) for item in data.get("document_pages", [])],
        spreadsheets=[_spreadsheet_model_from_dict(item) for item in data.get("spreadsheets", [])],
        projected_cash_flows=[_cash_flow_from_dict(item) for item in data.get("projected_cash_flows", [])],
        actual_cash_flows=[_cash_flow_from_dict(item) for item in data.get("actual_cash_flows", [])],
        debt_terms=[_simple_from_dict(DebtTerms, item) for item in data.get("debt_terms", [])],
        tenants=[_simple_from_dict(Tenant, item) for item in data.get("tenants", [])],
        leases=[_simple_from_dict(Lease, item) for item in data.get("leases", [])],
        rent_roll=[_rent_roll_from_dict(item) for item in data.get("rent_roll", [])],
        capex_items=[_simple_from_dict(CapexItem, item) for item in data.get("capex_items", [])],
        development_budgets=[_development_budget_from_dict(item) for item in data.get("development_budgets", [])],
        development_milestones=[
            _simple_from_dict(DevelopmentMilestone, item, status=MilestoneStatus)
            for item in data.get("development_milestones", [])
        ],
        market_comps=[_simple_from_dict(MarketComp, item) for item in data.get("market_comps", [])],
        property_records=[_simple_from_dict(PropertyRecord, item) for item in data.get("property_records", [])],
        location_context=[_location_context_from_dict(item) for item in data.get("location_context", [])],
        permit_events=[_simple_from_dict(PermitEvent, item) for item in data.get("permit_events", [])],
        web_sources=[_simple_from_dict(WebSource, item) for item in data.get("web_sources", [])],
        news_events=[
            _simple_from_dict(NewsEvent, item, classification=NewsClassification)
            for item in data.get("news_events", [])
        ],
        imagery_snapshots=[
            _simple_from_dict(ImagerySnapshot, item) for item in data.get("imagery_snapshots", [])
        ],
        alerts=[_alert_from_dict(item) for item in data.get("alerts", [])],
        tasks=[_simple_from_dict(Task, item, status=TaskStatus) for item in data.get("tasks", [])],
        obligations=[
            _simple_from_dict(Obligation, item, obligation_type=ObligationType)
            for item in data.get("obligations", [])
        ],
        comments=[_simple_from_dict(Comment, item) for item in data.get("comments", [])],
        approval_requests=[
            _simple_from_dict(ApprovalRequest, item, status=ApprovalStatus)
            for item in data.get("approval_requests", [])
        ],
        notifications=[
            _simple_from_dict(PushNotification, item, channel=NotificationChannel)
            for item in data.get("notifications", [])
        ],
        investment_decisions=[
            _simple_from_dict(InvestmentDecision, item) for item in data.get("investment_decisions", [])
        ],
        audit_log=[_simple_from_dict(AuditLogEntry, item) for item in data.get("audit_log", [])],
    )


def _identity_to_dict(identity: DealIdentity) -> dict[str, Any]:
    return {
        "name": identity.name,
        "address": identity.address,
        "parcel": identity.parcel,
        "asset_type": identity.asset_type,
        "sponsor": identity.sponsor,
        "broker": identity.broker,
        "seller": identity.seller,
        "source": identity.source,
        "owner": identity.owner,
    }


def _identity_from_dict(data: dict[str, Any]) -> DealIdentity:
    return DealIdentity(**data)


def _document_reference_to_dict(reference: DocumentReference) -> dict[str, Any]:
    return {
        "source_kind": reference.source_kind.value,
        "name": reference.name,
        "page": reference.page,
        "sheet": reference.sheet,
        "cell": reference.cell,
        "context": reference.context,
    }


def _document_reference_from_dict(data: dict[str, Any]) -> DocumentReference:
    return DocumentReference(
        source_kind=SourceKind(data["source_kind"]),
        name=data["name"],
        page=data.get("page"),
        sheet=data.get("sheet"),
        cell=data.get("cell"),
        context=data.get("context"),
    )


def _fact_to_dict(fact: ExtractedFact) -> dict[str, Any]:
    return {
        "id": fact.id,
        "field_name": fact.field_name,
        "value": _encode_value(fact.value),
        "source": _document_reference_to_dict(fact.source),
        "confidence": fact.confidence,
        "status": fact.status.value,
        "extracted_at": fact.extracted_at.isoformat(),
        "reviewed_at": fact.reviewed_at.isoformat() if fact.reviewed_at else None,
        "reviewer": fact.reviewer,
        "review_note": fact.review_note,
    }


def _fact_from_dict(data: dict[str, Any]) -> ExtractedFact:
    return ExtractedFact(
        id=data["id"],
        field_name=data["field_name"],
        value=_decode_value(data["value"]),
        source=_document_reference_from_dict(data["source"]),
        confidence=data["confidence"],
        status=FactReviewStatus(data["status"]),
        extracted_at=datetime.fromisoformat(data["extracted_at"]),
        reviewed_at=datetime.fromisoformat(data["reviewed_at"]) if data.get("reviewed_at") else None,
        reviewer=data.get("reviewer"),
        review_note=data.get("review_note"),
    )


def _assumption_to_dict(assumption: Assumption) -> dict[str, Any]:
    return {
        "id": assumption.id,
        "name": assumption.name,
        "value": _encode_value(assumption.value),
        "rationale": assumption.rationale,
        "source_fact_id": assumption.source_fact_id,
        "created_at": assumption.created_at.isoformat(),
    }


def _assumption_from_dict(data: dict[str, Any]) -> Assumption:
    return Assumption(
        id=data["id"],
        name=data["name"],
        value=_decode_value(data["value"]),
        rationale=data["rationale"],
        source_fact_id=data.get("source_fact_id"),
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def _scenario_to_dict(scenario: Scenario) -> dict[str, Any]:
    return {
        "id": scenario.id,
        "name": scenario.name,
        "scenario_type": scenario.scenario_type.value,
        "assumptions": [_assumption_to_dict(assumption) for assumption in scenario.assumptions],
        "outputs": _encode_value(scenario.outputs),
    }


def _scenario_from_dict(data: dict[str, Any]) -> Scenario:
    return Scenario(
        id=data["id"],
        name=data["name"],
        scenario_type=ScenarioType(data["scenario_type"]),
        assumptions=[_assumption_from_dict(item) for item in data.get("assumptions", [])],
        outputs=_decode_value(data.get("outputs", {})),
    )


def _decision_to_dict(event: DecisionEvent) -> dict[str, Any]:
    return {
        "from_status": event.from_status.value,
        "to_status": event.to_status.value,
        "actor": event.actor,
        "reason": event.reason,
        "occurred_at": event.occurred_at.isoformat(),
    }


def _decision_from_dict(data: dict[str, Any]) -> DecisionEvent:
    return DecisionEvent(
        from_status=DealStatus(data["from_status"]),
        to_status=DealStatus(data["to_status"]),
        actor=data["actor"],
        reason=data["reason"],
        occurred_at=datetime.fromisoformat(data["occurred_at"]),
    )


def _asset_to_dict(asset: Asset) -> dict[str, Any]:
    data = _simple_to_dict(asset)
    data["address"] = _simple_to_dict(asset.address) if asset.address else None
    data["coordinates"] = _simple_to_dict(asset.coordinates) if asset.coordinates else None
    return data


def _asset_from_dict(data: dict[str, Any]) -> Asset:
    return Asset(
        id=data["id"],
        name=data["name"],
        address=_simple_from_dict(Address, data["address"]) if data.get("address") else None,
        coordinates=_simple_from_dict(Coordinates, data["coordinates"]) if data.get("coordinates") else None,
        parcel_id=data.get("parcel_id"),
        asset_type=data.get("asset_type"),
        unit_count=data.get("unit_count"),
        building_size=data.get("building_size"),
        land_size=data.get("land_size"),
        year_built=data.get("year_built"),
    )


def _uploaded_document_to_dict(document: UploadedDocument) -> dict[str, Any]:
    return _simple_to_dict(document)


def _uploaded_document_from_dict(data: dict[str, Any]) -> UploadedDocument:
    return _simple_from_dict(UploadedDocument, data, document_type=DocumentType)


def _location_context_to_dict(item: LocationContextItem) -> dict[str, Any]:
    data = _simple_to_dict(item)
    data["coordinates"] = _simple_to_dict(item.coordinates) if item.coordinates else None
    return data


def _location_context_from_dict(data: dict[str, Any]) -> LocationContextItem:
    return LocationContextItem(
        id=data["id"],
        item_type=LocationContextType(data["item_type"]),
        name=data["name"],
        distance_miles=data.get("distance_miles"),
        source=data.get("source"),
        notes=data.get("notes"),
        coordinates=_simple_from_dict(Coordinates, data["coordinates"]) if data.get("coordinates") else None,
    )


def _spreadsheet_model_to_dict(spreadsheet: SpreadsheetModel) -> dict[str, Any]:
    data = _simple_to_dict(spreadsheet)
    data["cells"] = [_simple_to_dict(cell) for cell in spreadsheet.cells]
    return data


def _spreadsheet_model_from_dict(data: dict[str, Any]) -> SpreadsheetModel:
    return SpreadsheetModel(
        id=data["id"],
        name=data["name"],
        document_id=data["document_id"],
        cells=[_simple_from_dict(SpreadsheetCell, item) for item in data.get("cells", [])],
    )


def _cash_flow_to_dict(record: CashFlowRecord) -> dict[str, Any]:
    data = _simple_to_dict(record)
    data["source"] = _document_reference_to_dict(record.source) if record.source else None
    return data


def _cash_flow_from_dict(data: dict[str, Any]) -> CashFlowRecord:
    return CashFlowRecord(
        id=data["id"],
        period=data["period"],
        amount=_decode_value(data["amount"]),
        cash_flow_type=CashFlowType(data["cash_flow_type"]),
        category=data["category"],
        source=_document_reference_from_dict(data["source"]) if data.get("source") else None,
    )


def _rent_roll_to_dict(record: RentRollEntry) -> dict[str, Any]:
    data = _simple_to_dict(record)
    data["source"] = _document_reference_to_dict(record.source) if record.source else None
    return data


def _rent_roll_from_dict(data: dict[str, Any]) -> RentRollEntry:
    return RentRollEntry(
        id=data["id"],
        as_of_date=data["as_of_date"],
        unit=data["unit"],
        tenant_name=data.get("tenant_name"),
        monthly_rent=_decode_value(data.get("monthly_rent")),
        market_rent=_decode_value(data.get("market_rent")),
        occupied=bool(data.get("occupied", True)),
        concessions=_decode_value(data.get("concessions")),
        bad_debt=_decode_value(data.get("bad_debt")),
        lease_start=data.get("lease_start"),
        lease_end=data.get("lease_end"),
        source=_document_reference_from_dict(data["source"]) if data.get("source") else None,
    )


def _development_budget_to_dict(budget: DevelopmentBudget) -> dict[str, Any]:
    data = _simple_to_dict(budget)
    data["capex_items"] = [_simple_to_dict(item) for item in budget.capex_items]
    return data


def _development_budget_from_dict(data: dict[str, Any]) -> DevelopmentBudget:
    return DevelopmentBudget(
        id=data["id"],
        name=data["name"],
        hard_costs=_decode_value(data.get("hard_costs", 0)),
        soft_costs=_decode_value(data.get("soft_costs", 0)),
        contingency=_decode_value(data.get("contingency", 0)),
        land_cost=_decode_value(data.get("land_cost", 0)),
        capex_items=[_simple_from_dict(CapexItem, item) for item in data.get("capex_items", [])],
    )


def _alert_to_dict(alert: Alert) -> dict[str, Any]:
    return _simple_to_dict(alert)


def _alert_from_dict(data: dict[str, Any]) -> Alert:
    return _simple_from_dict(Alert, data, severity=AlertSeverity, status=AlertStatus)


def _simple_to_dict(record: Any) -> dict[str, Any]:
    return {item.name: _encode_value(getattr(record, item.name)) for item in fields(record)}


def _simple_from_dict(record_type: Callable[..., Any], data: dict[str, Any], **enum_fields: Any) -> Any:
    values = {}
    for item in fields(record_type):
        value = data.get(item.name)
        if item.name in enum_fields and value is not None:
            values[item.name] = enum_fields[item.name](value)
        else:
            values[item.name] = _decode_value(value)
    return record_type(**values)


def _encode_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return {"__type__": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, list):
        return [_encode_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _encode_value(item) for key, item in value.items()}
    return value


def _decode_value(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode_value(item) for item in value]
    if isinstance(value, dict):
        value_type = value.get("__type__")
        if value_type == "decimal":
            return Decimal(value["value"])
        if value_type == "datetime":
            return datetime.fromisoformat(value["value"])
        return {key: _decode_value(item) for key, item in value.items()}
    return value

"""JSON-safe serialization for deal records."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from real_estate_helm.domain import (
    Assumption,
    Deal,
    DealIdentity,
    DealStatus,
    DecisionEvent,
    DocumentReference,
    ExtractedFact,
    FactReviewStatus,
    Scenario,
    ScenarioType,
    SourceKind,
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


def _encode_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return {"__type__": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}
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

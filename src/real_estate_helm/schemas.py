"""Request validation models for API and client payloads."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from real_estate_helm.domain import CashFlowType, DealStatus, DocumentType, FactReviewStatus, SourceKind


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CreateDealRequest:
    name: str
    address: str | None = None
    asset_type: str | None = None
    sponsor: str | None = None
    broker: str | None = None
    owner: str | None = None

    @classmethod
    def parse(cls, payload: dict[str, Any]) -> "CreateDealRequest":
        return cls(name=_required_str(payload, "name"), **_optional_strings(payload, ["address", "asset_type", "sponsor", "broker", "owner"]))


@dataclass(frozen=True)
class ChangeStatusRequest:
    status: DealStatus
    actor: str
    reason: str

    @classmethod
    def parse(cls, payload: dict[str, Any]) -> "ChangeStatusRequest":
        return cls(
            status=DealStatus(_required_str(payload, "status")),
            actor=_required_str(payload, "actor"),
            reason=_required_str(payload, "reason"),
        )


@dataclass(frozen=True)
class AddFactRequest:
    field_name: str
    value: Any
    confidence: float
    source_name: str
    source_kind: SourceKind
    page: int | None = None
    sheet: str | None = None
    cell: str | None = None
    context: str | None = None

    @classmethod
    def parse(cls, payload: dict[str, Any]) -> "AddFactRequest":
        confidence = float(payload.get("confidence"))
        if not 0 <= confidence <= 1:
            raise ValidationError("confidence must be between 0 and 1")
        return cls(
            field_name=_required_str(payload, "field_name"),
            value=payload.get("value"),
            confidence=confidence,
            source_name=_required_str(payload, "source_name"),
            source_kind=SourceKind(payload.get("source_kind", SourceKind.MANUAL.value)),
            page=payload.get("page"),
            sheet=payload.get("sheet"),
            cell=payload.get("cell"),
            context=payload.get("context"),
        )


@dataclass(frozen=True)
class ReviewFactRequest:
    fact_id: str
    status: FactReviewStatus
    reviewer: str
    note: str | None = None
    corrected_value: Any | None = None
    promote_to_assumption: bool = False
    rationale: str | None = None

    @classmethod
    def parse(cls, payload: dict[str, Any]) -> "ReviewFactRequest":
        return cls(
            fact_id=_required_str(payload, "fact_id"),
            status=FactReviewStatus(_required_str(payload, "status")),
            reviewer=_required_str(payload, "reviewer"),
            note=payload.get("note"),
            corrected_value=payload.get("corrected_value"),
            promote_to_assumption=bool(payload.get("promote_to_assumption", False)),
            rationale=payload.get("rationale"),
        )


@dataclass(frozen=True)
class AddDocumentRequest:
    name: str
    document_type: DocumentType
    storage_uri: str
    uploaded_by: str
    sha256: str | None = None

    @classmethod
    def parse(cls, payload: dict[str, Any]) -> "AddDocumentRequest":
        return cls(
            name=_required_str(payload, "name"),
            document_type=DocumentType(_required_str(payload, "document_type")),
            storage_uri=_required_str(payload, "storage_uri"),
            uploaded_by=_required_str(payload, "uploaded_by"),
            sha256=payload.get("sha256"),
        )


@dataclass(frozen=True)
class AddCashFlowRequest:
    period: str
    amount: Decimal
    cash_flow_type: CashFlowType
    category: str

    @classmethod
    def parse(cls, payload: dict[str, Any]) -> "AddCashFlowRequest":
        return cls(
            period=_required_str(payload, "period"),
            amount=Decimal(str(payload["amount"])),
            cash_flow_type=CashFlowType(_required_str(payload, "cash_flow_type")),
            category=_required_str(payload, "category"),
        )


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} is required")
    return value


def _optional_strings(payload: dict[str, Any], keys: list[str]) -> dict[str, str | None]:
    return {key: payload.get(key) if isinstance(payload.get(key), str) and payload.get(key) else None for key in keys}

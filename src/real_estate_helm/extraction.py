"""Document and spreadsheet extraction workflows.

This module provides deterministic plumbing around extraction proposals. AI or
OCR providers can supply proposed fields later, but this layer is responsible
for preserving source references and keeping human review mandatory.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from real_estate_helm.domain import (
    Assumption,
    DocumentReference,
    ExtractedFact,
    FactReviewStatus,
    SourceKind,
    SpreadsheetCell,
    SpreadsheetModel,
)
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.underwriting import variance, variance_percent


@dataclass(frozen=True)
class ExtractionProposal:
    field_name: str
    value: Any
    confidence: float
    source: DocumentReference


@dataclass(frozen=True)
class DocumentSummary:
    title: str
    summary: str
    risks: list[str]
    source: DocumentReference


@dataclass(frozen=True)
class SpreadsheetComparisonRow:
    mapped_field: str
    sheet: str
    cell: str
    spreadsheet_value: Any
    canonical_value: Any
    delta: Any
    delta_percent: Any | None
    warning: str | None = None


class DocumentExtractionProvider(Protocol):
    def extract(self, document_name: str, content: bytes) -> list[ExtractionProposal]:
        """Return proposed facts from document bytes."""


class DocumentSummaryProvider(Protocol):
    def summarize(self, document_name: str, content: bytes) -> DocumentSummary:
        """Return a human-readable document summary and risks."""


@dataclass(frozen=True)
class StaticDocumentExtractionProvider:
    proposals: list[ExtractionProposal]

    def extract(self, document_name: str, content: bytes) -> list[ExtractionProposal]:
        return list(self.proposals)


@dataclass(frozen=True)
class StaticDocumentSummaryProvider:
    summary: DocumentSummary

    def summarize(self, document_name: str, content: bytes) -> DocumentSummary:
        return self.summary


class HttpJsonDocumentExtractionProvider:
    def __init__(self, endpoint: str, *, api_key: str | None = None, fetcher: Any) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.fetcher = fetcher

    def extract(self, document_name: str, content: bytes) -> list[ExtractionProposal]:
        payload = {
            "document_name": document_name,
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
        response = self.fetcher(self.endpoint, _auth_headers(self.api_key), payload)
        proposals = [_proposal_from_payload(document_name, item) for item in response.get("proposals", [])]
        return calibrate_proposals(
            proposals,
            provider_reliability=float(response.get("provider_reliability", 1.0)),
        )


class HttpJsonDocumentSummaryProvider:
    def __init__(self, endpoint: str, *, api_key: str | None = None, fetcher: Any) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.fetcher = fetcher

    def summarize(self, document_name: str, content: bytes) -> DocumentSummary:
        payload = {
            "document_name": document_name,
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
        response = self.fetcher(self.endpoint, _auth_headers(self.api_key), payload)
        source = response.get("source", {})
        return DocumentSummary(
            title=response["title"],
            summary=response["summary"],
            risks=list(response.get("risks", [])),
            source=DocumentReference(
                source_kind=SourceKind.DOCUMENT,
                name=source.get("name", document_name),
                page=source.get("page"),
                context=source.get("context"),
            ),
        )


def calibrate_proposals(
    proposals: list[ExtractionProposal],
    *,
    provider_reliability: float = 1.0,
    source_bonus: float = 0.05,
    missing_source_penalty: float = 0.15,
) -> list[ExtractionProposal]:
    calibrated = []
    for proposal in proposals:
        source_quality = source_bonus if _has_precise_source(proposal.source) else -missing_source_penalty
        confidence = round(_clamp((proposal.confidence * provider_reliability) + source_quality), 4)
        calibrated.append(
            ExtractionProposal(
                field_name=proposal.field_name,
                value=proposal.value,
                confidence=confidence,
                source=proposal.source,
            )
        )
    return calibrated


class ExtractionService:
    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository

    def add_proposals(self, deal_id: str, proposals: list[ExtractionProposal]) -> int:
        deal = self.repository.get(deal_id)
        for proposal in proposals:
            deal.extracted_facts.append(
                ExtractedFact(
                    field_name=proposal.field_name,
                    value=proposal.value,
                    confidence=proposal.confidence,
                    source=proposal.source,
                )
            )
        self.repository.save(deal)
        return len(proposals)

    def map_reviewed_facts_to_assumptions(self, deal_id: str, *, reviewer: str, rationale: str) -> int:
        deal = self.repository.get(deal_id)
        count = 0
        for fact in list(deal.extracted_facts):
            if fact.status in {FactReviewStatus.ACCEPTED, FactReviewStatus.EDITED}:
                deal.review_fact(
                    fact.id,
                    FactReviewStatus.ASSUMPTION,
                    reviewer,
                    note="Mapped to canonical assumption.",
                    promote_to_assumption=True,
                    rationale=rationale,
                )
                count += 1
        self.repository.save(deal)
        return count

    def extract_document(
        self,
        deal_id: str,
        *,
        document_name: str,
        content: bytes,
        provider: DocumentExtractionProvider,
    ) -> int:
        return self.add_proposals(deal_id, provider.extract(document_name, content))


def interpret_spreadsheet_cells(name: str, document_id: str, rows: list[dict[str, Any]]) -> SpreadsheetModel:
    cells = []
    for row in rows:
        value = row.get("value")
        formula = row.get("formula")
        warning = None
        if isinstance(formula, str) and formula.startswith("#"):
            warning = "broken_formula"
        elif isinstance(formula, str) and formula and not formula.startswith("="):
            warning = "formula_missing_equals"
        cells.append(
            SpreadsheetCell(
                sheet=row["sheet"],
                cell=row["cell"],
                value=value,
                formula=formula,
                mapped_field=row.get("mapped_field"),
                warning=warning,
            )
        )
    return SpreadsheetModel(name=name, document_id=document_id, cells=cells)


def proposals_from_spreadsheet(model: SpreadsheetModel) -> list[ExtractionProposal]:
    proposals = []
    for cell in model.cells:
        if cell.mapped_field is None:
            continue
        confidence = 0.5 if cell.warning else 0.8
        proposals.append(
            ExtractionProposal(
                field_name=cell.mapped_field,
                value=cell.value,
                confidence=confidence,
                source=DocumentReference(
                    source_kind=SourceKind.SPREADSHEET,
                    name=model.name,
                    sheet=cell.sheet,
                    cell=cell.cell,
                    context=cell.formula,
                ),
            )
        )
    return proposals


def compare_spreadsheet_to_canonical(
    model: SpreadsheetModel,
    assumptions: list[Assumption],
) -> list[SpreadsheetComparisonRow]:
    canonical = {assumption.name: assumption.value for assumption in assumptions}
    rows = []
    for cell in model.cells:
        if cell.mapped_field is None:
            continue
        canonical_value = canonical.get(cell.mapped_field)
        delta = None
        delta_percent = None
        if _is_number(cell.value) and _is_number(canonical_value):
            delta = variance(cell.value, canonical_value)
            delta_percent = variance_percent(cell.value, canonical_value) if Decimal(str(canonical_value)) != 0 else None
        rows.append(
            SpreadsheetComparisonRow(
                mapped_field=cell.mapped_field,
                sheet=cell.sheet,
                cell=cell.cell,
                spreadsheet_value=cell.value,
                canonical_value=canonical_value,
                delta=delta,
                delta_percent=delta_percent,
                warning=cell.warning or ("missing_canonical_value" if canonical_value is None else None),
            )
        )
    return rows


def _proposal_from_payload(document_name: str, payload: dict[str, Any]) -> ExtractionProposal:
    source = payload.get("source", {})
    return ExtractionProposal(
        field_name=payload["field_name"],
        value=payload.get("value"),
        confidence=float(payload.get("confidence", 0)),
        source=DocumentReference(
            source_kind=SourceKind.DOCUMENT,
            name=source.get("name", document_name),
            page=source.get("page"),
            sheet=source.get("sheet"),
            cell=source.get("cell"),
            context=source.get("context"),
        ),
    )


def _auth_headers(api_key: str | None) -> dict[str, str]:
    headers = {"content-type": "application/json"}
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    return headers


def _has_precise_source(source: DocumentReference) -> bool:
    return bool(source.page or (source.sheet and source.cell) or source.context)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 0.99) -> float:
    return max(minimum, min(maximum, value))


def _is_number(value: Any) -> bool:
    if value is None:
        return False
    try:
        Decimal(str(value))
    except Exception:
        return False
    return True

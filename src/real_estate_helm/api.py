"""Small JSON API router for early desktop/mobile integration tests."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any

from real_estate_helm.analytics import portfolio_dashboard_metrics, rejected_deal_hindsight
from real_estate_helm.cash_flow_import import CashFlowImportService
from real_estate_helm.collaboration import CollaborationService
from real_estate_helm.crm_import import CrmImportService
from real_estate_helm.data_room import DataRoomImportService
from real_estate_helm.email_import import EmailDealImportService
from real_estate_helm.domain import CashFlowType, Coordinates, DealStatus, DocumentReference, ObligationType, SourceKind
from real_estate_helm.intake import IntakeService
from real_estate_helm.monitoring import add_new_alerts, monitoring_alerts
from real_estate_helm.obligation_import import ObligationImportService
from real_estate_helm.portfolio_qa import PortfolioQuestionAnswerer
from real_estate_helm.reporting import (
    generate_asset_monitoring_report_markdown,
    generate_development_progress_report_markdown,
    generate_ic_memo_markdown,
    generate_lender_covenant_report_markdown,
    generate_monthly_performance_report_markdown,
)
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.serialization import deal_to_dict
from real_estate_helm.services import DealService
from real_estate_helm.storage import LocalObjectStorage
from real_estate_helm.schemas import (
    AddCashFlowRequest,
    AddDocumentRequest,
    AddFactRequest,
    ChangeStatusRequest,
    CreateDealRequest,
    ReviewFactRequest,
    ValidationError,
)


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: dict[str, Any] | list[Any]

    def to_json(self) -> str:
        return json.dumps(_json_safe(self.body), indent=2, sort_keys=True)


class ApiRouter:
    """Dependency-free route handler for the first backend contract."""

    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository
        self.service = DealService(repository)
        self.intake = IntakeService(repository)
        self.collaboration = CollaborationService(repository)

    def handle(self, method: str, path: str, body: dict[str, Any] | None = None) -> ApiResponse:
        try:
            return self._handle(method, path, body)
        except ValidationError as exc:
            return ApiResponse(422, {"error": "validation_error", "detail": str(exc)})

    def _handle(self, method: str, path: str, body: dict[str, Any] | None = None) -> ApiResponse:
        segments = [segment for segment in path.strip("/").split("/") if segment]
        body = body or {}

        if method == "GET" and segments == ["health"]:
            return ApiResponse(200, {"status": "ok"})

        if method == "GET" and segments == ["deals"]:
            return ApiResponse(200, [deal_to_dict(deal) for deal in self.repository.list()])

        if method == "GET" and segments == ["portfolio", "summary"]:
            return ApiResponse(200, _json_safe(portfolio_dashboard_metrics(self.repository.list())))

        if method == "GET" and segments == ["portfolio", "rejected-hindsight"]:
            return ApiResponse(200, rejected_deal_hindsight(self.repository.list()))

        if method == "POST" and segments == ["portfolio", "questions"]:
            question = body.get("question")
            if not question:
                return ApiResponse(422, {"error": "validation_error", "detail": "question is required"})
            answer = PortfolioQuestionAnswerer().answer(self.repository.list(), str(question))
            return ApiResponse(200, answer.to_dict())

        if method == "POST" and segments == ["deals"]:
            request = CreateDealRequest.parse(body)
            deal = self.service.create_deal(
                request.name,
                address=request.address,
                asset_type=request.asset_type,
                sponsor=request.sponsor,
                broker=request.broker,
                owner=request.owner,
            )
            return ApiResponse(201, deal_to_dict(deal))

        if method == "POST" and segments == ["emails", "import"]:
            if not body.get("content_base64") or not body.get("uploaded_by"):
                return ApiResponse(422, {"error": "validation_error", "detail": "content_base64 and uploaded_by are required"})
            email_bytes = base64.b64decode(body["content_base64"])
            storage = LocalObjectStorage(self.repository.root / "objects")
            result = EmailDealImportService(self.repository, storage).create_deal_from_email(
                email_bytes,
                uploaded_by=body["uploaded_by"],
                owner=body.get("owner"),
            )
            return ApiResponse(
                201,
                {
                    "deal_id": result.deal_id,
                    "subject": result.subject,
                    "sender": result.sender,
                    "attachments_imported": result.attachments_imported,
                    "deal": deal_to_dict(self.repository.get(result.deal_id)),
                },
            )

        if method == "POST" and segments == ["crm", "import"]:
            if not body.get("content_base64"):
                return ApiResponse(422, {"error": "validation_error", "detail": "content_base64 is required"})
            csv_text = base64.b64decode(body["content_base64"]).decode("utf-8-sig")
            result = CrmImportService(self.repository).import_csv(
                csv_text,
                default_owner=body.get("default_owner"),
            )
            return ApiResponse(
                201,
                {
                    "imported_rows": result.imported_rows,
                    "skipped_rows": result.skipped_rows,
                    "deal_ids": result.deal_ids,
                    "deals": [deal_to_dict(self.repository.get(deal_id)) for deal_id in result.deal_ids],
                },
            )

        if len(segments) >= 2 and segments[0] == "deals":
            deal_id = segments[1]
            if method == "GET" and len(segments) == 2:
                return ApiResponse(200, deal_to_dict(self.repository.get(deal_id)))
            if method == "POST" and segments[2:] == ["status"]:
                request = ChangeStatusRequest.parse(body)
                deal = self.service.change_status(
                    deal_id,
                    request.status,
                    request.actor,
                    request.reason,
                )
                return ApiResponse(200, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["reject"]:
                deal = self.service.reject_deal(deal_id, body["actor"], body["reason"])
                return ApiResponse(200, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["facts"]:
                request = AddFactRequest.parse(body)
                deal = self.service.add_extracted_fact(
                    deal_id,
                    field_name=request.field_name,
                    value=request.value,
                    confidence=request.confidence,
                    source=DocumentReference(
                        source_kind=request.source_kind,
                        name=request.source_name,
                        page=request.page,
                        sheet=request.sheet,
                        cell=request.cell,
                        context=request.context,
                    ),
                )
                return ApiResponse(201, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["review-fact"]:
                request = ReviewFactRequest.parse(body)
                deal = self.service.review_fact(
                    deal_id,
                    request.fact_id,
                    request.status,
                    request.reviewer,
                    note=request.note,
                    corrected_value=request.corrected_value,
                    promote_to_assumption=request.promote_to_assumption,
                    rationale=request.rationale,
                )
                return ApiResponse(200, deal_to_dict(deal))
            if method == "POST" and len(segments) == 5 and segments[2] == "facts" and segments[4] == "reextraction":
                if not body.get("reviewer"):
                    return ApiResponse(422, {"error": "validation_error", "detail": "reviewer is required"})
                deal = self.service.request_fact_reextraction(
                    deal_id,
                    segments[3],
                    reviewer=body["reviewer"],
                    note=body.get("note"),
                    owner=body.get("owner"),
                    due_date=body.get("due_date"),
                )
                return ApiResponse(200, deal_to_dict(deal))
            if method == "POST" and len(segments) == 5 and segments[2] == "scenarios" and segments[4] == "assumptions":
                deal = self.service.update_scenario_assumption(
                    deal_id,
                    segments[3],
                    name=body["name"],
                    value=body.get("value"),
                    actor=body["actor"],
                    rationale=body["rationale"],
                    source_fact_id=body.get("source_fact_id"),
                    revised_outputs=body.get("revised_outputs"),
                )
                return ApiResponse(200, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["assets"]:
                coordinates = None
                if body.get("latitude") is not None and body.get("longitude") is not None:
                    coordinates = Coordinates(float(body["latitude"]), float(body["longitude"]))
                deal = self.intake.add_asset(
                    deal_id,
                    body["name"],
                    asset_type=body.get("asset_type"),
                    unit_count=body.get("unit_count"),
                    coordinates=coordinates,
                )
                return ApiResponse(201, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["documents"]:
                request = AddDocumentRequest.parse(body)
                deal = self.intake.add_document(
                    deal_id,
                    name=request.name,
                    document_type=request.document_type,
                    storage_uri=request.storage_uri,
                    uploaded_by=request.uploaded_by,
                    sha256=request.sha256,
                )
                return ApiResponse(201, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["document-pages"]:
                deal = self.intake.add_document_page(
                    deal_id,
                    document_id=body["document_id"],
                    page_number=int(body["page_number"]),
                    text_content=body.get("text_content"),
                    image_uri=body.get("image_uri"),
                    extracted_tables=body.get("extracted_tables", []),
                )
                return ApiResponse(201, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["imagery"]:
                required = {"content_base64", "filename", "captured_at", "source"}
                if missing := sorted(name for name in required if not body.get(name)):
                    return ApiResponse(422, {"error": "validation_error", "detail": f"{', '.join(missing)} are required"})
                filename = _safe_filename(str(body["filename"]))
                storage = LocalObjectStorage(self.repository.root / "objects")
                stored = storage.put_bytes(
                    f"deals/{deal_id}/imagery/{filename}",
                    base64.b64decode(body["content_base64"]),
                )
                deal = self.intake.add_imagery_snapshot(
                    deal_id,
                    captured_at=str(body["captured_at"]),
                    storage_uri=stored.uri,
                    source=str(body["source"]),
                    notes=body.get("notes"),
                )
                return ApiResponse(201, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["data-room"]:
                if not body.get("content_base64") or not body.get("uploaded_by"):
                    return ApiResponse(422, {"error": "validation_error", "detail": "content_base64 and uploaded_by are required"})
                archive_bytes = base64.b64decode(body["content_base64"])
                storage = LocalObjectStorage(self.repository.root / "objects")
                result = DataRoomImportService(self.repository, storage).import_zip(
                    deal_id,
                    archive_bytes,
                    uploaded_by=body["uploaded_by"],
                    key_prefix=body.get("key_prefix"),
                )
                return ApiResponse(
                    201,
                    {
                        "documents_imported": result.documents_imported,
                        "skipped_entries": result.skipped_entries,
                        "deal": deal_to_dict(self.repository.get(deal_id)),
                    },
                )
            if method == "POST" and segments[2:] == ["data-room-folder"]:
                if not body.get("folder_path") or not body.get("uploaded_by"):
                    return ApiResponse(422, {"error": "validation_error", "detail": "folder_path and uploaded_by are required"})
                storage = LocalObjectStorage(self.repository.root / "objects")
                result = DataRoomImportService(self.repository, storage).import_directory(
                    deal_id,
                    body["folder_path"],
                    uploaded_by=body["uploaded_by"],
                    key_prefix=body.get("key_prefix"),
                )
                return ApiResponse(
                    201,
                    {
                        "documents_imported": result.documents_imported,
                        "skipped_entries": result.skipped_entries,
                        "deal": deal_to_dict(self.repository.get(deal_id)),
                    },
                )
            if method == "POST" and segments[2:] == ["email"]:
                if not body.get("content_base64") or not body.get("uploaded_by"):
                    return ApiResponse(422, {"error": "validation_error", "detail": "content_base64 and uploaded_by are required"})
                email_bytes = base64.b64decode(body["content_base64"])
                storage = LocalObjectStorage(self.repository.root / "objects")
                result = EmailDealImportService(self.repository, storage).import_email_attachments(
                    deal_id,
                    email_bytes,
                    uploaded_by=body["uploaded_by"],
                    key_prefix=body.get("key_prefix"),
                )
                return ApiResponse(
                    201,
                    {
                        "deal_id": result.deal_id,
                        "subject": result.subject,
                        "sender": result.sender,
                        "attachments_imported": result.attachments_imported,
                        "deal": deal_to_dict(self.repository.get(deal_id)),
                    },
                )
            if method == "POST" and segments[2:] == ["cash-flows"]:
                request = AddCashFlowRequest.parse(body)
                deal = self.intake.add_cash_flow(
                    deal_id,
                    period=request.period,
                    amount=request.amount,
                    cash_flow_type=request.cash_flow_type,
                    category=request.category,
                )
                return ApiResponse(201, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["cash-flow-imports"]:
                if not body.get("content_base64"):
                    return ApiResponse(422, {"error": "validation_error", "detail": "content_base64 is required"})
                csv_text = base64.b64decode(body["content_base64"]).decode("utf-8-sig")
                default_type = CashFlowType(body.get("default_type", CashFlowType.ACTUAL.value))
                result = CashFlowImportService(self.repository).import_csv(
                    deal_id,
                    csv_text,
                    default_type=default_type,
                )
                return ApiResponse(
                    201,
                    {
                        "imported_rows": result.imported_rows,
                        "skipped_rows": result.skipped_rows,
                        "deal": deal_to_dict(self.repository.get(deal_id)),
                    },
                )
            if method == "POST" and segments[2:] == ["bank-statement-imports"]:
                if not body.get("content_base64"):
                    return ApiResponse(422, {"error": "validation_error", "detail": "content_base64 is required"})
                csv_text = base64.b64decode(body["content_base64"]).decode("utf-8-sig")
                result = CashFlowImportService(self.repository).import_bank_statement_csv(
                    deal_id,
                    csv_text,
                    default_category=body.get("default_category", "bank_statement"),
                )
                return ApiResponse(
                    201,
                    {
                        "imported_rows": result.imported_rows,
                        "skipped_rows": result.skipped_rows,
                        "deal": deal_to_dict(self.repository.get(deal_id)),
                    },
                )
            if method == "POST" and segments[2:] == ["rent-roll"]:
                source = None
                if body.get("source_name"):
                    source = DocumentReference(
                        source_kind=SourceKind(body.get("source_kind", SourceKind.DOCUMENT.value)),
                        name=body["source_name"],
                        page=body.get("page"),
                        sheet=body.get("sheet"),
                        cell=body.get("cell"),
                        context=body.get("context"),
                    )
                deal = self.intake.add_rent_roll_entry(
                    deal_id,
                    as_of_date=body["as_of_date"],
                    unit=body["unit"],
                    tenant_name=body.get("tenant_name"),
                    monthly_rent=body.get("monthly_rent"),
                    market_rent=body.get("market_rent"),
                    occupied=bool(body.get("occupied", True)),
                    concessions=body.get("concessions"),
                    bad_debt=body.get("bad_debt"),
                    lease_start=body.get("lease_start"),
                    lease_end=body.get("lease_end"),
                    source=source,
                )
                return ApiResponse(201, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["obligations"]:
                deal = self.intake.add_obligation(
                    deal_id,
                    title=body["title"],
                    due_date=body["due_date"],
                    obligation_type=ObligationType(body["obligation_type"]),
                    amount=body.get("amount"),
                    source=body.get("source"),
                    owner=body.get("owner"),
                )
                return ApiResponse(201, deal_to_dict(deal))
            if method == "POST" and segments[2:] == ["obligation-imports"]:
                if not body.get("content_base64"):
                    return ApiResponse(422, {"error": "validation_error", "detail": "content_base64 is required"})
                csv_text = base64.b64decode(body["content_base64"]).decode("utf-8-sig")
                result = ObligationImportService(self.repository).import_csv(deal_id, csv_text)
                return ApiResponse(
                    201,
                    {
                        "imported_rows": result.imported_rows,
                        "skipped_rows": result.skipped_rows,
                        "deal": deal_to_dict(self.repository.get(deal_id)),
                    },
                )
            if method == "POST" and segments[2:] == ["monitoring"]:
                deal = self.repository.get(deal_id)
                add_new_alerts(deal, monitoring_alerts(deal))
                self.repository.save(deal)
                return ApiResponse(200, deal_to_dict(deal))
            if method == "GET" and segments[2:] == ["memo"]:
                return ApiResponse(200, {"markdown": generate_ic_memo_markdown(self.repository.get(deal_id))})
            if method == "POST" and segments[2:] == ["reports", "monthly-performance"]:
                return ApiResponse(
                    200,
                    {
                        "markdown": generate_monthly_performance_report_markdown(
                            self.repository.get(deal_id),
                            period=body.get("period"),
                        )
                    },
                )
            if method == "GET" and segments[2:] == ["reports", "development-progress"]:
                return ApiResponse(
                    200,
                    {"markdown": generate_development_progress_report_markdown(self.repository.get(deal_id))},
                )
            if method == "GET" and segments[2:] == ["reports", "asset-monitoring"]:
                return ApiResponse(
                    200,
                    {"markdown": generate_asset_monitoring_report_markdown(self.repository.get(deal_id))},
                )
            if method == "GET" and segments[2:] == ["reports", "lender-covenants"]:
                return ApiResponse(
                    200,
                    {"markdown": generate_lender_covenant_report_markdown(self.repository.get(deal_id))},
                )
            if method == "POST" and segments[2:] == ["comments"]:
                self.collaboration.add_comment(
                    deal_id,
                    author=body["author"],
                    body=body["body"],
                    entity_type=body.get("entity_type", "deal"),
                    entity_id=body.get("entity_id"),
                )
                return ApiResponse(201, deal_to_dict(self.repository.get(deal_id)))
            if method == "POST" and segments[2:] == ["approval-requests"]:
                self.collaboration.request_approval(
                    deal_id,
                    title=body["title"],
                    requested_by=body["requested_by"],
                    approver=body["approver"],
                    entity_type=body.get("entity_type", "deal"),
                    entity_id=body.get("entity_id"),
                )
                return ApiResponse(201, deal_to_dict(self.repository.get(deal_id)))
            if method == "POST" and segments[2:] == ["approval-decisions"]:
                self.collaboration.decide_approval(
                    deal_id,
                    body["approval_id"],
                    approved=body["approved"],
                    note=body.get("note"),
                )
                return ApiResponse(200, deal_to_dict(self.repository.get(deal_id)))

        return ApiResponse(404, {"error": "not_found"})


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _safe_filename(filename: str) -> str:
    normalized = filename.replace("\\", "/")
    basename = PurePosixPath(normalized).name
    if not basename or basename in {".", ".."}:
        return "upload.bin"
    return basename

"""Email-based deal intake helpers."""

from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from email.message import EmailMessage
from pathlib import PurePosixPath

from real_estate_helm.data_room import _document_type_for_name, _safe_zip_name
from real_estate_helm.intake import IntakeService
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.services import DealService
from real_estate_helm.storage import ObjectStorage


@dataclass(frozen=True)
class EmailImportResult:
    deal_id: str
    subject: str
    sender: str | None
    attachments_imported: int


class EmailDealImportService:
    def __init__(self, repository: JsonDealRepository, storage: ObjectStorage) -> None:
        self.repository = repository
        self.storage = storage
        self.deals = DealService(repository)
        self.intake = IntakeService(repository)

    def create_deal_from_email(
        self,
        email_bytes: bytes,
        *,
        uploaded_by: str,
        owner: str | None = None,
    ) -> EmailImportResult:
        message = _parse_email(email_bytes)
        subject = _subject(message)
        sender = message.get("from")
        deal = self.deals.create_deal(subject, source=sender, owner=owner)
        return self.import_email_attachments(deal.id, email_bytes, uploaded_by=uploaded_by)

    def import_email_attachments(
        self,
        deal_id: str,
        email_bytes: bytes,
        *,
        uploaded_by: str,
        key_prefix: str | None = None,
    ) -> EmailImportResult:
        message = _parse_email(email_bytes)
        subject = _subject(message)
        sender = message.get("from")
        prefix = (key_prefix or f"deals/{deal_id}/email").strip("/")
        imported = 0
        for attachment in _attachments(message):
            filename = _safe_attachment_name(attachment.get_filename(), imported + 1)
            data = attachment.get_payload(decode=True) or b""
            stored = self.storage.put_bytes(f"{prefix}/{filename}", data)
            self.intake.add_document(
                deal_id,
                name=filename,
                document_type=_document_type_for_name(filename),
                storage_uri=stored.uri,
                uploaded_by=uploaded_by,
                sha256=stored.sha256,
            )
            imported += 1
        return EmailImportResult(deal_id, subject, sender, imported)


def _parse_email(email_bytes: bytes) -> EmailMessage:
    return BytesParser(policy=policy.default).parsebytes(email_bytes)


def _subject(message: EmailMessage) -> str:
    return str(message.get("subject") or "Imported email deal").strip()


def _attachments(message: EmailMessage) -> list[EmailMessage]:
    return [part for part in message.iter_attachments() if not part.is_multipart()]


def _safe_attachment_name(filename: str | None, sequence: int) -> str:
    if not filename:
        return f"attachment-{sequence}.bin"
    normalized = filename.replace("\\", "/")
    safe_name = _safe_zip_name(normalized)
    if safe_name is not None:
        return safe_name
    basename = PurePosixPath(normalized).name
    return basename or f"attachment-{sequence}.bin"

"""Data-room ingestion helpers for zipped diligence folders."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from pathlib import PurePosixPath

from real_estate_helm.domain import DocumentType
from real_estate_helm.intake import IntakeService
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.storage import ObjectStorage


@dataclass(frozen=True)
class DataRoomImportResult:
    documents_imported: int
    skipped_entries: list[str]


class DataRoomImportService:
    def __init__(self, repository: JsonDealRepository, storage: ObjectStorage) -> None:
        self.repository = repository
        self.storage = storage
        self.intake = IntakeService(repository)

    def import_zip(
        self,
        deal_id: str,
        archive_bytes: bytes,
        *,
        uploaded_by: str,
        key_prefix: str | None = None,
    ) -> DataRoomImportResult:
        imported = 0
        skipped: list[str] = []
        prefix = (key_prefix or f"deals/{deal_id}/data-room").strip("/")
        with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = _safe_zip_name(info.filename)
                if name is None:
                    skipped.append(info.filename)
                    continue
                document_type = _document_type_for_name(name)
                data = archive.read(info)
                stored = self.storage.put_bytes(f"{prefix}/{name}", data)
                self.intake.add_document(
                    deal_id,
                    name=name,
                    document_type=document_type,
                    storage_uri=stored.uri,
                    uploaded_by=uploaded_by,
                    sha256=stored.sha256,
                )
                imported += 1
        return DataRoomImportResult(imported, skipped)

    def import_directory(
        self,
        deal_id: str,
        directory: Path | str,
        *,
        uploaded_by: str,
        key_prefix: str | None = None,
    ) -> DataRoomImportResult:
        root = Path(directory).resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"data-room directory does not exist: {directory}")
        imported = 0
        skipped: list[str] = []
        prefix = (key_prefix or f"deals/{deal_id}/data-room").strip("/")
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative_name = _safe_directory_name(root, path)
            if relative_name is None:
                skipped.append(str(path))
                continue
            document_type = _document_type_for_name(relative_name)
            stored = self.storage.put_bytes(f"{prefix}/{relative_name}", path.read_bytes())
            self.intake.add_document(
                deal_id,
                name=relative_name,
                document_type=document_type,
                storage_uri=stored.uri,
                uploaded_by=uploaded_by,
                sha256=stored.sha256,
            )
            imported += 1
        return DataRoomImportResult(imported, skipped)


def _safe_zip_name(filename: str) -> str | None:
    path = PurePosixPath(filename)
    if path.is_absolute() or ".." in path.parts or not path.name:
        return None
    if path.parts and path.parts[0] == "__MACOSX":
        return None
    return str(path)


def _safe_directory_name(root: Path, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        return None
    posix_name = relative.as_posix()
    safe_name = _safe_zip_name(posix_name)
    if safe_name is None or relative.name in {".DS_Store", "Thumbs.db"}:
        return None
    return safe_name


def _document_type_for_name(name: str) -> DocumentType:
    suffix = PurePosixPath(name).suffix.casefold()
    return {
        ".pdf": DocumentType.PDF,
        ".xlsx": DocumentType.EXCEL,
        ".xls": DocumentType.EXCEL,
        ".csv": DocumentType.CSV,
        ".doc": DocumentType.WORD,
        ".docx": DocumentType.WORD,
        ".png": DocumentType.IMAGE,
        ".jpg": DocumentType.IMAGE,
        ".jpeg": DocumentType.IMAGE,
        ".zip": DocumentType.ZIP,
    }.get(suffix, DocumentType.OTHER)

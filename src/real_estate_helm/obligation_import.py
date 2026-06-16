"""CSV import helpers for legal deadlines, expirations, and capital calls."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import StringIO

from real_estate_helm.domain import ObligationType
from real_estate_helm.intake import IntakeService
from real_estate_helm.repository import JsonDealRepository


@dataclass(frozen=True)
class ObligationImportResult:
    imported_rows: int
    skipped_rows: list[str] = field(default_factory=list)


class ObligationImportService:
    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository
        self.intake = IntakeService(repository)

    def import_csv(self, deal_id: str, csv_text: str) -> ObligationImportResult:
        imported = 0
        skipped: list[str] = []
        reader = csv.DictReader(StringIO(csv_text))
        for row_number, row in enumerate(reader, start=2):
            try:
                amount = _optional_decimal(row.get("amount"))
                self.intake.add_obligation(
                    deal_id,
                    title=_required(row, "title"),
                    due_date=_required(row, "due_date"),
                    obligation_type=ObligationType(_required(row, "obligation_type")),
                    amount=amount,
                    source=_optional(row.get("source")),
                    owner=_optional(row.get("owner")),
                )
            except (InvalidOperation, ValueError) as exc:
                skipped.append(f"row {row_number}: {exc}")
                continue
            imported += 1
        return ObligationImportResult(imported, skipped)


def _required(row: dict[str, str | None], key: str) -> str:
    value = row.get(key)
    if value is None or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _optional(value: str | None) -> str | None:
    return value.strip() if value is not None and value.strip() else None


def _optional_decimal(value: str | None) -> Decimal | None:
    if value is None or not value.strip():
        return None
    return Decimal(value.strip())

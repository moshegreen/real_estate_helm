"""CRM export ingestion for pipeline deal records."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from io import StringIO

from real_estate_helm.domain import DealStatus
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.services import DealService


@dataclass(frozen=True)
class CrmImportResult:
    imported_rows: int
    skipped_rows: list[str] = field(default_factory=list)
    deal_ids: list[str] = field(default_factory=list)


class CrmImportService:
    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository
        self.deals = DealService(repository)

    def import_csv(self, csv_text: str, *, default_owner: str | None = None) -> CrmImportResult:
        imported = 0
        skipped: list[str] = []
        deal_ids: list[str] = []
        reader = csv.DictReader(StringIO(csv_text))
        for row_number, row in enumerate(reader, start=2):
            try:
                name = _first(row, "name", "deal_name", "opportunity_name")
                if not name:
                    raise ValueError("name is required")
                deal = self.deals.create_deal(
                    name,
                    address=_first(row, "address", "property_address"),
                    asset_type=_first(row, "asset_type", "asset_class"),
                    sponsor=_first(row, "sponsor"),
                    broker=_first(row, "broker"),
                    seller=_first(row, "seller"),
                    source=_first(row, "source") or "crm_export",
                    owner=_first(row, "owner", "analyst") or default_owner,
                )
                status = _first(row, "status", "stage")
                if status:
                    deal.status = DealStatus(_normalize_status(status))
                    self.repository.save(deal)
            except ValueError as exc:
                skipped.append(f"row {row_number}: {exc}")
                continue
            imported += 1
            deal_ids.append(deal.id)
        return CrmImportResult(imported, skipped, deal_ids)


def _first(row: dict[str, str | None], *keys: str) -> str | None:
    normalized = {key.casefold(): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.casefold())
        if value is not None and value.strip():
            return value.strip()
    return None


def _normalize_status(value: str) -> str:
    return value.strip().casefold().replace(" ", "_").replace("-", "_")

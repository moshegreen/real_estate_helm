"""CSV import helpers for projected and actual cash-flow updates."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import StringIO

from real_estate_helm.domain import CashFlowRecord, CashFlowType
from real_estate_helm.repository import JsonDealRepository


@dataclass(frozen=True)
class CashFlowImportResult:
    imported_rows: int
    skipped_rows: list[str] = field(default_factory=list)


class CashFlowImportService:
    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository

    def import_csv(
        self,
        deal_id: str,
        csv_text: str,
        *,
        default_type: CashFlowType = CashFlowType.ACTUAL,
    ) -> CashFlowImportResult:
        deal = self.repository.get(deal_id)
        imported = 0
        skipped: list[str] = []
        reader = csv.DictReader(StringIO(csv_text))
        for row_number, row in enumerate(reader, start=2):
            try:
                period = _required(row, "period")
                category = _required(row, "category")
                amount = Decimal(_required(row, "amount"))
                cash_flow_type = CashFlowType(row.get("cash_flow_type") or default_type.value)
            except (InvalidOperation, ValueError) as exc:
                skipped.append(f"row {row_number}: {exc}")
                continue

            record = CashFlowRecord(
                period=period,
                amount=amount,
                cash_flow_type=cash_flow_type,
                category=category,
            )
            if cash_flow_type == CashFlowType.PROJECTED:
                deal.projected_cash_flows.append(record)
            else:
                deal.actual_cash_flows.append(record)
            imported += 1
        self.repository.save(deal)
        return CashFlowImportResult(imported, skipped)

    def import_bank_statement_csv(
        self,
        deal_id: str,
        csv_text: str,
        *,
        default_category: str = "bank_statement",
    ) -> CashFlowImportResult:
        deal = self.repository.get(deal_id)
        imported = 0
        skipped: list[str] = []
        reader = csv.DictReader(StringIO(csv_text))
        for row_number, row in enumerate(reader, start=2):
            try:
                posted_at = _first(row, "date", "posted_at", "transaction_date")
                if posted_at is None:
                    raise ValueError("date is required")
                amount = _bank_amount(row)
                category = _first(row, "category", "memo", "description") or default_category
            except (InvalidOperation, ValueError) as exc:
                skipped.append(f"row {row_number}: {exc}")
                continue
            deal.actual_cash_flows.append(
                CashFlowRecord(
                    period=posted_at[:7],
                    amount=amount,
                    cash_flow_type=CashFlowType.ACTUAL,
                    category=category,
                )
            )
            imported += 1
        self.repository.save(deal)
        return CashFlowImportResult(imported, skipped)


def _required(row: dict[str, str | None], key: str) -> str:
    value = row.get(key)
    if value is None or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _first(row: dict[str, str | None], *keys: str) -> str | None:
    normalized = {key.casefold(): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.casefold())
        if value is not None and value.strip():
            return value.strip()
    return None


def _bank_amount(row: dict[str, str | None]) -> Decimal:
    amount = _first(row, "amount")
    if amount is not None:
        return Decimal(amount)
    deposit = _first(row, "deposit", "credit")
    withdrawal = _first(row, "withdrawal", "debit")
    if deposit is not None:
        return Decimal(deposit)
    if withdrawal is not None:
        return -Decimal(withdrawal)
    raise ValueError("amount, deposit, credit, withdrawal, or debit is required")

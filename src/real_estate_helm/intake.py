"""Local intake helpers for assets, documents, spreadsheets, and cash flows."""

from __future__ import annotations

from typing import Any

from real_estate_helm.domain import (
    Address,
    Asset,
    CashFlowRecord,
    CashFlowType,
    Coordinates,
    Deal,
    DocumentPage,
    DocumentReference,
    DocumentType,
    ImagerySnapshot,
    Obligation,
    ObligationType,
    RentRollEntry,
    SpreadsheetCell,
    SpreadsheetModel,
    UploadedDocument,
)
from real_estate_helm.repository import JsonDealRepository


class IntakeService:
    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository

    def add_asset(
        self,
        deal_id: str,
        name: str,
        *,
        address: Address | None = None,
        coordinates: Coordinates | None = None,
        asset_type: str | None = None,
        unit_count: int | None = None,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        deal.assets.append(
            Asset(
                name=name,
                address=address,
                coordinates=coordinates,
                asset_type=asset_type,
                unit_count=unit_count,
            )
        )
        self.repository.save(deal)
        return deal

    def add_obligation(
        self,
        deal_id: str,
        *,
        title: str,
        due_date: str,
        obligation_type: ObligationType,
        amount: Any | None = None,
        source: str | None = None,
        owner: str | None = None,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        deal.obligations.append(
            Obligation(
                title=title,
                due_date=due_date,
                obligation_type=obligation_type,
                amount=amount,
                source=source,
                owner=owner,
            )
        )
        self.repository.save(deal)
        return deal

    def add_rent_roll_entry(
        self,
        deal_id: str,
        *,
        as_of_date: str,
        unit: str,
        tenant_name: str | None = None,
        monthly_rent: Any | None = None,
        market_rent: Any | None = None,
        occupied: bool = True,
        concessions: Any | None = None,
        bad_debt: Any | None = None,
        lease_start: str | None = None,
        lease_end: str | None = None,
        source: DocumentReference | None = None,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        deal.rent_roll.append(
            RentRollEntry(
                as_of_date=as_of_date,
                unit=unit,
                tenant_name=tenant_name,
                monthly_rent=monthly_rent,
                market_rent=market_rent,
                occupied=occupied,
                concessions=concessions,
                bad_debt=bad_debt,
                lease_start=lease_start,
                lease_end=lease_end,
                source=source,
            )
        )
        self.repository.save(deal)
        return deal

    def add_document(
        self,
        deal_id: str,
        *,
        name: str,
        document_type: DocumentType,
        storage_uri: str,
        uploaded_by: str,
        sha256: str | None = None,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        deal.documents.append(
            UploadedDocument(
                name=name,
                document_type=document_type,
                storage_uri=storage_uri,
                uploaded_by=uploaded_by,
                sha256=sha256,
            )
        )
        self.repository.save(deal)
        return deal

    def add_document_page(
        self,
        deal_id: str,
        *,
        document_id: str,
        page_number: int,
        text_content: str | None = None,
        image_uri: str | None = None,
        extracted_tables: list[dict[str, Any]] | None = None,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        if not any(document.id == document_id for document in deal.documents):
            raise ValueError(f"unknown document id: {document_id}")
        deal.document_pages.append(
            DocumentPage(
                document_id=document_id,
                page_number=page_number,
                text_content=text_content,
                image_uri=image_uri,
                extracted_tables=extracted_tables or [],
            )
        )
        self.repository.save(deal)
        return deal

    def add_imagery_snapshot(
        self,
        deal_id: str,
        *,
        captured_at: str,
        storage_uri: str,
        source: str,
        notes: str | None = None,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        deal.imagery_snapshots.append(
            ImagerySnapshot(
                captured_at=captured_at,
                storage_uri=storage_uri,
                source=source,
                notes=notes,
            )
        )
        self.repository.save(deal)
        return deal

    def add_spreadsheet_model(
        self,
        deal_id: str,
        *,
        name: str,
        document_id: str,
        cells: list[SpreadsheetCell],
    ) -> Deal:
        deal = self.repository.get(deal_id)
        deal.spreadsheets.append(SpreadsheetModel(name=name, document_id=document_id, cells=cells))
        self.repository.save(deal)
        return deal

    def add_cash_flow(
        self,
        deal_id: str,
        *,
        period: str,
        amount: Any,
        cash_flow_type: CashFlowType,
        category: str,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        record = CashFlowRecord(period=period, amount=amount, cash_flow_type=cash_flow_type, category=category)
        if cash_flow_type == CashFlowType.PROJECTED:
            deal.projected_cash_flows.append(record)
        else:
            deal.actual_cash_flows.append(record)
        self.repository.save(deal)
        return deal

"""Application services for deal intake and review workflows."""

from __future__ import annotations

from typing import Any

from real_estate_helm.domain import (
    Deal,
    DealIdentity,
    DealStatus,
    DocumentReference,
    ExtractedFact,
    FactReviewStatus,
)
from real_estate_helm.repository import JsonDealRepository


class DealService:
    """Coordinate common deal mutations with persistence."""

    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository

    def create_deal(
        self,
        name: str,
        *,
        address: str | None = None,
        parcel: str | None = None,
        asset_type: str | None = None,
        sponsor: str | None = None,
        broker: str | None = None,
        seller: str | None = None,
        source: str | None = None,
        owner: str | None = None,
    ) -> Deal:
        deal = Deal(
            DealIdentity(
                name=name,
                address=address,
                parcel=parcel,
                asset_type=asset_type,
                sponsor=sponsor,
                broker=broker,
                seller=seller,
                source=source,
                owner=owner,
            )
        )
        self.repository.save(deal)
        return deal

    def add_extracted_fact(
        self,
        deal_id: str,
        *,
        field_name: str,
        value: Any,
        confidence: float,
        source: DocumentReference,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        deal.add_extracted_fact(
            ExtractedFact(
                field_name=field_name,
                value=value,
                confidence=confidence,
                source=source,
            )
        )
        self.repository.save(deal)
        return deal

    def review_fact(
        self,
        deal_id: str,
        fact_id: str,
        status: FactReviewStatus,
        reviewer: str,
        *,
        note: str | None = None,
        corrected_value: Any | None = None,
        promote_to_assumption: bool = False,
        rationale: str | None = None,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        deal.review_fact(
            fact_id,
            status,
            reviewer,
            note=note,
            corrected_value=corrected_value,
            promote_to_assumption=promote_to_assumption,
            rationale=rationale,
        )
        self.repository.save(deal)
        return deal

    def change_status(self, deal_id: str, status: DealStatus, actor: str, reason: str) -> Deal:
        deal = self.repository.get(deal_id)
        deal.change_status(status, actor, reason)
        self.repository.save(deal)
        return deal

    def reject_deal(self, deal_id: str, actor: str, reason: str) -> Deal:
        deal = self.repository.get(deal_id)
        deal.reject(actor, reason)
        self.repository.save(deal)
        return deal

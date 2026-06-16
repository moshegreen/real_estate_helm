"""Application services for deal intake and review workflows."""

from __future__ import annotations

from typing import Any

from real_estate_helm.domain import (
    Assumption,
    AuditLogEntry,
    Deal,
    DealIdentity,
    DealStatus,
    DocumentReference,
    ExtractedFact,
    FactReviewStatus,
    Scenario,
    ScenarioType,
    Task,
)
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.scenarios import compare_scenario_outputs


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

    def request_fact_reextraction(
        self,
        deal_id: str,
        fact_id: str,
        *,
        reviewer: str,
        note: str | None = None,
        owner: str | None = None,
        due_date: str | None = None,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        fact = next(item for item in deal.extracted_facts if item.id == fact_id)
        deal.review_fact(
            fact_id,
            FactReviewStatus.NEEDS_REEXTRACTION,
            reviewer,
            note=note or "Re-extraction requested.",
        )
        task = Task(
            title=f"Re-extract {fact.field_name} from {fact.source.name}",
            owner=owner or reviewer,
            due_date=due_date,
        )
        deal.tasks.append(task)
        deal.audit_log.append(
            AuditLogEntry(
                actor=reviewer,
                action="request_fact_reextraction",
                entity_type="extracted_fact",
                entity_id=fact_id,
                reason=note or f"Re-extraction requested for {fact.field_name}.",
            )
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

    def update_scenario_assumption(
        self,
        deal_id: str,
        scenario_id: str,
        *,
        name: str,
        value: Any,
        actor: str,
        rationale: str,
        source_fact_id: str | None = None,
        revised_outputs: dict[str, Any] | None = None,
    ) -> Deal:
        deal = self.repository.get(deal_id)
        scenario = _scenario_by_id(deal, scenario_id)
        before = Scenario(
            name=scenario.name,
            scenario_type=scenario.scenario_type,
            assumptions=list(scenario.assumptions),
            outputs=dict(scenario.outputs),
        )
        old_value = None
        for index, assumption in enumerate(scenario.assumptions):
            if assumption.name == name:
                old_value = assumption.value
                scenario.assumptions[index] = Assumption(
                    name=name,
                    value=value,
                    rationale=rationale,
                    source_fact_id=source_fact_id or assumption.source_fact_id,
                )
                break
        else:
            scenario.assumptions.append(
                Assumption(name=name, value=value, rationale=rationale, source_fact_id=source_fact_id)
            )
        if revised_outputs:
            scenario.outputs.update(revised_outputs)
        output_changes = [
            f"{diff.metric}: {diff.left_value} -> {diff.right_value}"
            for diff in compare_scenario_outputs(before, scenario)
            if diff.left_value != diff.right_value
        ]
        reason_parts = [f"{name}: {old_value} -> {value}", rationale]
        if scenario.scenario_type == ScenarioType.INVESTMENT_COMMITTEE_CASE:
            reason_parts.append("IC-approved scenario modified")
        if output_changes:
            reason_parts.append("outputs changed: " + "; ".join(output_changes))
        deal.audit_log.append(
            AuditLogEntry(
                actor=actor,
                action="update_scenario_assumption",
                entity_type="scenario",
                entity_id=scenario.id,
                reason=". ".join(reason_parts),
            )
        )
        self.repository.save(deal)
        return deal


def _scenario_by_id(deal: Deal, scenario_id: str) -> Scenario:
    for scenario in deal.scenarios:
        if scenario.id == scenario_id:
            return scenario
    raise ValueError(f"unknown scenario id: {scenario_id}")

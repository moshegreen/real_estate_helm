"""Export authorization and redaction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from real_estate_helm.domain import Deal, UserRole
from real_estate_helm.security import AuthenticatedPrincipal
from real_estate_helm.serialization import deal_to_dict


class ExportKind(StrEnum):
    DEAL_JSON = "deal_json"
    IC_MEMO = "ic_memo"
    CASH_FLOW_REPORT = "cash_flow_report"
    DATA_ROOM_ARCHIVE = "data_room_archive"
    INVESTMENT_COMMITTEE_DECK = "investment_committee_deck"


@dataclass(frozen=True)
class ExportDecision:
    allowed: bool
    reason: str
    requires_redaction: bool = False


class ExportControlPolicy:
    """Central role/MFA policy for moving deal data out of the system."""

    _privileged_roles = {UserRole.ADMIN, UserRole.PORTFOLIO_MANAGER, UserRole.PRINCIPAL}
    _restricted_viewer_kinds = {ExportKind.DEAL_JSON, ExportKind.DATA_ROOM_ARCHIVE}

    def decide(
        self,
        principal: AuthenticatedPrincipal,
        export_kind: ExportKind,
        *,
        include_sensitive: bool = False,
    ) -> ExportDecision:
        if principal.role == UserRole.READ_ONLY_VIEWER and export_kind in self._restricted_viewer_kinds:
            return ExportDecision(False, "read-only viewers cannot export raw deal data")
        if export_kind == ExportKind.DATA_ROOM_ARCHIVE and principal.role not in self._privileged_roles:
            return ExportDecision(False, "data room archives require portfolio-level authorization")
        if include_sensitive and principal.role == UserRole.EXTERNAL_ADVISOR:
            return ExportDecision(False, "external advisors cannot export sensitive deal data")
        if include_sensitive and not principal.mfa_verified:
            return ExportDecision(False, "multi-factor authentication required for sensitive exports")
        return ExportDecision(True, "export allowed", requires_redaction=not include_sensitive)

    def require_allowed(
        self,
        principal: AuthenticatedPrincipal,
        export_kind: ExportKind,
        *,
        include_sensitive: bool = False,
    ) -> ExportDecision:
        decision = self.decide(principal, export_kind, include_sensitive=include_sensitive)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        return decision


def redacted_deal_export(deal: Deal) -> dict[str, Any]:
    """Return a JSON-safe deal dict with source files and sensitive values hidden."""

    data = deal_to_dict(deal)
    for document in data.get("documents", []):
        document["storage_uri"] = "[redacted]"
        if document.get("sha256") is not None:
            document["sha256"] = "[redacted]"
    for page in data.get("document_pages", []):
        if page.get("image_uri") is not None:
            page["image_uri"] = "[redacted]"
    for fact in data.get("extracted_facts", []):
        fact["value"] = "[redacted]"
    for assumption in data.get("assumptions", []):
        assumption["value"] = "[redacted]"
    for scenario in data.get("scenarios", []):
        for assumption in scenario.get("assumptions", []):
            assumption["value"] = "[redacted]"
    for terms in data.get("debt_terms", []):
        for field_name in ("debt_amount", "interest_rate"):
            if terms.get(field_name) is not None:
                terms[field_name] = "[redacted]"
    for record in data.get("property_records", []):
        if record.get("owner_name") is not None:
            record["owner_name"] = "[redacted]"
    return data

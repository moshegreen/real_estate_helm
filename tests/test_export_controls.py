import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest import TestCase

from real_estate_helm import (
    Assumption,
    Deal,
    DealIdentity,
    DebtTerms,
    DocumentPage,
    DocumentReference,
    DocumentType,
    ExportControlPolicy,
    ExportKind,
    ExtractedFact,
    PropertyRecord,
    SourceKind,
    UploadedDocument,
    UserRole,
)
from real_estate_helm.export_controls import redacted_deal_export
from real_estate_helm.reporting import export_redacted_deal_json
from real_estate_helm.security import AuthenticatedPrincipal


class ExportControlTests(TestCase):
    def test_sensitive_exports_require_mfa(self) -> None:
        policy = ExportControlPolicy()
        principal = _principal(UserRole.ADMIN, mfa_verified=False)

        decision = policy.decide(principal, ExportKind.DEAL_JSON, include_sensitive=True)

        self.assertFalse(decision.allowed)
        self.assertIn("multi-factor", decision.reason)

    def test_mfa_verified_privileged_user_can_export_sensitive_data_room(self) -> None:
        policy = ExportControlPolicy()
        principal = _principal(UserRole.PORTFOLIO_MANAGER, mfa_verified=True)

        decision = policy.require_allowed(
            principal,
            ExportKind.DATA_ROOM_ARCHIVE,
            include_sensitive=True,
        )

        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_redaction)

    def test_read_only_viewer_and_external_advisor_restrictions(self) -> None:
        policy = ExportControlPolicy()

        viewer_decision = policy.decide(_principal(UserRole.READ_ONLY_VIEWER), ExportKind.DEAL_JSON)
        advisor_decision = policy.decide(
            _principal(UserRole.EXTERNAL_ADVISOR, mfa_verified=True),
            ExportKind.IC_MEMO,
            include_sensitive=True,
        )

        self.assertFalse(viewer_decision.allowed)
        self.assertFalse(advisor_decision.allowed)
        with self.assertRaises(PermissionError):
            policy.require_allowed(_principal(UserRole.ANALYST), ExportKind.DATA_ROOM_ARCHIVE)

    def test_redacted_deal_export_hides_sensitive_fields_without_mutating_deal(self) -> None:
        deal = Deal(DealIdentity("Sensitive Deal"))
        deal.documents.append(
            UploadedDocument(
                "om.pdf",
                DocumentType.PDF,
                "local://objects/om.pdf",
                "analyst",
                sha256="abc123",
            )
        )
        deal.document_pages.append(DocumentPage(deal.documents[0].id, 1, image_uri="local://objects/page.png"))
        deal.extracted_facts.append(
            ExtractedFact(
                "current_noi",
                Decimal("1200000"),
                DocumentReference(SourceKind.DOCUMENT, "om.pdf", page=4),
                0.96,
            )
        )
        deal.assumptions.append(Assumption("exit_cap_rate", Decimal("0.0575"), "Comparable sales"))
        deal.debt_terms.append(DebtTerms(lender="Bank", debt_amount=Decimal("7000000"), interest_rate=Decimal("0.061")))
        deal.property_records.append(PropertyRecord("county", owner_name="Sponsor LLC", assessed_value=Decimal("9000000")))

        exported = redacted_deal_export(deal)
        exported_json = json.loads(export_redacted_deal_json(deal))

        self.assertEqual(exported["documents"][0]["storage_uri"], "[redacted]")
        self.assertEqual(exported["documents"][0]["sha256"], "[redacted]")
        self.assertEqual(exported["document_pages"][0]["image_uri"], "[redacted]")
        self.assertEqual(exported["extracted_facts"][0]["value"], "[redacted]")
        self.assertEqual(exported["assumptions"][0]["value"], "[redacted]")
        self.assertEqual(exported["debt_terms"][0]["debt_amount"], "[redacted]")
        self.assertEqual(exported["debt_terms"][0]["interest_rate"], "[redacted]")
        self.assertEqual(exported["property_records"][0]["owner_name"], "[redacted]")
        self.assertEqual(exported_json["documents"][0]["storage_uri"], "[redacted]")
        self.assertEqual(deal.documents[0].storage_uri, "local://objects/om.pdf")
        self.assertEqual(deal.extracted_facts[0].value, Decimal("1200000"))


def _principal(role: UserRole, *, mfa_verified: bool = False) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        "user@example.test",
        role,
        datetime(2030, 1, 1, tzinfo=UTC),
        mfa_verified=mfa_verified,
    )

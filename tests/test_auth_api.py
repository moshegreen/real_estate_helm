from tempfile import TemporaryDirectory
from unittest import TestCase
from datetime import UTC, datetime

from real_estate_helm import Deal, DealIdentity, DocumentType, UploadedDocument, UserRole
from real_estate_helm.api import ApiRouter
from real_estate_helm.auth_api import AuthenticatedApiRouter
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.security import (
    AccessGrant,
    AuthenticatedPrincipal,
    ObjectAccessPolicy,
    require_mfa,
    TokenAuthenticator,
    totp_code,
    verify_totp,
)


class AuthenticatedApiTests(TestCase):
    def test_bearer_token_allows_authorized_requests(self) -> None:
        with TemporaryDirectory() as directory:
            auth = TokenAuthenticator(b"0123456789abcdef")
            token = auth.issue_token("analyst@example.test", UserRole.ANALYST)
            router = AuthenticatedApiRouter(ApiRouter(JsonDealRepository(directory)), auth)

            response = router.handle(
                "POST",
                "/deals",
                {"name": "Authorized Deal"},
                authorization=f"Bearer {token}",
            )

            self.assertEqual(response.status, 201)

    def test_missing_or_read_only_token_blocks_write(self) -> None:
        with TemporaryDirectory() as directory:
            auth = TokenAuthenticator(b"0123456789abcdef")
            router = AuthenticatedApiRouter(ApiRouter(JsonDealRepository(directory)), auth)
            read_only = auth.issue_token("viewer@example.test", UserRole.READ_ONLY_VIEWER)

            self.assertEqual(router.handle("GET", "/health").status, 401)
            self.assertEqual(
                router.handle("POST", "/deals", {"name": "Blocked"}, authorization=f"Bearer {read_only}").status,
                403,
            )

    def test_object_policy_filters_deal_list_and_blocks_unowned_write(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            owned = Deal(DealIdentity("Owned Deal", owner="analyst@example.test"))
            restricted = Deal(DealIdentity("Restricted Deal", owner="other@example.test"))
            repository.save(owned)
            repository.save(restricted)
            auth = TokenAuthenticator(b"0123456789abcdef")
            token = auth.issue_token("analyst@example.test", UserRole.ANALYST)
            router = AuthenticatedApiRouter(ApiRouter(repository), auth, ObjectAccessPolicy())

            list_response = router.handle("GET", "/deals", authorization=f"Bearer {token}")
            write_response = router.handle(
                "POST",
                f"/deals/{restricted.id}/status",
                {"status": "screening", "actor": "analyst", "reason": "Review"},
                authorization=f"Bearer {token}",
            )

            self.assertEqual([deal["identity"]["name"] for deal in list_response.body], ["Owned Deal"])
            self.assertEqual(write_response.status, 403)

    def test_object_policy_supports_explicit_deal_and_document_grants(self) -> None:
        deal = Deal(DealIdentity("Granted Deal", owner="owner@example.test"))
        document = UploadedDocument("om.pdf", DocumentType.PDF, "local://om.pdf", "owner@example.test")
        deal.documents.append(document)
        principal = AuthenticatedPrincipal(
            "advisor@example.test",
            UserRole.EXTERNAL_ADVISOR,
            datetime(2030, 1, 1, tzinfo=UTC),
        )
        document_policy = ObjectAccessPolicy(
            [AccessGrant("advisor@example.test", deal.id, document_ids=(document.id,))]
        )
        deal_policy = ObjectAccessPolicy([AccessGrant("advisor@example.test", deal.id)])

        self.assertFalse(document_policy.can_read_deal(principal, deal))
        self.assertTrue(document_policy.can_read_document(principal, deal, document))
        self.assertTrue(deal_policy.can_read_deal(principal, deal))

    def test_totp_mfa_codes_and_token_claims(self) -> None:
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        at_time = datetime.fromtimestamp(59, UTC)
        auth = TokenAuthenticator(b"0123456789abcdef")
        token = auth.issue_token("admin@example.test", UserRole.ADMIN, mfa_verified=True)

        self.assertEqual(totp_code(secret, at_time=at_time, digits=8), "94287082")
        self.assertTrue(verify_totp(secret, "94287082", at_time=at_time, digits=8, window=0))
        self.assertTrue(auth.authenticate(f"Bearer {token}").mfa_verified)

    def test_require_mfa_rejects_unverified_principal(self) -> None:
        principal = AuthenticatedPrincipal("admin@example.test", UserRole.ADMIN, datetime(2030, 1, 1, tzinfo=UTC))

        with self.assertRaises(PermissionError):
            require_mfa(principal)

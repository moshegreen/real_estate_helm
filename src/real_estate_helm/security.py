"""Role-based permission helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import struct
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from real_estate_helm.domain import Deal, UploadedDocument, UserRole


_ROLE_PERMISSIONS = {
    UserRole.ADMIN: {"read", "write", "approve", "admin"},
    UserRole.PORTFOLIO_MANAGER: {"read", "write", "approve"},
    UserRole.PRINCIPAL: {"read", "write", "approve"},
    UserRole.ANALYST: {"read", "write"},
    UserRole.EXTERNAL_ADVISOR: {"read"},
    UserRole.READ_ONLY_VIEWER: {"read"},
}


def can(role: UserRole, action: str) -> bool:
    return action in _ROLE_PERMISSIONS[role]


def require(role: UserRole, action: str) -> None:
    if not can(role, action):
        raise PermissionError(f"{role.value} cannot {action}")


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    role: UserRole
    expires_at: datetime
    mfa_verified: bool = False


@dataclass(frozen=True)
class AccessGrant:
    subject: str
    deal_id: str
    document_ids: tuple[str, ...] = ()
    can_write: bool = False


class ObjectAccessPolicy:
    def __init__(self, grants: list[AccessGrant] | None = None) -> None:
        self.grants = grants or []

    def can_read_deal(self, principal: AuthenticatedPrincipal, deal: Deal) -> bool:
        if principal.role in {UserRole.ADMIN, UserRole.PORTFOLIO_MANAGER, UserRole.PRINCIPAL}:
            return True
        if deal.identity.owner == principal.subject:
            return True
        return any(
            grant.subject == principal.subject and grant.deal_id == deal.id and not grant.document_ids
            for grant in self.grants
        )

    def can_write_deal(self, principal: AuthenticatedPrincipal, deal: Deal) -> bool:
        if not can(principal.role, "write"):
            return False
        if principal.role in {UserRole.ADMIN, UserRole.PORTFOLIO_MANAGER, UserRole.PRINCIPAL}:
            return True
        if deal.identity.owner == principal.subject:
            return True
        return any(
            grant.subject == principal.subject and grant.deal_id == deal.id and grant.can_write
            for grant in self.grants
        )

    def can_read_document(
        self,
        principal: AuthenticatedPrincipal,
        deal: Deal,
        document: UploadedDocument,
    ) -> bool:
        if self.can_read_deal(principal, deal):
            return True
        return any(
            grant.subject == principal.subject
            and grant.deal_id == deal.id
            and document.id in grant.document_ids
            for grant in self.grants
        )


class TokenAuthenticator:
    def __init__(self, secret: bytes) -> None:
        if len(secret) < 16:
            raise ValueError("auth secret must be at least 16 bytes")
        self.secret = secret

    def issue_token(
        self,
        subject: str,
        role: UserRole,
        *,
        ttl_seconds: int = 3600,
        mfa_verified: bool = False,
    ) -> str:
        payload = {
            "sub": subject,
            "role": role.value,
            "exp": int((datetime.now(UTC) + timedelta(seconds=ttl_seconds)).timestamp()),
            "mfa": mfa_verified,
        }
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        encoded_payload = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=")
        signature = hmac.new(self.secret, encoded_payload, hashlib.sha256).digest()
        encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
        return f"{encoded_payload.decode()}.{encoded_signature.decode()}"

    def authenticate(self, authorization_header: str | None) -> AuthenticatedPrincipal:
        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise PermissionError("missing bearer token")
        token = authorization_header.removeprefix("Bearer ").strip()
        try:
            encoded_payload, encoded_signature = token.split(".", 1)
            expected = hmac.new(self.secret, encoded_payload.encode(), hashlib.sha256).digest()
            actual = _b64decode(encoded_signature)
            if not hmac.compare_digest(expected, actual):
                raise PermissionError("invalid token signature")
            payload = json.loads(_b64decode(encoded_payload))
            expires_at = datetime.fromtimestamp(payload["exp"], UTC)
            if expires_at < datetime.now(UTC):
                raise PermissionError("token expired")
            return AuthenticatedPrincipal(
                payload["sub"],
                UserRole(payload["role"]),
                expires_at,
                bool(payload.get("mfa", False)),
            )
        except PermissionError:
            raise
        except Exception as exc:
            raise PermissionError("invalid token") from exc


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def totp_code(
    base32_secret: str,
    *,
    at_time: datetime | None = None,
    time_step_seconds: int = 30,
    digits: int = 6,
) -> str:
    at_time = at_time or datetime.now(UTC)
    counter = int(at_time.timestamp()) // time_step_seconds
    secret = base64.b32decode(base32_secret.replace(" ", "").upper(), casefold=True)
    digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**digits)).zfill(digits)


def verify_totp(
    base32_secret: str,
    code: str,
    *,
    at_time: datetime | None = None,
    window: int = 1,
    time_step_seconds: int = 30,
    digits: int = 6,
) -> bool:
    at_time = at_time or datetime.now(UTC)
    normalized = code.strip()
    for offset in range(-window, window + 1):
        candidate_time = at_time + timedelta(seconds=offset * time_step_seconds)
        candidate = totp_code(
            base32_secret,
            at_time=candidate_time,
            time_step_seconds=time_step_seconds,
            digits=digits,
        )
        if hmac.compare_digest(candidate, normalized):
            return True
    return False


def require_mfa(principal: AuthenticatedPrincipal) -> None:
    if not principal.mfa_verified:
        raise PermissionError("multi-factor authentication required")

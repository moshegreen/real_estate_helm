"""Authenticated wrapper around the core API router."""

from __future__ import annotations

from typing import Any

from real_estate_helm.api import ApiResponse, ApiRouter
from real_estate_helm.security import ObjectAccessPolicy, TokenAuthenticator, can
from real_estate_helm.serialization import deal_to_dict


class AuthenticatedApiRouter:
    def __init__(
        self,
        router: ApiRouter,
        authenticator: TokenAuthenticator,
        access_policy: ObjectAccessPolicy | None = None,
    ) -> None:
        self.router = router
        self.authenticator = authenticator
        self.access_policy = access_policy

    def handle(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        authorization: str | None = None,
    ) -> ApiResponse:
        action = "read" if method == "GET" else "write"
        try:
            principal = self.authenticator.authenticate(authorization)
            if not can(principal.role, action):
                return ApiResponse(403, {"error": "forbidden"})
            segments = [segment for segment in path.strip("/").split("/") if segment]
            if self.access_policy and method == "GET" and segments == ["deals"]:
                deals = [
                    deal_to_dict(deal)
                    for deal in self.router.repository.list()
                    if self.access_policy.can_read_deal(principal, deal)
                ]
                return ApiResponse(200, deals)
            if self.access_policy and len(segments) >= 2 and segments[0] == "deals":
                deal = self.router.repository.get(segments[1])
                allowed = (
                    self.access_policy.can_read_deal(principal, deal)
                    if action == "read"
                    else self.access_policy.can_write_deal(principal, deal)
                )
                if not allowed:
                    return ApiResponse(403, {"error": "forbidden"})
        except PermissionError as exc:
            return ApiResponse(401, {"error": "unauthorized", "detail": str(exc)})
        return self.router.handle(method, path, body)

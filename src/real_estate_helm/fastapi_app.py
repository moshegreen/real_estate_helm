"""Optional FastAPI application factory.

The core repository does not require FastAPI to run tests. When FastAPI is
installed, this module builds route handlers over the existing ApiRouter.
"""

from __future__ import annotations

from typing import Any, Callable

from real_estate_helm.api import ApiRouter
from real_estate_helm.repository import JsonDealRepository


def create_app(repository: JsonDealRepository, fastapi_factory: Callable[..., Any] | None = None) -> Any:
    if fastapi_factory is None:
        try:
            from fastapi import FastAPI
        except ImportError as exc:
            raise RuntimeError("FastAPI is not installed. Install fastapi to create the production app.") from exc
        fastapi_factory = FastAPI

    app = fastapi_factory(title="Real Estate Helm")
    router = ApiRouter(repository)

    @app.get("/health")
    def health() -> Any:
        return router.handle("GET", "/health").body

    @app.get("/deals")
    def list_deals() -> Any:
        return router.handle("GET", "/deals").body

    @app.post("/deals", status_code=201)
    def create_deal(payload: dict[str, Any]) -> Any:
        return router.handle("POST", "/deals", payload).body

    @app.get("/deals/{deal_id}")
    def get_deal(deal_id: str) -> Any:
        return router.handle("GET", f"/deals/{deal_id}").body

    @app.post("/deals/{deal_id}/monitoring")
    def run_monitoring(deal_id: str) -> Any:
        return router.handle("POST", f"/deals/{deal_id}/monitoring").body

    @app.get("/portfolio/summary")
    def portfolio_summary() -> Any:
        return router.handle("GET", "/portfolio/summary").body

    return app

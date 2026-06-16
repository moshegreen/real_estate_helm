"""File-backed deal repository."""

from __future__ import annotations

import json
from pathlib import Path

from real_estate_helm.domain import Deal, DealStatus
from real_estate_helm.serialization import deal_from_dict, deal_to_dict


class JsonDealRepository:
    """Persist each deal as one JSON file.

    This is intentionally simple and local-first. It gives the early product a
    durable record format before introducing a database or sync layer.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.deals_dir = self.root / "deals"
        self.deals_dir.mkdir(parents=True, exist_ok=True)

    def save(self, deal: Deal) -> None:
        path = self._path_for(deal.id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(deal_to_dict(deal), indent=2, sort_keys=True) + "\n")
        tmp_path.replace(path)

    def get(self, deal_id: str) -> Deal:
        path = self._path_for(deal_id)
        if not path.exists():
            raise KeyError(f"unknown deal id: {deal_id}")
        return deal_from_dict(json.loads(path.read_text()))

    def list(self, *, status: DealStatus | None = None) -> list[Deal]:
        deals = [deal_from_dict(json.loads(path.read_text())) for path in sorted(self.deals_dir.glob("*.json"))]
        if status is not None:
            return [deal for deal in deals if deal.status == status]
        return deals

    def search(self, query: str) -> list[Deal]:
        normalized_query = query.casefold()
        return [
            deal
            for deal in self.list()
            if normalized_query in deal.identity.name.casefold()
            or (deal.identity.address is not None and normalized_query in deal.identity.address.casefold())
            or (deal.identity.sponsor is not None and normalized_query in deal.identity.sponsor.casefold())
            or (deal.identity.broker is not None and normalized_query in deal.identity.broker.casefold())
        ]

    def _path_for(self, deal_id: str) -> Path:
        return self.deals_dir / f"{deal_id}.json"

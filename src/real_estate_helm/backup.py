"""Backup, restore, and retention helpers for local repositories."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.serialization import deal_to_dict


@dataclass(frozen=True)
class BackupManifest:
    created_at: datetime
    deal_count: int


class BackupService:
    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository

    def create_backup(self, output_path: Path | str) -> BackupManifest:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        deals = self.repository.list()
        manifest = BackupManifest(created_at=datetime.now(UTC), deal_count=len(deals))
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps({"created_at": manifest.created_at.isoformat(), "deal_count": manifest.deal_count}),
            )
            for deal in deals:
                archive.writestr(f"deals/{deal.id}.json", json.dumps(deal_to_dict(deal), indent=2, sort_keys=True))
        return manifest

    @staticmethod
    def restore_backup(backup_path: Path | str, target_repository: JsonDealRepository) -> BackupManifest:
        with zipfile.ZipFile(backup_path) as archive:
            manifest_data = json.loads(archive.read("manifest.json"))
            for name in archive.namelist():
                if not name.startswith("deals/") or not name.endswith(".json"):
                    continue
                target_path = target_repository.deals_dir / Path(name).name
                target_path.write_bytes(archive.read(name))
        return BackupManifest(
            created_at=datetime.fromisoformat(manifest_data["created_at"]),
            deal_count=manifest_data["deal_count"],
        )


@dataclass(frozen=True)
class RetentionPolicy:
    retain_rejected: bool = True
    delete_resolved_alerts_after_days: int | None = None

    def apply_to_repository(self, repository: JsonDealRepository, *, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        changed = 0
        for deal in repository.list():
            original_alert_count = len(deal.alerts)
            if self.delete_resolved_alerts_after_days is not None:
                cutoff = now - timedelta(days=self.delete_resolved_alerts_after_days)
                deal.alerts = [
                    alert
                    for alert in deal.alerts
                    if alert.resolved_at is None or alert.resolved_at >= cutoff
                ]
            if len(deal.alerts) != original_alert_count:
                repository.save(deal)
                changed += 1
        return changed

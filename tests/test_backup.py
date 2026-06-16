from datetime import UTC, datetime, timedelta
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import Alert, AlertSeverity, Deal, DealIdentity
from real_estate_helm.backup import BackupService, RetentionPolicy
from real_estate_helm.repository import JsonDealRepository


class BackupAndRetentionTests(TestCase):
    def test_backup_and_restore_repository(self) -> None:
        with TemporaryDirectory() as source_dir, TemporaryDirectory() as target_dir:
            source = JsonDealRepository(source_dir)
            deal = Deal(DealIdentity("Backup Deal"))
            source.save(deal)
            backup_path = f"{source_dir}/backup.zip"

            manifest = BackupService(source).create_backup(backup_path)
            restored_manifest = BackupService.restore_backup(backup_path, JsonDealRepository(target_dir))

            self.assertEqual(manifest.deal_count, 1)
            self.assertEqual(restored_manifest.deal_count, 1)
            self.assertEqual(JsonDealRepository(target_dir).get(deal.id).identity.name, "Backup Deal")

    def test_retention_removes_old_resolved_alerts_but_preserves_deal(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Retention Deal"))
            alert = Alert("Resolved", AlertSeverity.LOW, "test", "unit", "old")
            alert.resolve()
            alert.resolved_at = datetime.now(UTC) - timedelta(days=40)
            deal.alerts.append(alert)
            repository.save(deal)

            changed = RetentionPolicy(delete_resolved_alerts_after_days=30).apply_to_repository(repository)

            self.assertEqual(changed, 1)
            self.assertEqual(repository.get(deal.id).alerts, [])

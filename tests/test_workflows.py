from decimal import Decimal
from datetime import UTC, datetime, timedelta
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import (
    Alert,
    AlertSeverity,
    AlertStatus,
    CashFlowRecord,
    CashFlowType,
    Deal,
    DealIdentity,
    DealStatus,
    NewsClassification,
    NewsEvent,
)
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.workflows import (
    BackgroundWorkflowRuntime,
    RetryPolicy,
    ScheduledWorkflowRunner,
    WorkflowAttemptStore,
    WorkflowEngine,
    WorkflowLockStore,
    WorkflowRun,
    WorkflowSchedule,
)


class WorkflowEngineTests(TestCase):
    def test_monitoring_workflow_checks_active_deals_and_persists_alerts(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Workflow Deal"))
            deal.change_status(DealStatus.ACQUIRED, "principal", "Closed")
            deal.projected_cash_flows.append(CashFlowRecord("2027-01", Decimal("100000"), CashFlowType.PROJECTED, "noi"))
            deal.actual_cash_flows.append(CashFlowRecord("2027-01", Decimal("90000"), CashFlowType.ACTUAL, "noi"))
            deal.news_events.append(
                NewsEvent("Tenant bankruptcy", "https://example.test", NewsClassification.MATERIAL_NEGATIVE)
            )
            ignored = Deal(DealIdentity("New Deal"))
            repository.save(deal)
            repository.save(ignored)

            run = WorkflowEngine(repository).run_monitoring(source_statuses={"news": False})

            self.assertEqual(run.deals_checked, 1)
            self.assertEqual(run.alerts_created, 3)
            self.assertEqual(len(repository.get(deal.id).alerts), 3)
            self.assertEqual(len(repository.get(ignored.id).alerts), 0)

    def test_monitoring_workflow_escalates_stale_alerts_and_queues_notifications(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Escalation Deal", owner="analyst@example.test"))
            deal.change_status(DealStatus.ACQUIRED, "principal", "Closed")
            deal.alerts.append(
                Alert(
                    "NOI below budget",
                    AlertSeverity.HIGH,
                    "cash_flow",
                    "monthly import",
                    "NOI is below plan.",
                    recommended_action="Call property manager.",
                    created_at=datetime(2020, 1, 1, tzinfo=UTC),
                )
            )
            repository.save(deal)

            run = WorkflowEngine(repository).run_monitoring(escalate_after_days=0)
            saved = repository.get(deal.id)

            self.assertEqual(run.notifications_queued, 1)
            self.assertEqual(saved.alerts[0].status, AlertStatus.ESCALATED)
            self.assertEqual(saved.notifications[0].recipient, "analyst@example.test")
            self.assertEqual(saved.notifications[0].entity_type, "alert")

    def test_scheduled_workflow_runner_only_runs_when_due(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Scheduled Deal"))
            deal.change_status(DealStatus.WATCHLIST, "analyst", "Track")
            repository.save(deal)
            runner = ScheduledWorkflowRunner(
                WorkflowEngine(repository),
                WorkflowSchedule("monitoring", timedelta(hours=1)),
            )
            now = datetime(2027, 1, 1, 12, tzinfo=UTC)

            first = runner.run_if_due(now=now)
            second = runner.run_if_due(now=now + timedelta(minutes=30))
            third = runner.run_if_due(now=now + timedelta(hours=1, minutes=1))

            self.assertIsNotNone(first)
            self.assertIsNone(second)
            self.assertIsNotNone(third)

    def test_background_runtime_records_successful_due_runs(self) -> None:
        now = datetime(2027, 1, 1, 12, tzinfo=UTC)
        runner = FakeRunner("monitoring", [WorkflowRun("monitoring", now, now, 1, 0)])
        runtime = BackgroundWorkflowRuntime([runner])

        attempts = runtime.tick(now=now)

        self.assertEqual(len(attempts), 1)
        self.assertTrue(attempts[0].succeeded)
        self.assertEqual(attempts[0].run.deals_checked, 1)

    def test_background_runtime_retries_failures_with_backoff(self) -> None:
        now = datetime(2027, 1, 1, 12, tzinfo=UTC)
        runner = FakeRunner("monitoring", [RuntimeError("source unavailable"), WorkflowRun("monitoring", now, now, 1, 0)])
        runtime = BackgroundWorkflowRuntime([runner], RetryPolicy(max_attempts=3, backoff=timedelta(minutes=10)))

        failed = runtime.tick(now=now)
        skipped = runtime.tick(now=now + timedelta(minutes=5))
        succeeded = runtime.tick(now=now + timedelta(minutes=10))

        self.assertFalse(failed[0].succeeded)
        self.assertEqual(failed[0].next_retry_at, now + timedelta(minutes=10))
        self.assertEqual(skipped, [])
        self.assertTrue(succeeded[0].succeeded)

    def test_background_runtime_persists_attempts_and_uses_locks(self) -> None:
        with TemporaryDirectory() as directory:
            now = datetime(2027, 1, 1, 12, tzinfo=UTC)
            runner = FakeRunner("monitoring", [WorkflowRun("monitoring", now, now, 1, 2)])
            lock_store = WorkflowLockStore(f"{directory}/locks")
            attempt_store = WorkflowAttemptStore(f"{directory}/attempts.jsonl")
            runtime = BackgroundWorkflowRuntime(
                [runner],
                attempt_store=attempt_store,
                lock_store=lock_store,
                owner="worker-a",
            )

            attempts = runtime.tick(now=now)

            self.assertEqual(len(attempts), 1)
            persisted = attempt_store.list()
            self.assertEqual(persisted[0]["run"]["alerts_created"], 2)
            self.assertTrue(lock_store.acquire("monitoring", "worker-b", ttl=timedelta(minutes=1), now=now))

    def test_workflow_lock_store_respects_owner_and_expiry(self) -> None:
        with TemporaryDirectory() as directory:
            locks = WorkflowLockStore(directory)
            now = datetime(2027, 1, 1, 12, tzinfo=UTC)

            self.assertTrue(locks.acquire("monitoring", "worker-a", ttl=timedelta(minutes=5), now=now))
            self.assertFalse(locks.acquire("monitoring", "worker-b", ttl=timedelta(minutes=5), now=now))
            self.assertTrue(
                locks.acquire("monitoring", "worker-b", ttl=timedelta(minutes=5), now=now + timedelta(minutes=6))
            )


class FakeRunner:
    def __init__(self, name, outcomes):
        self.schedule = WorkflowSchedule(name, timedelta(minutes=1))
        self.outcomes = list(outcomes)

    def is_due(self, now):
        return True

    def run_if_due(self, *, now):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

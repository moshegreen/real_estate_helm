"""Workflow primitives for scheduled monitoring and alert generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from real_estate_helm.domain import Deal, DealStatus
from real_estate_helm.monitoring import (
    add_new_alerts,
    escalate_stale_alerts,
    monitoring_alerts,
)
from real_estate_helm.notifications import build_alert_notifications
from real_estate_helm.repository import JsonDealRepository


@dataclass(frozen=True)
class WorkflowRun:
    name: str
    started_at: datetime
    finished_at: datetime
    deals_checked: int
    alerts_created: int
    notifications_queued: int = 0


@dataclass(frozen=True)
class WorkflowSchedule:
    name: str
    interval: timedelta


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff: timedelta = timedelta(minutes=5)


@dataclass(frozen=True)
class WorkflowAttempt:
    name: str
    attempted_at: datetime
    attempt_number: int
    succeeded: bool
    run: WorkflowRun | None = None
    error: str | None = None
    next_retry_at: datetime | None = None


class WorkflowAttemptStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, attempt: WorkflowAttempt) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(_attempt_to_dict(attempt), sort_keys=True) + "\n")

    def list(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]


class WorkflowLockStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def acquire(self, name: str, owner: str, *, ttl: timedelta, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        path = self._path(name)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            expires_at = datetime.fromisoformat(payload["expires_at"])
            if expires_at > now and payload["owner"] != owner:
                return False
        path.write_text(
            json.dumps({"name": name, "owner": owner, "expires_at": (now + ttl).isoformat()}, sort_keys=True),
            encoding="utf-8",
        )
        return True

    def release(self, name: str, owner: str) -> None:
        path = self._path(name)
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["owner"] == owner:
            path.unlink()

    def _path(self, name: str) -> Path:
        safe = name.replace("/", "_")
        return self.root / f"{safe}.lock.json"


@dataclass
class WorkflowEngine:
    repository: JsonDealRepository
    runs: list[WorkflowRun] = field(default_factory=list)

    def run_monitoring(
        self,
        selector: Callable[[Deal], bool] | None = None,
        *,
        source_statuses: dict[str, bool] | None = None,
        escalate_after_days: int | None = None,
        notification_recipient: str | None = None,
    ) -> WorkflowRun:
        started = datetime.now(UTC)
        selector = selector or _default_monitoring_selector
        checked = 0
        alerts_created = 0
        notifications_queued = 0
        for deal in self.repository.list():
            if not selector(deal):
                continue
            checked += 1
            alerts = monitoring_alerts(deal, source_statuses=source_statuses)
            alerts_created += add_new_alerts(deal, alerts)
            if escalate_after_days is not None:
                escalated = escalate_stale_alerts(deal, stale_days=escalate_after_days)
                notifications = build_alert_notifications(deal, escalated, recipient=notification_recipient)
                deal.notifications.extend(notifications)
                notifications_queued += len(notifications)
            self.repository.save(deal)
        run = WorkflowRun(
            name="monitoring",
            started_at=started,
            finished_at=datetime.now(UTC),
            deals_checked=checked,
            alerts_created=alerts_created,
            notifications_queued=notifications_queued,
        )
        self.runs.append(run)
        return run


@dataclass
class ScheduledWorkflowRunner:
    engine: WorkflowEngine
    schedule: WorkflowSchedule
    last_run_at: datetime | None = None

    def is_due(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        if self.last_run_at is None:
            return True
        return now - self.last_run_at >= self.schedule.interval

    def run_if_due(
        self,
        *,
        now: datetime | None = None,
        source_statuses: dict[str, bool] | None = None,
        escalate_after_days: int | None = None,
        notification_recipient: str | None = None,
    ) -> WorkflowRun | None:
        now = now or datetime.now(UTC)
        if not self.is_due(now):
            return None
        run = self.engine.run_monitoring(
            source_statuses=source_statuses,
            escalate_after_days=escalate_after_days,
            notification_recipient=notification_recipient,
        )
        self.last_run_at = now
        return run


@dataclass
class BackgroundWorkflowRuntime:
    runners: list[Any]
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    attempt_store: WorkflowAttemptStore | None = None
    lock_store: WorkflowLockStore | None = None
    owner: str = "local-worker"
    lock_ttl: timedelta = timedelta(minutes=15)
    attempts: list[WorkflowAttempt] = field(default_factory=list)
    failure_counts: dict[str, int] = field(default_factory=dict)
    retry_after: dict[str, datetime] = field(default_factory=dict)

    def tick(self, *, now: datetime | None = None) -> list[WorkflowAttempt]:
        now = now or datetime.now(UTC)
        attempts: list[WorkflowAttempt] = []
        for runner in self.runners:
            name = runner.schedule.name
            lock_acquired = False
            if self.lock_store is not None:
                lock_acquired = self.lock_store.acquire(name, self.owner, ttl=self.lock_ttl, now=now)
                if not lock_acquired:
                    continue
            if self.retry_after.get(name) and now < self.retry_after[name]:
                if lock_acquired:
                    self.lock_store.release(name, self.owner)
                continue
            if not runner.is_due(now):
                if lock_acquired:
                    self.lock_store.release(name, self.owner)
                continue
            attempt_number = self.failure_counts.get(name, 0) + 1
            try:
                run = runner.run_if_due(now=now)
                if run is None:
                    if lock_acquired:
                        self.lock_store.release(name, self.owner)
                    continue
                self.failure_counts.pop(name, None)
                self.retry_after.pop(name, None)
                attempt = WorkflowAttempt(name, now, attempt_number, True, run=run)
            except Exception as exc:
                self.failure_counts[name] = attempt_number
                next_retry_at = None
                if attempt_number < self.retry_policy.max_attempts:
                    next_retry_at = now + (self.retry_policy.backoff * attempt_number)
                    self.retry_after[name] = next_retry_at
                else:
                    self.retry_after.pop(name, None)
                attempt = WorkflowAttempt(
                    name,
                    now,
                    attempt_number,
                    False,
                    error=str(exc),
                    next_retry_at=next_retry_at,
                )
            self.attempts.append(attempt)
            if self.attempt_store is not None:
                self.attempt_store.append(attempt)
            attempts.append(attempt)
            if lock_acquired:
                self.lock_store.release(name, self.owner)
        return attempts


def _default_monitoring_selector(deal: Deal) -> bool:
    return deal.status in {DealStatus.WATCHLIST, DealStatus.ACQUIRED, DealStatus.DILIGENCE}


def _attempt_to_dict(attempt: WorkflowAttempt) -> dict[str, Any]:
    return {
        "name": attempt.name,
        "attempted_at": attempt.attempted_at.isoformat(),
        "attempt_number": attempt.attempt_number,
        "succeeded": attempt.succeeded,
        "error": attempt.error,
        "next_retry_at": attempt.next_retry_at.isoformat() if attempt.next_retry_at else None,
        "run": _run_to_dict(attempt.run) if attempt.run else None,
    }


def _run_to_dict(run: WorkflowRun) -> dict[str, Any]:
    return {
        "name": run.name,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat(),
        "deals_checked": run.deals_checked,
        "alerts_created": run.alerts_created,
        "notifications_queued": run.notifications_queued,
    }

"""Notification delivery adapter contracts and local outbox."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from real_estate_helm.domain import Alert, Deal, NotificationChannel, PushNotification


class NotificationProvider(Protocol):
    def send(self, notification: PushNotification) -> str:
        """Deliver a notification and return provider message id."""


@dataclass(frozen=True)
class NotificationDelivery:
    notification_id: str
    provider_message_id: str
    delivered_at: datetime


@dataclass
class InMemoryNotificationProvider:
    sent: list[PushNotification] = field(default_factory=list)

    def send(self, notification: PushNotification) -> str:
        self.sent.append(notification)
        return f"local-{len(self.sent)}"


class HttpPushNotificationProvider:
    def __init__(self, endpoint: str, *, api_key: str | None = None, fetcher: Any) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.fetcher = fetcher

    def send(self, notification: PushNotification) -> str:
        payload = {
            "channel": notification.channel.value,
            "recipient": notification.recipient,
            "title": notification.title,
            "body": notification.body,
            "entity_type": notification.entity_type,
            "entity_id": notification.entity_id,
        }
        response = self.fetcher(self.endpoint, _push_headers(self.api_key), payload)
        return response["message_id"]


class NotificationDeliveryService:
    def __init__(self, provider: NotificationProvider) -> None:
        self.provider = provider

    def deliver_pending(self, notifications: list[PushNotification]) -> list[NotificationDelivery]:
        deliveries = []
        for notification in notifications:
            message_id = self.provider.send(notification)
            deliveries.append(
                NotificationDelivery(
                    notification_id=notification.id,
                    provider_message_id=message_id,
                    delivered_at=datetime.now(UTC),
                )
            )
        return deliveries


def build_alert_notifications(
    deal: Deal,
    alerts: list[Alert],
    *,
    recipient: str | None = None,
    channel: NotificationChannel = NotificationChannel.ANDROID_PUSH,
) -> list[PushNotification]:
    target = recipient or deal.identity.owner
    if not target:
        return []
    notifications = []
    for alert in alerts:
        notifications.append(
            PushNotification(
                channel=channel,
                recipient=target,
                title=alert.title,
                body=alert.recommended_action or alert.description,
                entity_type="alert",
                entity_id=alert.id,
            )
        )
    return notifications


def _push_headers(api_key: str | None) -> dict[str, str]:
    headers = {"content-type": "application/json"}
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    return headers

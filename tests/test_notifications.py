from unittest import TestCase

from real_estate_helm import Alert, AlertSeverity, Deal, DealIdentity, NotificationChannel, PushNotification
from real_estate_helm.notifications import (
    build_alert_notifications,
    HttpPushNotificationProvider,
    InMemoryNotificationProvider,
    NotificationDeliveryService,
)


class NotificationTests(TestCase):
    def test_delivery_service_sends_pending_notifications(self) -> None:
        provider = InMemoryNotificationProvider()
        service = NotificationDeliveryService(provider)
        notification = PushNotification(
            channel=NotificationChannel.ANDROID_PUSH,
            recipient="principal",
            title="Alert",
            body="Review deal.",
        )

        deliveries = service.deliver_pending([notification])

        self.assertEqual(len(provider.sent), 1)
        self.assertEqual(deliveries[0].notification_id, notification.id)
        self.assertEqual(deliveries[0].provider_message_id, "local-1")

    def test_build_alert_notifications_targets_owner_or_override(self) -> None:
        deal = Deal(DealIdentity("Notify Deal", owner="owner@example.test"))
        alert = Alert("Debt maturity soon", AlertSeverity.HIGH, "debt", "debt_terms", "Loan matures soon.")

        owner_notifications = build_alert_notifications(deal, [alert])
        override_notifications = build_alert_notifications(deal, [alert], recipient="principal@example.test")

        self.assertEqual(owner_notifications[0].recipient, "owner@example.test")
        self.assertEqual(override_notifications[0].recipient, "principal@example.test")
        self.assertEqual(owner_notifications[0].entity_id, alert.id)

    def test_http_push_provider_posts_notification_payload(self) -> None:
        seen = {}

        def fetcher(url, headers, payload):
            seen["url"] = url
            seen["headers"] = headers
            seen["payload"] = payload
            return {"message_id": "push-1"}

        provider = HttpPushNotificationProvider("https://push.example.test/send", api_key="secret", fetcher=fetcher)
        message_id = provider.send(
            PushNotification(
                channel=NotificationChannel.ANDROID_PUSH,
                recipient="device-token",
                title="Alert",
                body="Review alert.",
                entity_type="alert",
                entity_id="alert-1",
            )
        )

        self.assertEqual(message_id, "push-1")
        self.assertEqual(seen["headers"]["authorization"], "Bearer secret")
        self.assertEqual(seen["payload"]["channel"], "android_push")
        self.assertEqual(seen["payload"]["entity_id"], "alert-1")

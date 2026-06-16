from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import (
    ApprovalStatus,
    Deal,
    DealIdentity,
    NotificationChannel,
)
from real_estate_helm.collaboration import CollaborationService
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.serialization import deal_from_dict, deal_to_dict


class CollaborationTests(TestCase):
    def test_comments_approvals_and_notifications_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Mobile Review Deal"))
            repository.save(deal)
            service = CollaborationService(repository)

            comment = service.add_comment(deal.id, author="advisor", body="Need zoning follow-up.")
            approval = service.request_approval(
                deal.id,
                title="Approve watchlist move",
                requested_by="analyst",
                approver="principal",
            )
            service.decide_approval(deal.id, approval.id, approved=True, note="Approved for watchlist.")
            notification = service.queue_notification(
                deal.id,
                channel=NotificationChannel.ANDROID_PUSH,
                recipient="principal",
                title="Approval requested",
                body="Review Mobile Review Deal.",
            )

            restored = deal_from_dict(deal_to_dict(repository.get(deal.id)))

            self.assertEqual(restored.comments[0].id, comment.id)
            self.assertEqual(restored.comments[0].body, "Need zoning follow-up.")
            self.assertEqual(restored.approval_requests[0].status, ApprovalStatus.APPROVED)
            self.assertEqual(restored.approval_requests[0].decision_note, "Approved for watchlist.")
            self.assertEqual(restored.notifications[0].id, notification.id)
            self.assertEqual(restored.notifications[0].channel, NotificationChannel.ANDROID_PUSH)

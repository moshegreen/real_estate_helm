"""Comments, approvals, and notification workflows for companion clients."""

from __future__ import annotations

from real_estate_helm.domain import (
    ApprovalRequest,
    Comment,
    NotificationChannel,
    PushNotification,
)
from real_estate_helm.repository import JsonDealRepository


class CollaborationService:
    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository

    def add_comment(
        self,
        deal_id: str,
        *,
        author: str,
        body: str,
        entity_type: str = "deal",
        entity_id: str | None = None,
    ) -> Comment:
        deal = self.repository.get(deal_id)
        comment = Comment(author=author, body=body, entity_type=entity_type, entity_id=entity_id or deal_id)
        deal.comments.append(comment)
        self.repository.save(deal)
        return comment

    def request_approval(
        self,
        deal_id: str,
        *,
        title: str,
        requested_by: str,
        approver: str,
        entity_type: str = "deal",
        entity_id: str | None = None,
    ) -> ApprovalRequest:
        deal = self.repository.get(deal_id)
        request = ApprovalRequest(
            title=title,
            requested_by=requested_by,
            approver=approver,
            entity_type=entity_type,
            entity_id=entity_id or deal_id,
        )
        deal.approval_requests.append(request)
        self.repository.save(deal)
        return request

    def decide_approval(self, deal_id: str, approval_id: str, *, approved: bool, note: str | None = None) -> ApprovalRequest:
        deal = self.repository.get(deal_id)
        request = next(item for item in deal.approval_requests if item.id == approval_id)
        if approved:
            request.approve(note)
        else:
            request.reject(note)
        self.repository.save(deal)
        return request

    def queue_notification(
        self,
        deal_id: str,
        *,
        channel: NotificationChannel,
        recipient: str,
        title: str,
        body: str,
        entity_type: str = "deal",
        entity_id: str | None = None,
    ) -> PushNotification:
        deal = self.repository.get(deal_id)
        notification = PushNotification(
            channel=channel,
            recipient=recipient,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id or deal_id,
        )
        deal.notifications.append(notification)
        self.repository.save(deal)
        return notification

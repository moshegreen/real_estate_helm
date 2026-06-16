"""Task workflows for desktop and mobile companion clients."""

from __future__ import annotations

from real_estate_helm.domain import Task, TaskStatus
from real_estate_helm.repository import JsonDealRepository


class TaskService:
    def __init__(self, repository: JsonDealRepository) -> None:
        self.repository = repository

    def create_task(
        self,
        deal_id: str,
        *,
        title: str,
        owner: str | None = None,
        due_date: str | None = None,
    ) -> Task:
        deal = self.repository.get(deal_id)
        task = Task(title=title, owner=owner, due_date=due_date)
        deal.tasks.append(task)
        self.repository.save(deal)
        return task

    def update_task_status(self, deal_id: str, task_id: str, status: TaskStatus) -> Task:
        deal = self.repository.get(deal_id)
        task = next(item for item in deal.tasks if item.id == task_id)
        task.status = status
        self.repository.save(deal)
        return task

    def tasks_for_owner(self, owner: str) -> list[tuple[str, Task]]:
        results = []
        for deal in self.repository.list():
            for task in deal.tasks:
                if task.owner == owner and task.status not in {TaskStatus.DONE, TaskStatus.CANCELED}:
                    results.append((deal.id, task))
        return results

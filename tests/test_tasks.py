from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import Deal, DealIdentity, TaskStatus
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.tasks import TaskService


class TaskServiceTests(TestCase):
    def test_create_complete_and_filter_mobile_tasks(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Task Deal"))
            repository.save(deal)
            service = TaskService(repository)

            task = service.create_task(deal.id, title="Review alert", owner="principal", due_date="2027-01-31")
            self.assertEqual(service.tasks_for_owner("principal")[0][1].title, "Review alert")

            service.update_task_status(deal.id, task.id, TaskStatus.DONE)

            self.assertEqual(service.tasks_for_owner("principal"), [])

from email.message import EmailMessage
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm.email_import import EmailDealImportService
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.services import DealService
from real_estate_helm.storage import LocalObjectStorage


class EmailDealImportServiceTests(TestCase):
    def test_create_deal_from_email_attaches_documents(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            storage = LocalObjectStorage(f"{directory}/objects")
            message = _email_bytes(
                subject="Harbor Email Deal",
                attachments={
                    "om.pdf": b"pdf",
                    "models/rent-roll.csv": b"csv",
                },
            )

            result = EmailDealImportService(repository, storage).create_deal_from_email(
                message,
                uploaded_by="analyst",
                owner="associate",
            )

            deal = repository.get(result.deal_id)
            self.assertEqual(result.subject, "Harbor Email Deal")
            self.assertEqual(result.sender, "broker@example.test")
            self.assertEqual(result.attachments_imported, 2)
            self.assertEqual(deal.identity.name, "Harbor Email Deal")
            self.assertEqual(deal.identity.source, "broker@example.test")
            self.assertEqual(deal.identity.owner, "associate")
            self.assertEqual(deal.documents[0].document_type.value, "pdf")
            self.assertEqual(deal.documents[1].name, "models/rent-roll.csv")
            self.assertEqual(storage.get_bytes(deal.documents[1].storage_uri), b"csv")

    def test_import_email_attachments_sanitizes_unsafe_names(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            storage = LocalObjectStorage(f"{directory}/objects")
            deal = DealService(repository).create_deal("Existing Deal")

            result = EmailDealImportService(repository, storage).import_email_attachments(
                deal.id,
                _email_bytes(attachments={"../outside.pdf": b"pdf"}),
                uploaded_by="analyst",
            )

            imported = repository.get(deal.id).documents[0]
            self.assertEqual(result.attachments_imported, 1)
            self.assertEqual(imported.name, "outside.pdf")
            self.assertTrue(imported.storage_uri.endswith("/outside.pdf"))


def _email_bytes(
    *,
    subject: str = "Attached Deal",
    attachments: dict[str, bytes],
) -> bytes:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = "broker@example.test"
    message.set_content("Please review the attached materials.")
    for filename, data in attachments.items():
        message.add_attachment(data, maintype="application", subtype="octet-stream", filename=filename)
    return message.as_bytes()

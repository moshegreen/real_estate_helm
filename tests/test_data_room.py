import zipfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import DataRoomImportService, Deal, DealIdentity, DocumentType
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.storage import LocalObjectStorage


class DataRoomImportTests(TestCase):
    def test_import_zip_stores_documents_and_skips_unsafe_entries(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Data Room Deal"))
            repository.save(deal)
            storage = LocalObjectStorage(f"{directory}/objects")
            service = DataRoomImportService(repository, storage)

            result = service.import_zip(
                deal.id,
                _zip_bytes(
                    {
                        "OM.pdf": b"pdf",
                        "models/underwriting.xlsx": b"xlsx",
                        "../secret.txt": b"bad",
                        "__MACOSX/metadata": b"skip",
                    }
                ),
                uploaded_by="analyst",
            )

            restored = repository.get(deal.id)
            self.assertEqual(result.documents_imported, 2)
            self.assertEqual(result.skipped_entries, ["../secret.txt", "__MACOSX/metadata"])
            self.assertEqual([document.document_type for document in restored.documents], [DocumentType.PDF, DocumentType.EXCEL])
            self.assertTrue(restored.documents[0].storage_uri.startswith("local://"))

    def test_import_directory_stores_nested_documents_and_skips_metadata(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Folder Deal"))
            repository.save(deal)
            folder = Path(directory) / "folder-room"
            (folder / "models").mkdir(parents=True)
            (folder / "OM.pdf").write_bytes(b"pdf")
            (folder / "models" / "rent-roll.csv").write_bytes(b"csv")
            (folder / ".DS_Store").write_bytes(b"metadata")

            result = DataRoomImportService(repository, LocalObjectStorage(f"{directory}/objects")).import_directory(
                deal.id,
                folder,
                uploaded_by="analyst",
            )

            restored = repository.get(deal.id)
            self.assertEqual(result.documents_imported, 2)
            self.assertEqual(len(result.skipped_entries), 1)
            self.assertEqual([document.name for document in restored.documents], ["OM.pdf", "models/rent-roll.csv"])
            self.assertEqual(restored.documents[1].document_type, DocumentType.CSV)


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()

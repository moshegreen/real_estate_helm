from tempfile import TemporaryDirectory
from unittest import TestCase
from datetime import UTC, datetime

from real_estate_helm.settings import StorageSettings
from real_estate_helm.storage import (
    EncryptedObjectStorage,
    LocalObjectStorage,
    s3_storage_from_settings,
    S3CompatibleObjectStorage,
    S3Credentials,
    S3HttpClient,
)


class LocalObjectStorageTests(TestCase):
    def test_put_and_get_bytes_with_hash_metadata(self) -> None:
        with TemporaryDirectory() as directory:
            storage = LocalObjectStorage(directory)

            stored = storage.put_bytes("documents/om.pdf", b"fake pdf bytes")

            self.assertEqual(stored.uri, "local://documents/om.pdf")
            self.assertEqual(stored.size_bytes, 14)
            self.assertEqual(
                stored.sha256,
                "a855ce33bc03967d815ff35813cb249c5d63582cd9ee3ac890ba3f864ac62998",
            )
            self.assertEqual(storage.get_bytes(stored.uri), b"fake pdf bytes")

    def test_encrypted_storage_round_trip_hides_plaintext(self) -> None:
        with TemporaryDirectory() as directory:
            local = LocalObjectStorage(directory)
            encrypted = EncryptedObjectStorage(local, b"0123456789abcdef")

            stored = encrypted.put_bytes("private/report.pdf", b"sensitive report")

            self.assertNotIn(b"sensitive report", local.get_bytes(stored.uri))
            self.assertEqual(encrypted.get_bytes(stored.uri), b"sensitive report")

    def test_s3_compatible_storage_delegates_with_metadata(self) -> None:
        client = RecordingS3Client()
        storage = S3CompatibleObjectStorage("deal-data-room", client)

        stored = storage.put_bytes("/reports/ic-memo.pdf", b"memo")

        self.assertEqual(stored.uri, "s3://deal-data-room/reports/ic-memo.pdf")
        self.assertEqual(stored.size_bytes, 4)
        self.assertEqual(client.puts[0]["bucket"], "deal-data-room")
        self.assertEqual(client.puts[0]["key"], "reports/ic-memo.pdf")
        self.assertEqual(client.puts[0]["metadata"]["size_bytes"], "4")
        self.assertEqual(storage.get_bytes(stored.uri), b"memo")

    def test_s3_http_client_signs_put_and_get_requests(self) -> None:
        opener = RecordingHttpOpener(response_body=b"memo")
        client = S3HttpClient(
            "http://minio:9000",
            S3Credentials("minio", "secret", "us-east-1"),
            opener=opener,
            clock=lambda: datetime(2027, 1, 2, 3, 4, 5, tzinfo=UTC),
        )

        client.put_object("deal-data", "reports/ic memo.pdf", b"memo", {"sha256": "abc", "size_bytes": "4"})
        body = client.get_object("deal-data", "reports/ic memo.pdf")

        put_request = opener.requests[0]
        get_request = opener.requests[1]
        self.assertEqual(body, b"memo")
        self.assertEqual(put_request.full_url, "http://minio:9000/deal-data/reports/ic%20memo.pdf")
        self.assertEqual(put_request.get_method(), "PUT")
        self.assertEqual(put_request.data, b"memo")
        self.assertIn("AWS4-HMAC-SHA256 Credential=minio/20270102/us-east-1/s3/aws4_request", _header(put_request, "authorization"))
        self.assertEqual(_header(put_request, "x-amz-date"), "20270102T030405Z")
        self.assertEqual(_header(put_request, "x-amz-meta-sha256"), "abc")
        self.assertEqual(get_request.get_method(), "GET")

    def test_s3_storage_from_settings_builds_real_http_client(self) -> None:
        opener = RecordingHttpOpener(response_body=b"memo")
        settings = StorageSettings(
            endpoint="http://minio:9000",
            bucket="deal-data",
            access_key="minio",
            secret_key="secret",
            region="us-west-2",
        )
        storage = s3_storage_from_settings(settings, opener=opener)

        stored = storage.put_bytes("exports/report.pdf", b"memo")

        self.assertEqual(stored.uri, "s3://deal-data/exports/report.pdf")
        self.assertIn("/us-west-2/s3/aws4_request", _header(opener.requests[0], "authorization"))


class RecordingS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.puts: list[dict[str, object]] = []

    def put_object(self, bucket: str, key: str, data: bytes, metadata: dict[str, str]) -> None:
        self.objects[(bucket, key)] = data
        self.puts.append({"bucket": bucket, "key": key, "data": data, "metadata": metadata})

    def get_object(self, bucket: str, key: str) -> bytes:
        return self.objects[(bucket, key)]


class RecordingHttpResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body


class RecordingHttpOpener:
    def __init__(self, response_body: bytes = b"") -> None:
        self.response_body = response_body
        self.requests = []

    def open(self, request):
        self.requests.append(request)
        return RecordingHttpResponse(self.response_body)


def _header(request, name: str) -> str:
    headers = {key.lower(): value for key, value in request.header_items()}
    return headers[name]

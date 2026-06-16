"""Object storage adapters for documents, images, reports, and exports."""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class StoredObject:
    uri: str
    sha256: str
    size_bytes: int


class ObjectStorage(Protocol):
    def put_bytes(self, key: str, data: bytes) -> StoredObject:
        """Store bytes under a key and return addressable metadata."""

    def get_bytes(self, uri: str) -> bytes:
        """Load bytes by URI."""


class S3ObjectClient(Protocol):
    def put_object(self, bucket: str, key: str, data: bytes, metadata: dict[str, str]) -> None:
        """Upload object bytes to an S3-compatible service."""

    def get_object(self, bucket: str, key: str) -> bytes:
        """Read object bytes from an S3-compatible service."""


@dataclass(frozen=True)
class S3Credentials:
    access_key: str
    secret_key: str
    region: str = "us-east-1"


class S3HttpClient:
    """Minimal path-style S3/MinIO client using AWS Signature Version 4."""

    def __init__(
        self,
        endpoint: str,
        credentials: S3Credentials,
        *,
        opener: Any | None = None,
        clock: Any | None = None,
    ) -> None:
        if not endpoint:
            raise ValueError("endpoint is required")
        if not credentials.access_key or not credentials.secret_key:
            raise ValueError("S3 access key and secret key are required")
        self.endpoint = endpoint.rstrip("/")
        self.credentials = credentials
        self.opener = opener or urlopen
        self.clock = clock or (lambda: datetime.now(UTC))

    def put_object(self, bucket: str, key: str, data: bytes, metadata: dict[str, str]) -> None:
        headers = {
            "content-length": str(len(data)),
            "content-type": "application/octet-stream",
            **{f"x-amz-meta-{name}": value for name, value in metadata.items()},
        }
        request = self._request("PUT", bucket, key, headers=headers, body=data)
        self._open(request)

    def get_object(self, bucket: str, key: str) -> bytes:
        request = self._request("GET", bucket, key, headers={}, body=b"")
        response = self._open(request)
        return response.read()

    def _request(self, method: str, bucket: str, key: str, *, headers: dict[str, str], body: bytes) -> Request:
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"invalid S3 endpoint: {self.endpoint}")
        encoded_path = "/".join(quote(part, safe="") for part in key.split("/"))
        base_path = parsed.path.rstrip("/")
        canonical_uri = f"{base_path}/{quote(bucket, safe='')}/{encoded_path}"
        url = f"{parsed.scheme}://{parsed.netloc}{canonical_uri}"
        now = self.clock()
        timestamp = now.strftime("%Y%m%dT%H%M%SZ")
        datestamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(body).hexdigest()
        signing_headers = {
            "host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": timestamp,
            **{name.lower(): value for name, value in headers.items()},
        }
        authorization = self._authorization(method, canonical_uri, signing_headers, payload_hash, datestamp)
        request_headers = {name: value for name, value in signing_headers.items()}
        request_headers["authorization"] = authorization
        return Request(url, data=body if method != "GET" else None, headers=request_headers, method=method)

    def _authorization(
        self,
        method: str,
        canonical_uri: str,
        headers: dict[str, str],
        payload_hash: str,
        datestamp: str,
    ) -> str:
        signed_header_names = sorted(headers)
        canonical_headers = "".join(f"{name}:{headers[name].strip()}\n" for name in signed_header_names)
        signed_headers = ";".join(signed_header_names)
        canonical_request = "\n".join(
            [method, canonical_uri, "", canonical_headers, signed_headers, payload_hash]
        )
        scope = f"{datestamp}/{self.credentials.region}/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                headers["x-amz-date"],
                scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            ]
        )
        signature = hmac.new(
            _s3_signing_key(self.credentials.secret_key, datestamp, self.credentials.region),
            string_to_sign.encode(),
            hashlib.sha256,
        ).hexdigest()
        return (
            f"AWS4-HMAC-SHA256 Credential={self.credentials.access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

    def _open(self, request: Request) -> Any:
        if hasattr(self.opener, "open"):
            return self.opener.open(request)
        return self.opener(request)


class LocalObjectStorage:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, key: str, data: bytes) -> StoredObject:
        safe_key = key.strip("/").replace("..", "_")
        path = self.root / safe_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        return StoredObject(uri=f"local://{safe_key}", sha256=digest, size_bytes=len(data))

    def get_bytes(self, uri: str) -> bytes:
        if not uri.startswith("local://"):
            raise ValueError(f"unsupported local storage uri: {uri}")
        key = uri.removeprefix("local://")
        path = (self.root / key).resolve()
        path.relative_to(self.root.resolve())
        return path.read_bytes()


class S3CompatibleObjectStorage:
    """Object storage adapter over an injected S3-compatible client.

    The core package stays dependency-free; production deployments can provide
    a boto3, MinIO, or gateway client that implements ``S3ObjectClient``.
    """

    def __init__(self, bucket: str, client: S3ObjectClient, uri_scheme: str = "s3") -> None:
        if not bucket:
            raise ValueError("bucket is required")
        self.bucket = bucket
        self.client = client
        self.uri_scheme = uri_scheme

    def put_bytes(self, key: str, data: bytes) -> StoredObject:
        safe_key = key.strip("/").replace("..", "_")
        if not safe_key:
            raise ValueError("object key is required")
        digest = hashlib.sha256(data).hexdigest()
        self.client.put_object(
            self.bucket,
            safe_key,
            data,
            metadata={"sha256": digest, "size_bytes": str(len(data))},
        )
        return StoredObject(uri=f"{self.uri_scheme}://{self.bucket}/{safe_key}", sha256=digest, size_bytes=len(data))

    def get_bytes(self, uri: str) -> bytes:
        prefix = f"{self.uri_scheme}://{self.bucket}/"
        if not uri.startswith(prefix):
            raise ValueError(f"unsupported S3 storage uri: {uri}")
        key = uri.removeprefix(prefix)
        return self.client.get_object(self.bucket, key)


def s3_storage_from_settings(storage_settings: Any, *, opener: Any | None = None) -> S3CompatibleObjectStorage:
    credentials = S3Credentials(
        access_key=storage_settings.access_key,
        secret_key=storage_settings.secret_key,
        region=getattr(storage_settings, "region", "us-east-1"),
    )
    client = S3HttpClient(storage_settings.endpoint, credentials, opener=opener)
    return S3CompatibleObjectStorage(storage_settings.bucket, client)


class EncryptedObjectStorage:
    """Encrypt objects before delegating to another storage adapter.

    This standard-library implementation is meant for local development and
    tests. Production deployments should replace it with cloud KMS or a vetted
    encryption library.
    """

    def __init__(self, delegate: ObjectStorage, key: bytes) -> None:
        if len(key) < 16:
            raise ValueError("encryption key must be at least 16 bytes")
        self.delegate = delegate
        self.key = key

    def put_bytes(self, key: str, data: bytes) -> StoredObject:
        nonce = os.urandom(16)
        ciphertext = _xor_stream(data, self.key, nonce)
        mac = hmac.new(self.key, nonce + ciphertext, hashlib.sha256).digest()
        return self.delegate.put_bytes(key, b"REH1" + nonce + mac + ciphertext)

    def get_bytes(self, uri: str) -> bytes:
        payload = self.delegate.get_bytes(uri)
        if not payload.startswith(b"REH1"):
            raise ValueError("invalid encrypted payload")
        nonce = payload[4:20]
        mac = payload[20:52]
        ciphertext = payload[52:]
        expected = hmac.new(self.key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            raise ValueError("encrypted payload authentication failed")
        return _xor_stream(ciphertext, self.key, nonce)


def _xor_stream(data: bytes, key: bytes, nonce: bytes) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < len(data):
        block = hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest()
        output.extend(block)
        counter += 1
    return bytes(byte ^ stream for byte, stream in zip(data, output))


def _s3_signing_key(secret_key: str, datestamp: str, region: str) -> bytes:
    date_key = hmac.new(f"AWS4{secret_key}".encode(), datestamp.encode(), hashlib.sha256).digest()
    region_key = hmac.new(date_key, region.encode(), hashlib.sha256).digest()
    service_key = hmac.new(region_key, b"s3", hashlib.sha256).digest()
    return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()

"""Environment-backed configuration for local and deployed runtime modes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class StorageSettings:
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: str = "us-east-1"

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.bucket and self.access_key and self.secret_key)


@dataclass(frozen=True)
class ProviderSettings:
    geocoder_api_key: str = ""
    market_comp_api_key: str = ""
    news_api_key: str = ""
    imagery_api_key: str = ""
    web_source_api_key: str = ""
    ocr_api_key: str = ""
    llm_api_key: str = ""

    @property
    def configured_providers(self) -> tuple[str, ...]:
        configured = []
        for name, value in self.__dict__.items():
            if value:
                configured.append(name.removesuffix("_api_key"))
        return tuple(configured)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    auth_secret: str
    postgres_dsn: str
    redis_url: str
    storage: StorageSettings
    providers: ProviderSettings

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ
        return cls(
            data_dir=Path(env.get("REAL_ESTATE_HELM_DATA_DIR", ".real_estate_helm")),
            auth_secret=env.get("REAL_ESTATE_HELM_AUTH_SECRET", ""),
            postgres_dsn=env.get("POSTGRES_DSN", ""),
            redis_url=env.get("REDIS_URL", ""),
            storage=StorageSettings(
                endpoint=env.get("S3_ENDPOINT", ""),
                bucket=env.get("S3_BUCKET", ""),
                access_key=env.get("S3_ACCESS_KEY", ""),
                secret_key=env.get("S3_SECRET_KEY", ""),
                region=env.get("S3_REGION", "us-east-1"),
            ),
            providers=ProviderSettings(
                geocoder_api_key=env.get("GEOCODER_API_KEY", ""),
                market_comp_api_key=env.get("MARKET_COMP_API_KEY", ""),
                news_api_key=env.get("NEWS_API_KEY", ""),
                imagery_api_key=env.get("IMAGERY_API_KEY", ""),
                web_source_api_key=env.get("WEB_SOURCE_API_KEY", ""),
                ocr_api_key=env.get("OCR_API_KEY", ""),
                llm_api_key=env.get("LLM_API_KEY", ""),
            ),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.auth_secret and len(self.auth_secret.encode("utf-8")) < 16:
            errors.append("REAL_ESTATE_HELM_AUTH_SECRET must be at least 16 bytes")

        storage_values = [
            self.storage.endpoint,
            self.storage.bucket,
            self.storage.access_key,
            self.storage.secret_key,
        ]
        if any(storage_values) and not all(storage_values):
            errors.append("S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, and S3_SECRET_KEY must be set together")

        return errors

# Deployment Notes

This repository is dependency-light by default. The local API can run from the source tree, while `docker-compose.yml` defines the target production services: API, PostGIS, MinIO-compatible object storage, and Redis.

## Local API

```sh
PYTHONPATH=src python3 -m real_estate_helm.server --host 127.0.0.1 --port 8799
```

Open `http://127.0.0.1:8799/` for the static dashboard or call `/api/health` for an API health check.

## Compose Stack

```sh
cp .env.example .env
docker compose up --build
```

Set `REAL_ESTATE_HELM_AUTH_SECRET` to at least 16 bytes before exposing the API. Configure `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY` together; partial object-storage settings are rejected by `Settings.validate()`. `S3_REGION` defaults to `us-east-1` and is used by the built-in SigV4 MinIO/S3 client.

Validate runtime settings before starting services:

```sh
PYTHONPATH=src python3 -m real_estate_helm validate-config
```

## Release Automation

`.github/workflows/ci.yml` runs the Python test suite, bytecode compile check, and API image build. `.github/workflows/release.yml` is a manual workflow that records the container, Windows desktop, and Android mobile packaging entry points until signing credentials and dependency installation are finalized.

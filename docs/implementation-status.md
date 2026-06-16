# Implementation Status

This repository now implements the local backend foundation for `plan.md`.

## Implemented

- Canonical deal state for deals, assets, documents, document pages/tables, extracted facts, assumptions, scenarios, cash flows, debt, tenants, leases, rent-roll records, capex, development milestones, comps, property records, permit events, web/news/imagery, alerts, tasks, obligations, investment decisions, users, and audit log.
- Mobile collaboration state for comments, approval requests, and queued notifications.
- API routes for comments, approval requests, approval decisions, intake, monitoring, memos, and portfolio intelligence.
- Request validation models and structured API validation errors.
- HMAC bearer-token authenticator and secured API router wrapper.
- Object-level access policy for deal ownership, explicit deal grants, and document-specific grants.
- TOTP MFA code generation/verification and MFA-verified token claims for high-risk authorization flows.
- Export-control policy for sensitive deal exports, data-room archive access, and redacted deal JSON.
- JSON persistence, serialization, local CLI workflows, and a dependency-free API router.
- Zipped data-room import workflow that stores files through object storage and attaches typed document records via API and CLI.
- Local folder import workflow for diligence/data-room folders with safe relative paths, metadata skipping, typed documents, and object-storage persistence via API and CLI.
- Email deal import workflow that creates deals from `.eml` messages, stores attachments through object storage, sanitizes attachment names, and exposes API/CLI paths for new and existing deals.
- Document-page provenance records for OCR text, page images, extracted tables, and review source highlighting via API and CLI.
- Standard-library HTTP server that serves the JSON API and browser dashboard scaffold.
- Optional FastAPI app factory over the same API router.
- Browser dashboard scaffold for portfolio metrics, Kanban-style pipeline with plan-level card metadata, deal intake, deal detail, document review, financial model, market context, monitoring alerts, and IC memo preview.
- Coordinate intake via API/CLI and browser map handoff links for geocoded assets.
- Windows React/TypeScript app scaffold for the desktop workflow.
- Android React Native companion scaffold for alerts, quick deal summaries, mobile map handoff, and document preview links.
- Docker/Compose deployment scaffold for API, PostGIS, MinIO, and Redis.
- Environment template for database, object storage, auth, and provider credentials.
- Environment-backed runtime settings with validation for auth, provider keys, and object-storage configuration.
- CLI config validation command for checking deployment settings before startup.
- Tauri Windows packaging config and Android Gradle/manifest scaffold.
- Document/spreadsheet extraction proposal plumbing with mandatory human review before assumptions are promoted.
- Re-extraction request workflow for low-confidence or disputed extracted facts, including fact status updates, generated follow-up tasks, and audit entries via API/CLI.
- OCR/LLM-style document extraction and summary provider contracts with static test adapters.
- HTTP JSON OCR/document-AI extraction and LLM summary adapters with confidence calibration.
- Deterministic underwriting math for ratios, loan-to-cost, break-even occupancy, exit value, development spread, NPV, IRR, payback, variance, and sensitivities.
- Scenario cloning, scenario output comparison, and assumption comparison.
- Sponsor spreadsheet comparison against canonical assumptions plus scenario CSV export.
- Scenario assumption update workflow with actor/rationale audit logging and changed-output traces.
- Monitoring rules for cash-flow variance and development delays.
- Monitoring rules for debt maturity, DSCR covenant breaches, source health failures, material local news, permit risk, property reassessments, and comparable-sale downside signals.
- Monitoring rules for legal deadlines, document expirations, and capital calls.
- Monitoring rules for insurance cost increases and development contingency consumption.
- Monitoring rules for sponsor litigation mentions, tenant credit/bankruptcy risk, and nearby competing development.
- Portfolio analytics for dashboard metrics, value/equity/gain rollups, sponsor/geography/asset exposure, debt maturities, capital calls, open alerts, rejected-deal hindsight, and actual-vs-underwritten variance.
- Deterministic natural-language portfolio Q&A for alerts, rejected-deal hindsight, exposure, status, and actual-vs-underwritten questions via API and CLI.
- Income-asset analytics for rent-roll occupancy, vacancy, concessions, bad debt, market-rent gap, lease expiry schedule, tenant concentration, and weighted average lease term.
- Geospatial analytics for radius searches and exposure by geography.
- Provider adapter contracts for geocoding, market comps, local news, imagery, and web sources.
- Provider adapter contracts and HTTP JSON adapters for geocoding, market comps, property data, permits, local news, imagery, and web-source providers.
- Structured location-context enrichment for roads/transit/schools/employment centers/environmental risks/nearby construction and competing properties.
- Local object storage adapter with URI, size, and SHA-256 metadata for document/report storage.
- S3-compatible object storage adapter with metadata plus standard-library SigV4 HTTP client wiring for MinIO/S3.
- Encrypted local object storage wrapper for development encrypted-at-rest behavior.
- Backup/restore service and retention policy cleanup for resolved alerts.
- Notification delivery adapter contract with local in-memory provider.
- HTTP push notification provider adapter for Android/desktop/email gateway integration.
- Workflow engine primitive for scheduled monitoring runs across active deals.
- Scheduled workflow runner with interval-based due checks.
- Background workflow runtime for due schedule execution, attempt tracking, retry limits, and backoff.
- File-backed workflow attempt log and lock store for durable local worker coordination boundaries.
- Alert escalation rules for stale high/critical alerts.
- Escalated alert notification queueing for Android/desktop/email provider handoff.
- Task workflow service for mobile/desktop task assignment and completion.
- Source health alert rules for failed external feeds.
- Expanded Markdown IC memo with thesis, property details, sponsor details, sources and uses, debt terms, projected returns, scenario table, sensitivity snapshot, comps, map/local context, red flags, recommendation, source citations, and human approval marker.
- Portfolio, monitoring, monthly performance, development progress, lender covenant, and rejected-deal review reports plus JSON, CSV, PDF, XLSX, and PPTX exports, including CLI artifact writers.
- PostgreSQL/PostGIS target schema draft.
- PostgreSQL SQL mapper, migration runner, and DB-API execution adapter for parameterized deal upsert statements.
- CI workflow for unit tests, bytecode compile checks, and API image builds.
- Manual release workflow for container image, signed Windows desktop bundles, and signed Android mobile artifacts.
- Deployment notes for local API, Compose stack, configuration validation, and release automation.

## Remaining Product Work

- Production Pydantic/FastAPI middleware hardening and external SSO/MFA provider integration.
- Production export approval workflows, audit attestations, and legal/compliance policy mapping.
- Live PostgreSQL integration tests against a running database.
- Live S3/MinIO integration tests and bucket lifecycle policies for PDFs, Excel files, images, reports, and data-room archives.
- Production OCR/document AI and LLM vendor tuning, prompt governance, natural-language Q&A expansion, and confidence calibration datasets.
- Real credentialed vendor tuning and legal/compliance review for map, satellite, property data, news, permit, OCR, LLM, and comp providers.
- Windows installer notarization/distribution hardening and release-channel approvals.
- Android native map SDK integration, authenticated document preview downloads, store metadata, and device QA.
- Production Redis/Postgres worker deployment with distributed locks, observability dashboards, and alert escalation SLAs.
- Production-grade branded PDF, Excel, and PowerPoint rendering fidelity.

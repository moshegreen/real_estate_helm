# Repository Guidelines

## Project Structure & Module Organization

Treat `plan.md` as the source of truth for product scope, domain language, workflows, and concepts such as `Deal`, facts, assumptions, scenarios, alerts, and monitoring feeds.

The repository starts with a local-first Python backend:

- `src/real_estate_helm/` for domain records, JSON persistence, CLI, API, intake, enrichment, analytics, monitoring, reporting, security, and underwriting.
- `schema/postgres.sql` for the planned PostgreSQL/PostGIS server schema.
- `tests/` for automated unit tests.
- `web/` for the browser dashboard scaffold.
- `apps/windows/` and `apps/android/` for desktop and mobile client scaffolds.
- `docs/` for implementation status and architecture notes.

Avoid mixing generated files, sample deal data, and source code in the root.

## Build, Test, and Development Commands

Use the standard library test runner for the current codebase:

- `PYTHONPATH=src python3 -m unittest discover -s tests`: run all tests.
- `python3 -m compileall src tests`: syntax-check Python modules.
- `PYTHONPATH=src python3 -m real_estate_helm --data-dir .real_estate_helm create-deal "Example Deal"`: create a local deal record.
- `PYTHONPATH=src python3 -m real_estate_helm --data-dir .real_estate_helm list-deals`: list local deal records.
- `PYTHONPATH=src python3 -m real_estate_helm --data-dir .real_estate_helm portfolio-summary`: summarize local deals.
- `PYTHONPATH=src python3 -m real_estate_helm.server --data-dir .real_estate_helm`: run the local HTTP API and dashboard.

Add framework-specific commands when the Windows desktop or Android apps are introduced.

## Coding Style & Naming Conventions

Use 4-space indentation for Python and type annotations for public APIs. Keep Markdown concise and prefer domain terms from `plan.md`.

Use clear names that preserve the product model: `Deal`, `Assumption`, `ExtractedFact`, `Scenario`, `Alert`, and `CashFlowUpdate` are preferable to vague names like `Item` or `Record`.

## Testing Guidelines

Tests currently use `unittest`. Include tests for deal intake, document extraction review, underwriting calculations, and status transitions. Name tests after behavior, for example `test_rejected_deal_preserves_decision_history`.

Keep fixtures small and anonymized. Do not commit confidential offering memoranda, rent rolls, bank records, or personally identifiable information.

## Commit & Pull Request Guidelines

Use short, imperative commit messages such as `Add deal intake model` or `Document underwriting assumptions`.

Pull requests should include a summary, reason for the change, testing performed, and screenshots or sample outputs for user-facing work. Link related issues or planning sections.

## Security & Configuration Tips

Real-estate documents may contain sensitive financial and personal data. Keep secrets, raw deal documents, local `.real_estate_helm/` data, and private investor materials out of git. Use environment variables or ignored local files for API keys and service credentials.

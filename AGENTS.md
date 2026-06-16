# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains the product plan for a real-estate investment dashboard and analysis tool. Treat `plan.md` as the source of truth for scope, domain language, workflows, and concepts such as `Deal`, extracted facts, assumptions, scenarios, alerts, and monitoring feeds.

The repository now starts with a small Python domain package:

- `src/real_estate_helm/` for core deal, scenario, fact, assumption, and underwriting logic.
- `tests/` for automated unit tests.
- `assets/` for images, icons, sample documents, or fixtures.
- `docs/` for architecture notes beyond the main plan.

Avoid mixing generated files, sample deal data, and source code in the repository root.

## Build, Test, and Development Commands

Use the standard library test runner for the current codebase:

- `PYTHONPATH=src python3 -m unittest discover -s tests`: run all tests.
- `python3 -m compileall src tests`: syntax-check Python modules.

Add framework-specific commands here when the Windows desktop or Android apps are introduced.

## Coding Style & Naming Conventions

Use 4-space indentation for Python and type annotations for public domain APIs. Keep Markdown concise, use sentence-case headings where practical, and prefer concrete domain terms from `plan.md`.

Use clear names that preserve the product model: `Deal`, `Assumption`, `ExtractedFact`, `Scenario`, `Alert`, and `CashFlowUpdate` are preferable to vague names like `Item` or `Record`.

## Testing Guidelines

Tests currently use `unittest`. Include tests for deal intake, document extraction review, underwriting calculations, and status transitions. Name tests after behavior, for example `test_rejected_deal_preserves_decision_history`.

Keep fixtures small and anonymized. Do not commit confidential offering memoranda, rent rolls, bank records, or personally identifiable information.

## Commit & Pull Request Guidelines

This repository has no commit history yet, so no local convention is established. Use short, imperative commit messages such as `Add deal intake model` or `Document underwriting assumptions`.

Pull requests should include a summary, reason for the change, testing performed, and screenshots or sample outputs for user-facing work. Link related issues or planning sections.

## Security & Configuration Tips

Real-estate documents may contain sensitive financial and personal data. Keep secrets, raw deal documents, and private investor materials out of git. Use environment variables or ignored local files for API keys and service credentials.

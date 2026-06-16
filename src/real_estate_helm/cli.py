"""Command line interface for local deal intake and review."""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any, TextIO

from real_estate_helm.analytics import portfolio_dashboard_metrics, rejected_deal_hindsight
from real_estate_helm.cash_flow_import import CashFlowImportService
from real_estate_helm.crm_import import CrmImportService
from real_estate_helm.data_room import DataRoomImportService
from real_estate_helm.email_import import EmailDealImportService
from real_estate_helm.domain import (
    Address,
    CashFlowType,
    Coordinates,
    DealStatus,
    DocumentReference,
    DocumentType,
    FactReviewStatus,
    ObligationType,
    SourceKind,
)
from real_estate_helm.intake import IntakeService
from real_estate_helm.extraction import ExtractionService, interpret_spreadsheet_cells, proposals_from_spreadsheet
from real_estate_helm.exports import render_cash_flow_xlsx, render_deal_summary_pdf, render_ic_memo_pptx
from real_estate_helm.monitoring import add_new_alerts, monitoring_alerts
from real_estate_helm.obligation_import import ObligationImportService
from real_estate_helm.portfolio_qa import PortfolioQuestionAnswerer
from real_estate_helm.reporting import (
    generate_asset_monitoring_report_markdown,
    generate_development_progress_report_markdown,
    generate_ic_memo_markdown,
    generate_lender_covenant_report_markdown,
    generate_monthly_performance_report_markdown,
)
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.scenarios import export_scenario_csv
from real_estate_helm.serialization import deal_to_dict
from real_estate_helm.services import DealService
from real_estate_helm.settings import Settings
from real_estate_helm.storage import LocalObjectStorage


def main(argv: list[str] | None = None, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-config":
        settings = Settings.from_env()
        errors = settings.validate()
        if errors:
            for error in errors:
                print(f"config-error {error}", file=stderr or sys.stderr)
            return 1
        configured = ",".join(settings.providers.configured_providers) or "none"
        storage = "configured" if settings.storage.configured else "local-only"
        print(f"config-ok storage={storage} providers={configured}", file=stdout)
        return 0

    repository = JsonDealRepository(args.data_dir)
    service = DealService(repository)
    intake = IntakeService(repository)
    extraction = ExtractionService(repository)

    if args.command == "create-deal":
        deal = service.create_deal(
            args.name,
            address=args.address,
            parcel=args.parcel,
            asset_type=args.asset_type,
            sponsor=args.sponsor,
            broker=args.broker,
            seller=args.seller,
            source=args.source,
            owner=args.owner,
        )
        print(f"created {deal.id} {deal.identity.name}", file=stdout)
        return 0

    if args.command == "list-deals":
        status = DealStatus(args.status) if args.status else None
        deals = repository.search(args.query) if args.query else repository.list(status=status)
        if args.query and status:
            deals = [deal for deal in deals if deal.status == status]
        for deal in deals:
            print(_deal_summary(deal), file=stdout)
        return 0

    if args.command == "show-deal":
        deal = repository.get(args.deal_id)
        print(json.dumps(deal_to_dict(deal), indent=2, sort_keys=True), file=stdout)
        return 0

    if args.command == "add-asset":
        deal = intake.add_asset(
            args.deal_id,
            args.name,
            address=Address(args.address, city=args.city, state=args.state, country=args.country)
            if args.address
            else None,
            coordinates=Coordinates(args.latitude, args.longitude)
            if args.latitude is not None and args.longitude is not None
            else None,
            asset_type=args.asset_type,
            unit_count=args.unit_count,
        )
        print(f"added-asset {deal.assets[-1].id} {deal.assets[-1].name}", file=stdout)
        return 0

    if args.command == "add-document":
        deal = intake.add_document(
            args.deal_id,
            name=args.name,
            document_type=DocumentType(args.document_type),
            storage_uri=args.storage_uri,
            uploaded_by=args.uploaded_by,
            sha256=args.sha256,
        )
        print(f"added-document {deal.documents[-1].id} {deal.documents[-1].name}", file=stdout)
        return 0

    if args.command == "add-document-page":
        tables = json.loads(args.extracted_tables_json) if args.extracted_tables_json else []
        deal = intake.add_document_page(
            args.deal_id,
            document_id=args.document_id,
            page_number=args.page_number,
            text_content=args.text_content,
            image_uri=args.image_uri,
            extracted_tables=tables,
        )
        page = deal.document_pages[-1]
        print(f"added-document-page {page.id} document={page.document_id} page={page.page_number}", file=stdout)
        return 0

    if args.command == "import-data-room":
        storage = LocalObjectStorage(args.storage_root or (args.data_dir / "objects"))
        result = DataRoomImportService(repository, storage).import_zip(
            args.deal_id,
            args.zip_path.read_bytes(),
            uploaded_by=args.uploaded_by,
            key_prefix=args.key_prefix,
        )
        print(
            json.dumps(
                {"documents_imported": result.documents_imported, "skipped_entries": result.skipped_entries},
                indent=2,
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    if args.command == "import-folder":
        storage = LocalObjectStorage(args.storage_root or (args.data_dir / "objects"))
        result = DataRoomImportService(repository, storage).import_directory(
            args.deal_id,
            args.folder_path,
            uploaded_by=args.uploaded_by,
            key_prefix=args.key_prefix,
        )
        print(
            json.dumps(
                {"documents_imported": result.documents_imported, "skipped_entries": result.skipped_entries},
                indent=2,
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    if args.command == "import-email":
        storage = LocalObjectStorage(args.storage_root or (args.data_dir / "objects"))
        result = EmailDealImportService(repository, storage).create_deal_from_email(
            args.email_path.read_bytes(),
            uploaded_by=args.uploaded_by,
            owner=args.owner,
        )
        print(
            json.dumps(
                {
                    "deal_id": result.deal_id,
                    "subject": result.subject,
                    "sender": result.sender,
                    "attachments_imported": result.attachments_imported,
                },
                indent=2,
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    if args.command == "import-email-attachments":
        storage = LocalObjectStorage(args.storage_root or (args.data_dir / "objects"))
        result = EmailDealImportService(repository, storage).import_email_attachments(
            args.deal_id,
            args.email_path.read_bytes(),
            uploaded_by=args.uploaded_by,
            key_prefix=args.key_prefix,
        )
        print(
            json.dumps(
                {
                    "deal_id": result.deal_id,
                    "subject": result.subject,
                    "sender": result.sender,
                    "attachments_imported": result.attachments_imported,
                },
                indent=2,
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    if args.command == "import-crm":
        result = CrmImportService(repository).import_csv(
            args.csv_path.read_text(encoding="utf-8-sig"),
            default_owner=args.default_owner,
        )
        print(
            json.dumps(
                {
                    "imported_rows": result.imported_rows,
                    "skipped_rows": result.skipped_rows,
                    "deal_ids": result.deal_ids,
                },
                indent=2,
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    if args.command == "add-cash-flow":
        deal = intake.add_cash_flow(
            args.deal_id,
            period=args.period,
            amount=Decimal(args.amount),
            cash_flow_type=CashFlowType(args.cash_flow_type),
            category=args.category,
        )
        records = deal.projected_cash_flows if args.cash_flow_type == CashFlowType.PROJECTED.value else deal.actual_cash_flows
        record = records[-1]
        print(f"added-cash-flow {record.id} {record.period} {record.category}", file=stdout)
        return 0

    if args.command == "import-cash-flows":
        result = CashFlowImportService(repository).import_csv(
            args.deal_id,
            args.csv_path.read_text(encoding="utf-8-sig"),
            default_type=CashFlowType(args.default_type),
        )
        print(
            json.dumps(
                {"imported_rows": result.imported_rows, "skipped_rows": result.skipped_rows},
                indent=2,
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    if args.command == "import-bank-statement":
        result = CashFlowImportService(repository).import_bank_statement_csv(
            args.deal_id,
            args.csv_path.read_text(encoding="utf-8-sig"),
            default_category=args.default_category,
        )
        print(
            json.dumps(
                {"imported_rows": result.imported_rows, "skipped_rows": result.skipped_rows},
                indent=2,
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    if args.command == "import-imagery":
        storage = LocalObjectStorage(args.storage_root or (args.data_dir / "objects"))
        filename = _safe_filename(args.image_path.name)
        stored = storage.put_bytes(f"deals/{args.deal_id}/imagery/{filename}", args.image_path.read_bytes())
        deal = intake.add_imagery_snapshot(
            args.deal_id,
            captured_at=args.captured_at,
            storage_uri=stored.uri,
            source=args.source,
            notes=args.notes,
        )
        snapshot = deal.imagery_snapshots[-1]
        print(
            json.dumps(
                {
                    "snapshot_id": snapshot.id,
                    "captured_at": snapshot.captured_at,
                    "source": snapshot.source,
                    "storage_uri": snapshot.storage_uri,
                },
                indent=2,
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    if args.command == "add-rent-roll":
        source = (
            DocumentReference(
                SourceKind(args.source_kind),
                args.source_name,
                page=args.page,
                sheet=args.sheet,
                cell=args.cell,
                context=args.context,
            )
            if args.source_name
            else None
        )
        deal = intake.add_rent_roll_entry(
            args.deal_id,
            as_of_date=args.as_of_date,
            unit=args.unit,
            tenant_name=args.tenant_name,
            monthly_rent=Decimal(args.monthly_rent) if args.monthly_rent is not None else None,
            market_rent=Decimal(args.market_rent) if args.market_rent is not None else None,
            occupied=not args.vacant,
            concessions=Decimal(args.concessions) if args.concessions is not None else None,
            bad_debt=Decimal(args.bad_debt) if args.bad_debt is not None else None,
            lease_start=args.lease_start,
            lease_end=args.lease_end,
            source=source,
        )
        entry = deal.rent_roll[-1]
        print(f"added-rent-roll {entry.id} {entry.unit}", file=stdout)
        return 0

    if args.command == "add-obligation":
        deal = intake.add_obligation(
            args.deal_id,
            title=args.title,
            due_date=args.due_date,
            obligation_type=ObligationType(args.obligation_type),
            amount=Decimal(args.amount) if args.amount is not None else None,
            source=args.source,
            owner=args.owner,
        )
        obligation = deal.obligations[-1]
        print(f"added-obligation {obligation.id} {obligation.obligation_type.value}", file=stdout)
        return 0

    if args.command == "import-obligations":
        result = ObligationImportService(repository).import_csv(
            args.deal_id,
            args.csv_path.read_text(encoding="utf-8-sig"),
        )
        print(
            json.dumps(
                {"imported_rows": result.imported_rows, "skipped_rows": result.skipped_rows},
                indent=2,
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    if args.command == "add-fact":
        deal = service.add_extracted_fact(
            args.deal_id,
            field_name=args.field,
            value=_parse_value(args.value, args.value_type),
            confidence=args.confidence,
            source=DocumentReference(
                source_kind=SourceKind(args.source_kind),
                name=args.source_name,
                page=args.page,
                sheet=args.sheet,
                cell=args.cell,
                context=args.context,
            ),
        )
        fact = deal.extracted_facts[-1]
        print(f"added-fact {fact.id} {fact.field_name}", file=stdout)
        return 0

    if args.command == "import-spreadsheet-proposals":
        rows = json.loads(args.rows_json)
        model = interpret_spreadsheet_cells(args.name, args.document_id, rows)
        count = extraction.add_proposals(args.deal_id, proposals_from_spreadsheet(model))
        deal = repository.get(args.deal_id)
        deal.spreadsheets.append(model)
        repository.save(deal)
        print(f"imported-spreadsheet-proposals {count}", file=stdout)
        return 0

    if args.command == "map-reviewed-facts":
        count = extraction.map_reviewed_facts_to_assumptions(args.deal_id, reviewer=args.reviewer, rationale=args.rationale)
        print(f"mapped-reviewed-facts {count}", file=stdout)
        return 0

    if args.command == "review-fact":
        deal = service.review_fact(
            args.deal_id,
            args.fact_id,
            FactReviewStatus(args.status),
            args.reviewer,
            note=args.note,
            corrected_value=_parse_value(args.corrected_value, args.corrected_value_type)
            if args.corrected_value is not None
            else None,
            promote_to_assumption=args.promote_to_assumption,
            rationale=args.rationale,
        )
        fact = next(fact for fact in deal.extracted_facts if fact.id == args.fact_id)
        print(f"reviewed-fact {fact.id} {fact.status.value}", file=stdout)
        return 0

    if args.command == "request-reextraction":
        deal = service.request_fact_reextraction(
            args.deal_id,
            args.fact_id,
            reviewer=args.reviewer,
            note=args.note,
            owner=args.owner,
            due_date=args.due_date,
        )
        fact = next(fact for fact in deal.extracted_facts if fact.id == args.fact_id)
        task = deal.tasks[-1]
        print(f"requested-reextraction {fact.id} task={task.id} owner={task.owner or ''}", file=stdout)
        return 0

    if args.command == "update-scenario-assumption":
        outputs = json.loads(args.outputs_json) if args.outputs_json else None
        deal = service.update_scenario_assumption(
            args.deal_id,
            args.scenario_id,
            name=args.name,
            value=_parse_value(args.value, args.value_type),
            actor=args.actor,
            rationale=args.rationale,
            source_fact_id=args.source_fact_id,
            revised_outputs=outputs,
        )
        scenario = next(item for item in deal.scenarios if item.id == args.scenario_id)
        print(f"updated-scenario-assumption {scenario.id} {args.name}", file=stdout)
        return 0

    if args.command == "change-status":
        deal = service.change_status(args.deal_id, DealStatus(args.status), args.actor, args.reason)
        print(f"status {deal.id} {deal.status.value}", file=stdout)
        return 0

    if args.command == "reject-deal":
        deal = service.reject_deal(args.deal_id, args.actor, args.reason)
        print(f"status {deal.id} {deal.status.value}", file=stdout)
        return 0

    if args.command == "run-monitoring":
        deal = repository.get(args.deal_id)
        added = add_new_alerts(deal, monitoring_alerts(deal))
        repository.save(deal)
        print(f"monitoring {deal.id} added_alerts={added}", file=stdout)
        return 0

    if args.command == "generate-memo":
        deal = repository.get(args.deal_id)
        print(generate_ic_memo_markdown(deal), file=stdout, end="")
        return 0

    if args.command == "generate-report":
        deal = repository.get(args.deal_id)
        if args.report_type == "monthly-performance":
            report = generate_monthly_performance_report_markdown(deal, period=args.period)
        elif args.report_type == "asset-monitoring":
            report = generate_asset_monitoring_report_markdown(deal)
        elif args.report_type == "development-progress":
            report = generate_development_progress_report_markdown(deal)
        else:
            report = generate_lender_covenant_report_markdown(deal)
        print(report, file=stdout, end="")
        return 0

    if args.command == "export-deal-pdf":
        deal = repository.get(args.deal_id)
        args.output.write_bytes(render_deal_summary_pdf(deal))
        print(f"exported {args.output}", file=stdout)
        return 0

    if args.command == "export-cash-flow-xlsx":
        from real_estate_helm.analytics import cash_flow_variances

        deal = repository.get(args.deal_id)
        args.output.write_bytes(render_cash_flow_xlsx(cash_flow_variances(deal)))
        print(f"exported {args.output}", file=stdout)
        return 0

    if args.command == "export-memo-pptx":
        deal = repository.get(args.deal_id)
        args.output.write_bytes(render_ic_memo_pptx(deal))
        print(f"exported {args.output}", file=stdout)
        return 0

    if args.command == "export-scenario-csv":
        deal = repository.get(args.deal_id)
        scenario = next(item for item in deal.scenarios if item.id == args.scenario_id)
        args.output.write_text(export_scenario_csv(scenario))
        print(f"exported {args.output}", file=stdout)
        return 0

    if args.command == "portfolio-summary":
        print(json.dumps(portfolio_dashboard_metrics(repository.list()), indent=2, sort_keys=True, default=str), file=stdout)
        return 0

    if args.command == "rejected-hindsight":
        print(json.dumps(rejected_deal_hindsight(repository.list()), indent=2, sort_keys=True, default=str), file=stdout)
        return 0

    if args.command == "ask-portfolio":
        answer = PortfolioQuestionAnswerer().answer(repository.list(), args.question)
        print(json.dumps(answer.to_dict(), indent=2, sort_keys=True), file=stdout)
        return 0

    parser.print_help(stderr or sys.stderr)
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="real-estate-helm")
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("REAL_ESTATE_HELM_DATA_DIR", ".real_estate_helm"),
        type=Path,
        help="Directory for local JSON deal records.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate-config", help="Validate environment-backed runtime settings.")

    create = subparsers.add_parser("create-deal", help="Create a new deal record.")
    create.add_argument("name")
    create.add_argument("--address")
    create.add_argument("--parcel")
    create.add_argument("--asset-type")
    create.add_argument("--sponsor")
    create.add_argument("--broker")
    create.add_argument("--seller")
    create.add_argument("--source")
    create.add_argument("--owner")

    list_deals = subparsers.add_parser("list-deals", help="List deal summaries.")
    list_deals.add_argument("--status", choices=_enum_values(DealStatus))
    list_deals.add_argument("--query", help="Search name, address, sponsor, or broker.")

    show = subparsers.add_parser("show-deal", help="Print one deal as JSON.")
    show.add_argument("deal_id")

    add_asset = subparsers.add_parser("add-asset", help="Attach an asset record to a deal.")
    add_asset.add_argument("deal_id")
    add_asset.add_argument("name")
    add_asset.add_argument("--address")
    add_asset.add_argument("--city")
    add_asset.add_argument("--state")
    add_asset.add_argument("--country")
    add_asset.add_argument("--latitude", type=float)
    add_asset.add_argument("--longitude", type=float)
    add_asset.add_argument("--asset-type")
    add_asset.add_argument("--unit-count", type=int)

    add_document = subparsers.add_parser("add-document", help="Attach an uploaded document record to a deal.")
    add_document.add_argument("deal_id")
    add_document.add_argument("--name", required=True)
    add_document.add_argument("--document-type", choices=_enum_values(DocumentType), required=True)
    add_document.add_argument("--storage-uri", required=True)
    add_document.add_argument("--uploaded-by", required=True)
    add_document.add_argument("--sha256")

    add_page = subparsers.add_parser("add-document-page", help="Attach OCR/page text and extracted tables to a document.")
    add_page.add_argument("deal_id")
    add_page.add_argument("--document-id", required=True)
    add_page.add_argument("--page-number", required=True, type=int)
    add_page.add_argument("--text-content")
    add_page.add_argument("--image-uri")
    add_page.add_argument("--extracted-tables-json")

    data_room = subparsers.add_parser("import-data-room", help="Import documents from a zipped data room.")
    data_room.add_argument("deal_id")
    data_room.add_argument("--zip-path", required=True, type=Path)
    data_room.add_argument("--uploaded-by", required=True)
    data_room.add_argument("--key-prefix")
    data_room.add_argument("--storage-root", type=Path)

    folder = subparsers.add_parser("import-folder", help="Import documents from a local diligence folder.")
    folder.add_argument("deal_id")
    folder.add_argument("--folder-path", required=True, type=Path)
    folder.add_argument("--uploaded-by", required=True)
    folder.add_argument("--key-prefix")
    folder.add_argument("--storage-root", type=Path)

    email_import = subparsers.add_parser("import-email", help="Create a deal from an email and import its attachments.")
    email_import.add_argument("--email-path", required=True, type=Path)
    email_import.add_argument("--uploaded-by", required=True)
    email_import.add_argument("--owner")
    email_import.add_argument("--storage-root", type=Path)

    email_attachments = subparsers.add_parser("import-email-attachments", help="Attach email attachments to an existing deal.")
    email_attachments.add_argument("deal_id")
    email_attachments.add_argument("--email-path", required=True, type=Path)
    email_attachments.add_argument("--uploaded-by", required=True)
    email_attachments.add_argument("--key-prefix")
    email_attachments.add_argument("--storage-root", type=Path)

    crm = subparsers.add_parser("import-crm", help="Import deal pipeline records from a CRM CSV export.")
    crm.add_argument("--csv-path", required=True, type=Path)
    crm.add_argument("--default-owner")

    add_cash_flow = subparsers.add_parser("add-cash-flow", help="Attach projected or actual cash flow.")
    add_cash_flow.add_argument("deal_id")
    add_cash_flow.add_argument("--period", required=True)
    add_cash_flow.add_argument("--category", required=True)
    add_cash_flow.add_argument("--amount", required=True)
    add_cash_flow.add_argument("--cash-flow-type", choices=_enum_values(CashFlowType), required=True)

    import_cash_flows = subparsers.add_parser("import-cash-flows", help="Import projected or actual cash-flow rows from CSV.")
    import_cash_flows.add_argument("deal_id")
    import_cash_flows.add_argument("--csv-path", required=True, type=Path)
    import_cash_flows.add_argument("--default-type", choices=_enum_values(CashFlowType), default=CashFlowType.ACTUAL.value)

    bank_statement = subparsers.add_parser("import-bank-statement", help="Import bank statement transactions as actual cash flows.")
    bank_statement.add_argument("deal_id")
    bank_statement.add_argument("--csv-path", required=True, type=Path)
    bank_statement.add_argument("--default-category", default="bank_statement")

    imagery = subparsers.add_parser("import-imagery", help="Store a photo, drone image, or satellite snapshot for a deal.")
    imagery.add_argument("deal_id")
    imagery.add_argument("--image-path", required=True, type=Path)
    imagery.add_argument("--captured-at", required=True)
    imagery.add_argument("--source", required=True)
    imagery.add_argument("--notes")
    imagery.add_argument("--storage-root", type=Path)

    rent_roll = subparsers.add_parser("add-rent-roll", help="Attach a rent-roll line item to a deal.")
    rent_roll.add_argument("deal_id")
    rent_roll.add_argument("--as-of-date", required=True)
    rent_roll.add_argument("--unit", required=True)
    rent_roll.add_argument("--tenant-name")
    rent_roll.add_argument("--monthly-rent")
    rent_roll.add_argument("--market-rent")
    rent_roll.add_argument("--vacant", action="store_true")
    rent_roll.add_argument("--concessions")
    rent_roll.add_argument("--bad-debt")
    rent_roll.add_argument("--lease-start")
    rent_roll.add_argument("--lease-end")
    rent_roll.add_argument("--source-kind", choices=_enum_values(SourceKind), default=SourceKind.DOCUMENT.value)
    rent_roll.add_argument("--source-name")
    rent_roll.add_argument("--page", type=int)
    rent_roll.add_argument("--sheet")
    rent_roll.add_argument("--cell")
    rent_roll.add_argument("--context")

    add_obligation = subparsers.add_parser("add-obligation", help="Attach a legal deadline, document expiration, or capital call.")
    add_obligation.add_argument("deal_id")
    add_obligation.add_argument("--title", required=True)
    add_obligation.add_argument("--due-date", required=True)
    add_obligation.add_argument("--obligation-type", choices=_enum_values(ObligationType), required=True)
    add_obligation.add_argument("--amount")
    add_obligation.add_argument("--source")
    add_obligation.add_argument("--owner")

    import_obligations = subparsers.add_parser("import-obligations", help="Import legal deadlines, expirations, and capital calls from CSV.")
    import_obligations.add_argument("deal_id")
    import_obligations.add_argument("--csv-path", required=True, type=Path)

    add_fact = subparsers.add_parser("add-fact", help="Attach an extracted fact to a deal.")
    add_fact.add_argument("deal_id")
    add_fact.add_argument("--field", required=True)
    add_fact.add_argument("--value", required=True)
    add_fact.add_argument("--value-type", choices=["string", "decimal", "int", "float", "bool"], default="string")
    add_fact.add_argument("--confidence", required=True, type=float)
    add_fact.add_argument("--source-kind", choices=_enum_values(SourceKind), default=SourceKind.DOCUMENT.value)
    add_fact.add_argument("--source-name", required=True)
    add_fact.add_argument("--page", type=int)
    add_fact.add_argument("--sheet")
    add_fact.add_argument("--cell")
    add_fact.add_argument("--context")

    spreadsheet = subparsers.add_parser(
        "import-spreadsheet-proposals",
        help="Import mapped spreadsheet cells as extracted fact proposals.",
    )
    spreadsheet.add_argument("deal_id")
    spreadsheet.add_argument("--name", required=True)
    spreadsheet.add_argument("--document-id", required=True)
    spreadsheet.add_argument("--rows-json", required=True)

    map_facts = subparsers.add_parser("map-reviewed-facts", help="Promote reviewed facts to assumptions.")
    map_facts.add_argument("deal_id")
    map_facts.add_argument("--reviewer", required=True)
    map_facts.add_argument("--rationale", required=True)

    review_fact = subparsers.add_parser("review-fact", help="Review an extracted fact.")
    review_fact.add_argument("deal_id")
    review_fact.add_argument("fact_id")
    review_fact.add_argument("--status", required=True, choices=_enum_values(FactReviewStatus))
    review_fact.add_argument("--reviewer", required=True)
    review_fact.add_argument("--note")
    review_fact.add_argument("--corrected-value")
    review_fact.add_argument(
        "--corrected-value-type",
        choices=["string", "decimal", "int", "float", "bool"],
        default="string",
    )
    review_fact.add_argument("--promote-to-assumption", action="store_true")
    review_fact.add_argument("--rationale")

    reextract = subparsers.add_parser("request-reextraction", help="Request re-extraction for an extracted fact.")
    reextract.add_argument("deal_id")
    reextract.add_argument("fact_id")
    reextract.add_argument("--reviewer", required=True)
    reextract.add_argument("--note")
    reextract.add_argument("--owner")
    reextract.add_argument("--due-date")

    update_assumption = subparsers.add_parser(
        "update-scenario-assumption",
        help="Update a scenario assumption and append an audit entry.",
    )
    update_assumption.add_argument("deal_id")
    update_assumption.add_argument("scenario_id")
    update_assumption.add_argument("--name", required=True)
    update_assumption.add_argument("--value", required=True)
    update_assumption.add_argument("--value-type", choices=["string", "decimal", "int", "float", "bool"], default="string")
    update_assumption.add_argument("--actor", required=True)
    update_assumption.add_argument("--rationale", required=True)
    update_assumption.add_argument("--source-fact-id")
    update_assumption.add_argument("--outputs-json")

    change_status = subparsers.add_parser("change-status", help="Move a deal to another status.")
    change_status.add_argument("deal_id")
    change_status.add_argument("status", choices=_enum_values(DealStatus))
    change_status.add_argument("--actor", required=True)
    change_status.add_argument("--reason", required=True)

    reject = subparsers.add_parser("reject-deal", help="Reject a deal and preserve the reason.")
    reject.add_argument("deal_id")
    reject.add_argument("--actor", required=True)
    reject.add_argument("--reason", required=True)

    monitor = subparsers.add_parser("run-monitoring", help="Run local monitoring rules for one deal.")
    monitor.add_argument("deal_id")

    memo = subparsers.add_parser("generate-memo", help="Generate a Markdown IC memo draft.")
    memo.add_argument("deal_id")

    report = subparsers.add_parser("generate-report", help="Generate a Markdown operating report.")
    report.add_argument("deal_id")
    report.add_argument(
        "--report-type",
        required=True,
        choices=["monthly-performance", "asset-monitoring", "development-progress", "lender-covenants"],
    )
    report.add_argument("--period", help="Optional reporting period for monthly performance reports, such as 2027-01.")

    export_pdf = subparsers.add_parser("export-deal-pdf", help="Export a deal summary PDF.")
    export_pdf.add_argument("deal_id")
    export_pdf.add_argument("--output", required=True, type=Path)

    export_xlsx = subparsers.add_parser("export-cash-flow-xlsx", help="Export cash-flow variance XLSX.")
    export_xlsx.add_argument("deal_id")
    export_xlsx.add_argument("--output", required=True, type=Path)

    export_pptx = subparsers.add_parser("export-memo-pptx", help="Export an IC memo PPTX.")
    export_pptx.add_argument("deal_id")
    export_pptx.add_argument("--output", required=True, type=Path)

    export_scenario = subparsers.add_parser("export-scenario-csv", help="Export a scenario assumptions/output table to CSV.")
    export_scenario.add_argument("deal_id")
    export_scenario.add_argument("scenario_id")
    export_scenario.add_argument("--output", required=True, type=Path)

    subparsers.add_parser("portfolio-summary", help="Print portfolio summary JSON.")
    subparsers.add_parser("rejected-hindsight", help="Print rejected-deal hindsight JSON.")
    ask = subparsers.add_parser("ask-portfolio", help="Answer a deterministic natural-language portfolio question.")
    ask.add_argument("question")

    return parser


def _enum_values(enum_type: type[Any]) -> list[str]:
    return [item.value for item in enum_type]


def _parse_value(value: str, value_type: str) -> Any:
    if value_type == "decimal":
        return Decimal(value)
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    if value_type == "bool":
        return value.casefold() in {"1", "true", "yes", "y"}
    return value


def _deal_summary(deal: Any) -> str:
    parts = [
        deal.id,
        deal.status.value,
        deal.identity.name,
    ]
    if deal.identity.asset_type:
        parts.append(deal.identity.asset_type)
    if deal.identity.address:
        parts.append(deal.identity.address)
    return " | ".join(parts)


def _safe_filename(filename: str) -> str:
    normalized = filename.replace("\\", "/")
    basename = PurePosixPath(normalized).name
    if not basename or basename in {".", ".."}:
        return "upload.bin"
    return basename


if __name__ == "__main__":
    raise SystemExit(main())

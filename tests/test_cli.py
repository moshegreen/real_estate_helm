import io
import json
import zipfile
from email.message import EmailMessage
from io import BytesIO
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from real_estate_helm import Assumption, FactReviewStatus, Scenario, ScenarioType
from real_estate_helm.cli import main
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.storage import LocalObjectStorage


class CliTests(TestCase):
    def test_validate_config_command_reports_environment_errors(self) -> None:
        stderr = io.StringIO()
        with patch.dict(
            "os.environ",
            {
                "REAL_ESTATE_HELM_AUTH_SECRET": "short",
                "S3_ENDPOINT": "http://minio:9000",
                "S3_BUCKET": "deal-data",
            },
            clear=True,
        ):
            exit_code = main(["validate-config"], stdout=io.StringIO(), stderr=stderr)

        self.assertEqual(exit_code, 1)
        self.assertIn("REAL_ESTATE_HELM_AUTH_SECRET", stderr.getvalue())
        self.assertIn("S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY", stderr.getvalue())

    def test_validate_config_command_reports_configured_providers(self) -> None:
        stdout = io.StringIO()
        with patch.dict(
            "os.environ",
            {
                "REAL_ESTATE_HELM_AUTH_SECRET": "0123456789abcdef",
                "S3_ENDPOINT": "http://minio:9000",
                "S3_BUCKET": "deal-data",
                "S3_ACCESS_KEY": "minio",
                "S3_SECRET_KEY": "secret",
                "NEWS_API_KEY": "news",
            },
            clear=True,
        ):
            exit_code = main(["validate-config"], stdout=stdout, stderr=io.StringIO())

        self.assertEqual(exit_code, 0)
        self.assertIn("storage=configured", stdout.getvalue())
        self.assertIn("providers=news", stdout.getvalue())

    def test_create_list_show_and_reject_deal(self) -> None:
        with TemporaryDirectory() as directory:
            create_output = io.StringIO()
            exit_code = main(
                [
                    "--data-dir",
                    directory,
                    "create-deal",
                    "Harbor Apartments",
                    "--address",
                    "10 Harbor Way",
                    "--asset-type",
                    "multifamily",
                    "--broker",
                    "Metro Capital",
                ],
                stdout=create_output,
            )
            self.assertEqual(exit_code, 0)
            deal_id = create_output.getvalue().split()[1]

            list_output = io.StringIO()
            main(["--data-dir", directory, "list-deals", "--query", "metro"], stdout=list_output)
            self.assertIn("Harbor Apartments", list_output.getvalue())

            reject_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "reject-deal",
                    deal_id,
                    "--actor",
                    "principal",
                    "--reason",
                    "Downside DSCR is too weak",
                ],
                stdout=reject_output,
            )
            self.assertIn("rejected", reject_output.getvalue())

            show_output = io.StringIO()
            main(["--data-dir", directory, "show-deal", deal_id], stdout=show_output)
            payload = json.loads(show_output.getvalue())
            self.assertEqual(payload["status"], "rejected")
            self.assertEqual(payload["decision_history"][0]["reason"], "Downside DSCR is too weak")

    def test_add_and_review_fact_promotes_assumption(self) -> None:
        with TemporaryDirectory() as directory:
            create_output = io.StringIO()
            main(["--data-dir", directory, "create-deal", "Pine Logistics"], stdout=create_output)
            deal_id = create_output.getvalue().split()[1]

            fact_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "add-fact",
                    deal_id,
                    "--field",
                    "purchase_price",
                    "--value",
                    "21000000",
                    "--value-type",
                    "decimal",
                    "--confidence",
                    "0.9",
                    "--source-name",
                    "om.pdf",
                    "--page",
                    "4",
                ],
                stdout=fact_output,
            )
            fact_id = fact_output.getvalue().split()[1]

            review_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "review-fact",
                    deal_id,
                    fact_id,
                    "--status",
                    "assumption",
                    "--reviewer",
                    "analyst",
                    "--corrected-value",
                    "20500000",
                    "--corrected-value-type",
                    "decimal",
                    "--promote-to-assumption",
                    "--rationale",
                    "Corrected after rent roll check",
                ],
                stdout=review_output,
            )

            self.assertIn("assumption", review_output.getvalue())
            deal = JsonDealRepository(directory).get(deal_id)
            self.assertEqual(deal.assumptions[0].value, Decimal("20500000"))

            reextract_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "request-reextraction",
                    deal_id,
                    fact_id,
                    "--reviewer",
                    "analyst",
                    "--note",
                    "Rerun page table extraction.",
                    "--owner",
                    "document-ai",
                    "--due-date",
                    "2027-01-15",
                ],
                stdout=reextract_output,
            )

            self.assertIn("requested-reextraction", reextract_output.getvalue())
            reloaded = JsonDealRepository(directory).get(deal_id)
            self.assertEqual(reloaded.extracted_facts[0].status, FactReviewStatus.NEEDS_REEXTRACTION)
            self.assertEqual(reloaded.tasks[0].owner, "document-ai")

    def test_intake_monitoring_memo_and_portfolio_summary_commands(self) -> None:
        with TemporaryDirectory() as directory:
            create_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "create-deal",
                    "Oak Retail",
                    "--asset-type",
                    "retail",
                ],
                stdout=create_output,
            )
            deal_id = create_output.getvalue().split()[1]

            main(
                [
                    "--data-dir",
                    directory,
                    "add-asset",
                    deal_id,
                    "Oak Retail",
                    "--address",
                    "100 Oak Street",
                    "--city",
                    "Dallas",
                    "--asset-type",
                    "retail",
                    "--latitude",
                    "32.1",
                    "--longitude",
                    "34.8",
                ],
                stdout=io.StringIO(),
            )
            self.assertEqual(JsonDealRepository(directory).get(deal_id).assets[0].coordinates.latitude, 32.1)
            main(
                [
                    "--data-dir",
                    directory,
                    "add-document",
                    deal_id,
                    "--name",
                    "om.pdf",
                    "--document-type",
                    "pdf",
                    "--storage-uri",
                    "local://om.pdf",
                    "--uploaded-by",
                    "analyst",
                ],
                stdout=io.StringIO(),
            )
            repository = JsonDealRepository(directory)
            document_id = repository.get(deal_id).documents[0].id
            page_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "add-document-page",
                    deal_id,
                    "--document-id",
                    document_id,
                    "--page-number",
                    "1",
                    "--text-content",
                    "NOI table",
                    "--extracted-tables-json",
                    '[{"name": "NOI"}]',
                ],
                stdout=page_output,
            )
            self.assertIn("added-document-page", page_output.getvalue())
            main(
                [
                    "--data-dir",
                    directory,
                    "add-cash-flow",
                    deal_id,
                    "--period",
                    "2027-01",
                    "--category",
                    "noi",
                    "--amount",
                    "100000",
                    "--cash-flow-type",
                    "projected",
                ],
                stdout=io.StringIO(),
            )
            main(
                [
                    "--data-dir",
                    directory,
                    "add-cash-flow",
                    deal_id,
                    "--period",
                    "2027-01",
                    "--category",
                    "noi",
                    "--amount",
                    "90000",
                    "--cash-flow-type",
                    "actual",
                ],
                stdout=io.StringIO(),
            )
            csv_path = Path(directory) / "actuals.csv"
            csv_path.write_text(
                "period,category,amount,cash_flow_type\n"
                "2027-02,noi,95000,actual\n"
                "2027-02,noi,105000,projected\n"
                "bad,noi,nope,actual\n"
            )
            import_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-cash-flows",
                    deal_id,
                    "--csv-path",
                    str(csv_path),
                ],
                stdout=import_output,
            )
            import_payload = json.loads(import_output.getvalue())
            imported_deal = JsonDealRepository(directory).get(deal_id)
            self.assertEqual(import_payload["imported_rows"], 2)
            self.assertEqual(len(import_payload["skipped_rows"]), 1)
            self.assertEqual(imported_deal.actual_cash_flows[1].amount, Decimal("95000"))
            self.assertEqual(imported_deal.projected_cash_flows[1].amount, Decimal("105000"))
            bank_path = Path(directory) / "bank.csv"
            bank_path.write_text("date,description,deposit,withdrawal\n2027-03-05,Rent collection,142000,\n2027-03-06,Repair invoice,,25000\n")
            bank_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-bank-statement",
                    deal_id,
                    "--csv-path",
                    str(bank_path),
                ],
                stdout=bank_output,
            )
            bank_payload = json.loads(bank_output.getvalue())
            bank_deal = JsonDealRepository(directory).get(deal_id)
            self.assertEqual(bank_payload["imported_rows"], 2)
            self.assertEqual(bank_deal.actual_cash_flows[2].amount, Decimal("142000"))
            self.assertEqual(bank_deal.actual_cash_flows[3].amount, Decimal("-25000"))
            image_path = Path(directory) / "site.jpg"
            image_path.write_bytes(b"image-bytes")
            imagery_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-imagery",
                    deal_id,
                    "--image-path",
                    str(image_path),
                    "--captured-at",
                    "2027-02-15",
                    "--source",
                    "drone",
                    "--notes",
                    "North elevation progress photo.",
                ],
                stdout=imagery_output,
            )
            imagery_payload = json.loads(imagery_output.getvalue())
            imagery_deal = JsonDealRepository(directory).get(deal_id)
            self.assertEqual(imagery_payload["source"], "drone")
            self.assertEqual(imagery_deal.imagery_snapshots[0].notes, "North elevation progress photo.")
            self.assertEqual(
                LocalObjectStorage(Path(directory) / "objects").get_bytes(imagery_deal.imagery_snapshots[0].storage_uri),
                b"image-bytes",
            )
            rent_roll_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "add-rent-roll",
                    deal_id,
                    "--as-of-date",
                    "2027-01-31",
                    "--unit",
                    "101",
                    "--tenant-name",
                    "Shop Tenant",
                    "--monthly-rent",
                    "2000",
                    "--market-rent",
                    "2200",
                    "--source-kind",
                    "spreadsheet",
                    "--source-name",
                    "rent-roll.xlsx",
                    "--sheet",
                    "Rent Roll",
                    "--cell",
                    "B2",
                ],
                stdout=rent_roll_output,
            )
            self.assertIn("added-rent-roll", rent_roll_output.getvalue())
            self.assertEqual(JsonDealRepository(directory).get(deal_id).rent_roll[0].source.cell, "B2")
            obligation_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "add-obligation",
                    deal_id,
                    "--title",
                    "Fund capital call",
                    "--due-date",
                    "2027-02-01",
                    "--obligation-type",
                    "capital_call",
                    "--amount",
                    "250000",
                ],
                stdout=obligation_output,
            )
            self.assertIn("added-obligation", obligation_output.getvalue())
            obligations_path = Path(directory) / "obligations.csv"
            obligations_path.write_text(
                "title,due_date,obligation_type,amount,source,owner\n"
                "File zoning appeal,2027-01-10,legal_deadline,,legal tracker,counsel\n"
                "Insurance certificate,2027-01-20,document_expiration,,data room,analyst\n"
                "Broken row,,capital_call,100,fund notice,principal\n"
            )
            obligations_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-obligations",
                    deal_id,
                    "--csv-path",
                    str(obligations_path),
                ],
                stdout=obligations_output,
            )
            obligations_payload = json.loads(obligations_output.getvalue())
            obligations_deal = JsonDealRepository(directory).get(deal_id)
            self.assertEqual(obligations_payload["imported_rows"], 2)
            self.assertEqual(len(obligations_payload["skipped_rows"]), 1)
            self.assertEqual(obligations_deal.obligations[1].owner, "counsel")

            monitoring_output = io.StringIO()
            main(["--data-dir", directory, "run-monitoring", deal_id], stdout=monitoring_output)
            self.assertIn("monitoring", monitoring_output.getvalue())

            memo_output = io.StringIO()
            main(["--data-dir", directory, "generate-memo", deal_id], stdout=memo_output)
            self.assertIn("# Investment Committee Memo: Oak Retail", memo_output.getvalue())
            self.assertIn("NOI", memo_output.getvalue().upper())

            report_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "generate-report",
                    deal_id,
                    "--report-type",
                    "monthly-performance",
                    "--period",
                    "2027-01",
                ],
                stdout=report_output,
            )
            self.assertIn("# Monthly Performance Report: Oak Retail", report_output.getvalue())
            self.assertIn("Variance: -10000", report_output.getvalue())

            asset_report_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "generate-report",
                    deal_id,
                    "--report-type",
                    "asset-monitoring",
                ],
                stdout=asset_report_output,
            )
            self.assertIn("# Asset Monitoring Report: Oak Retail", asset_report_output.getvalue())
            self.assertIn("100 Oak Street", asset_report_output.getvalue())

            summary_output = io.StringIO()
            main(["--data-dir", directory, "portfolio-summary"], stdout=summary_output)
            payload = json.loads(summary_output.getvalue())
            self.assertEqual(payload["deal_count"], 1)
            self.assertEqual(payload["current_portfolio_value"], "0")
            self.assertEqual(payload["exposure_by_asset_type"], {"retail": 1})
            self.assertEqual(payload["exposure_by_sponsor"], {"unknown": 1})
            self.assertIn("debt_maturity_schedule", payload)
            self.assertGreaterEqual(payload["open_alert_count"], 1)

            question_output = io.StringIO()
            main(["--data-dir", directory, "ask-portfolio", "What are the open alerts?"], stdout=question_output)
            answer = json.loads(question_output.getvalue())
            self.assertEqual(answer["answer_type"], "open_alerts")
            self.assertEqual(answer["rows"][0]["deal_name"], "Oak Retail")

    def test_import_data_room_command_attaches_documents(self) -> None:
        with TemporaryDirectory() as directory:
            create_output = io.StringIO()
            main(["--data-dir", directory, "create-deal", "Data Room CLI Deal"], stdout=create_output)
            deal_id = create_output.getvalue().split()[1]
            zip_path = Path(directory) / "data-room.zip"
            zip_path.write_bytes(_zip_bytes({"om.pdf": b"pdf", "folder/model.xlsx": b"xlsx"}))

            output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-data-room",
                    deal_id,
                    "--zip-path",
                    str(zip_path),
                    "--uploaded-by",
                    "analyst",
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            deal = JsonDealRepository(directory).get(deal_id)
            self.assertEqual(payload["documents_imported"], 2)
            self.assertEqual(deal.documents[1].name, "folder/model.xlsx")

    def test_import_folder_command_attaches_documents(self) -> None:
        with TemporaryDirectory() as directory:
            create_output = io.StringIO()
            main(["--data-dir", directory, "create-deal", "Folder CLI Deal"], stdout=create_output)
            deal_id = create_output.getvalue().split()[1]
            folder = Path(directory) / "folder-room"
            (folder / "reports").mkdir(parents=True)
            (folder / "reports" / "appraisal.pdf").write_bytes(b"pdf")

            output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-folder",
                    deal_id,
                    "--folder-path",
                    str(folder),
                    "--uploaded-by",
                    "analyst",
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            deal = JsonDealRepository(directory).get(deal_id)
            self.assertEqual(payload["documents_imported"], 1)
            self.assertEqual(deal.documents[0].name, "reports/appraisal.pdf")

    def test_import_email_command_creates_deal_and_attaches_documents(self) -> None:
        with TemporaryDirectory() as directory:
            email_path = Path(directory) / "deal.eml"
            email_path.write_bytes(_email_bytes("Email CLI Deal", {"om.pdf": b"pdf", "rent-roll.csv": b"csv"}))

            output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-email",
                    "--email-path",
                    str(email_path),
                    "--uploaded-by",
                    "analyst",
                    "--owner",
                    "associate",
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            deal = JsonDealRepository(directory).get(payload["deal_id"])
            self.assertEqual(payload["subject"], "Email CLI Deal")
            self.assertEqual(payload["attachments_imported"], 2)
            self.assertEqual(deal.identity.owner, "associate")
            self.assertEqual(deal.documents[1].document_type.value, "csv")

    def test_import_email_attachments_command_updates_existing_deal(self) -> None:
        with TemporaryDirectory() as directory:
            create_output = io.StringIO()
            main(["--data-dir", directory, "create-deal", "Existing Email CLI Deal"], stdout=create_output)
            deal_id = create_output.getvalue().split()[1]
            email_path = Path(directory) / "followup.eml"
            email_path.write_bytes(_email_bytes("Followup", {"../om.pdf": b"pdf"}))

            output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-email-attachments",
                    deal_id,
                    "--email-path",
                    str(email_path),
                    "--uploaded-by",
                    "analyst",
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            deal = JsonDealRepository(directory).get(deal_id)
            self.assertEqual(payload["attachments_imported"], 1)
            self.assertEqual(deal.documents[0].name, "om.pdf")

    def test_import_crm_command_creates_pipeline_deals(self) -> None:
        with TemporaryDirectory() as directory:
            csv_path = Path(directory) / "crm.csv"
            csv_path.write_text("deal_name,property_address,asset_class,stage\nCRM CLI Deal,1 CRM Way,office,screening\n")

            output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-crm",
                    "--csv-path",
                    str(csv_path),
                    "--default-owner",
                    "analyst",
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            deal = JsonDealRepository(directory).get(payload["deal_ids"][0])
            self.assertEqual(payload["imported_rows"], 1)
            self.assertEqual(deal.identity.name, "CRM CLI Deal")
            self.assertEqual(deal.identity.owner, "analyst")
            self.assertEqual(deal.status.value, "screening")

    def test_spreadsheet_proposals_mapping_and_rejected_hindsight_commands(self) -> None:
        with TemporaryDirectory() as directory:
            create_output = io.StringIO()
            main(["--data-dir", directory, "create-deal", "Passed Deal"], stdout=create_output)
            deal_id = create_output.getvalue().split()[1]
            rows = json.dumps(
                [
                    {
                        "sheet": "Summary",
                        "cell": "B4",
                        "value": "10000000",
                        "formula": "=PurchasePrice",
                        "mapped_field": "proposed_price",
                    }
                ]
            )

            import_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "import-spreadsheet-proposals",
                    deal_id,
                    "--name",
                    "Sponsor Model",
                    "--document-id",
                    "doc-1",
                    "--rows-json",
                    rows,
                ],
                stdout=import_output,
            )
            self.assertIn("imported-spreadsheet-proposals 1", import_output.getvalue())

            repository = JsonDealRepository(directory)
            deal = repository.get(deal_id)
            fact_id = deal.extracted_facts[0].id
            deal.review_fact(fact_id, FactReviewStatus.ACCEPTED, "analyst")
            repository.save(deal)

            map_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "map-reviewed-facts",
                    deal_id,
                    "--reviewer",
                    "analyst",
                    "--rationale",
                    "Reviewed sponsor model",
                ],
                stdout=map_output,
            )
            self.assertIn("mapped-reviewed-facts 1", map_output.getvalue())

            main(
                [
                    "--data-dir",
                    directory,
                    "reject-deal",
                    deal_id,
                    "--actor",
                    "principal",
                    "--reason",
                    "Return too low",
                ],
                stdout=io.StringIO(),
            )
            hindsight_output = io.StringIO()
            main(["--data-dir", directory, "rejected-hindsight"], stdout=hindsight_output)
            self.assertIn("Passed Deal", hindsight_output.getvalue())

    def test_export_artifact_commands_write_files(self) -> None:
        with TemporaryDirectory() as directory:
            create_output = io.StringIO()
            main(["--data-dir", directory, "create-deal", "Export Deal"], stdout=create_output)
            deal_id = create_output.getvalue().split()[1]
            pdf_path = Path(directory) / "deal.pdf"
            xlsx_path = Path(directory) / "cash-flows.xlsx"
            pptx_path = Path(directory) / "memo.pptx"
            scenario_path = Path(directory) / "scenario.csv"
            repository = JsonDealRepository(directory)
            deal = repository.get(deal_id)
            scenario = Scenario("Base Case", ScenarioType.ANALYST_BASE_CASE)
            scenario.assumptions.append(Assumption("rent_growth", Decimal("0.03"), "Market"))
            scenario.outputs["irr"] = Decimal("0.14")
            deal.scenarios.append(scenario)
            repository.save(deal)

            main(["--data-dir", directory, "export-deal-pdf", deal_id, "--output", str(pdf_path)], stdout=io.StringIO())
            main(
                ["--data-dir", directory, "export-cash-flow-xlsx", deal_id, "--output", str(xlsx_path)],
                stdout=io.StringIO(),
            )
            main(["--data-dir", directory, "export-memo-pptx", deal_id, "--output", str(pptx_path)], stdout=io.StringIO())
            main(
                ["--data-dir", directory, "export-scenario-csv", deal_id, scenario.id, "--output", str(scenario_path)],
                stdout=io.StringIO(),
            )
            update_output = io.StringIO()
            main(
                [
                    "--data-dir",
                    directory,
                    "update-scenario-assumption",
                    deal_id,
                    scenario.id,
                    "--name",
                    "rent_growth",
                    "--value",
                    "0.025",
                    "--value-type",
                    "decimal",
                    "--actor",
                    "analyst",
                    "--rationale",
                    "Updated rent roll",
                    "--outputs-json",
                    '{"irr": "0.12"}',
                ],
                stdout=update_output,
            )

            self.assertTrue(pdf_path.read_bytes().startswith(b"%PDF"))
            with zipfile.ZipFile(xlsx_path) as archive:
                self.assertIn("xl/workbook.xml", archive.namelist())
            with zipfile.ZipFile(pptx_path) as archive:
                self.assertIn("ppt/presentation.xml", archive.namelist())
            self.assertIn("assumption,rent_growth,0.03,Market", scenario_path.read_text())
            self.assertIn("updated-scenario-assumption", update_output.getvalue())
            self.assertEqual(JsonDealRepository(directory).get(deal_id).audit_log[-1].action, "update_scenario_assumption")


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def _email_bytes(subject: str, attachments: dict[str, bytes]) -> bytes:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = "broker@example.test"
    message.set_content("Please review the attached materials.")
    for filename, data in attachments.items():
        message.add_attachment(data, maintype="application", subtype="octet-stream", filename=filename)
    return message.as_bytes()

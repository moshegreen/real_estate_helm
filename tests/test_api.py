import base64
import zipfile
from email.message import EmailMessage
from io import BytesIO
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import Assumption, DebtTerms, Scenario, ScenarioType
from real_estate_helm.api import ApiRouter
from real_estate_helm.repository import JsonDealRepository


class ApiRouterTests(TestCase):
    def test_create_list_get_and_change_status(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))

            health = router.handle("GET", "/health")
            self.assertEqual(health.status, 200)
            self.assertEqual(health.body, {"status": "ok"})

            created = router.handle(
                "POST",
                "/deals",
                {"name": "API Deal", "address": "1 API Way", "asset_type": "office"},
            )
            self.assertEqual(created.status, 201)
            deal_id = created.body["id"]

            listed = router.handle("GET", "/deals")
            self.assertEqual(len(listed.body), 1)

            changed = router.handle(
                "POST",
                f"/deals/{deal_id}/status",
                {"status": "underwriting", "actor": "analyst", "reason": "Ready for model"},
            )
            self.assertEqual(changed.body["status"], "underwriting")

            fetched = router.handle("GET", f"/deals/{deal_id}")
            self.assertEqual(fetched.body["decision_history"][0]["reason"], "Ready for model")

    def test_intake_review_monitoring_memo_and_portfolio_routes(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))
            created = router.handle("POST", "/deals", {"name": "API Monitoring Deal", "asset_type": "retail"})
            deal_id = created.body["id"]

            asset = router.handle("POST", f"/deals/{deal_id}/assets", {"name": "API Monitoring Deal", "asset_type": "retail"})
            self.assertEqual(asset.status, 201)
            mapped_asset = router.handle(
                "POST",
                f"/deals/{deal_id}/assets",
                {"name": "Mapped Asset", "asset_type": "retail", "latitude": 32.1, "longitude": 34.8},
            )
            self.assertEqual(mapped_asset.body["assets"][1]["coordinates"]["latitude"], 32.1)
            document = router.handle(
                "POST",
                f"/deals/{deal_id}/documents",
                {
                    "name": "om.pdf",
                    "document_type": "pdf",
                    "storage_uri": "local://om.pdf",
                    "uploaded_by": "analyst",
                },
            )
            self.assertEqual(document.body["documents"][0]["name"], "om.pdf")
            page = router.handle(
                "POST",
                f"/deals/{deal_id}/document-pages",
                {
                    "document_id": document.body["documents"][0]["id"],
                    "page_number": 1,
                    "text_content": "Purchase price table",
                    "extracted_tables": [{"name": "pricing"}],
                },
            )
            self.assertEqual(page.body["document_pages"][0]["extracted_tables"][0]["name"], "pricing")
            imagery = router.handle(
                "POST",
                f"/deals/{deal_id}/imagery",
                {
                    "content_base64": base64.b64encode(b"image-bytes").decode(),
                    "filename": "../site.jpg",
                    "captured_at": "2027-02-15",
                    "source": "drone",
                    "notes": "North elevation progress photo.",
                },
            )
            self.assertEqual(imagery.status, 201)
            self.assertEqual(imagery.body["imagery_snapshots"][0]["source"], "drone")
            self.assertTrue(imagery.body["imagery_snapshots"][0]["storage_uri"].endswith("/site.jpg"))
            fact_response = router.handle(
                "POST",
                f"/deals/{deal_id}/facts",
                {
                    "field_name": "purchase_price",
                    "value": "10000000",
                    "confidence": 0.9,
                    "source_name": "om.pdf",
                    "source_kind": "document",
                    "page": 4,
                },
            )
            fact_id = fact_response.body["extracted_facts"][0]["id"]
            reviewed = router.handle(
                "POST",
                f"/deals/{deal_id}/review-fact",
                {
                    "fact_id": fact_id,
                    "status": "assumption",
                    "reviewer": "analyst",
                    "promote_to_assumption": True,
                    "rationale": "Reviewed source page",
                },
            )
            self.assertEqual(reviewed.body["assumptions"][0]["name"], "purchase_price")
            reextraction = router.handle(
                "POST",
                f"/deals/{deal_id}/facts/{fact_id}/reextraction",
                {
                    "reviewer": "analyst",
                    "note": "Rerun extraction against appendix table.",
                    "owner": "document-ai",
                    "due_date": "2027-01-15",
                },
            )
            self.assertEqual(reextraction.status, 200)
            self.assertEqual(reextraction.body["extracted_facts"][0]["status"], "needs_reextraction")
            self.assertEqual(reextraction.body["tasks"][0]["owner"], "document-ai")
            self.assertEqual(reextraction.body["audit_log"][-1]["action"], "request_fact_reextraction")
            router.handle(
                "POST",
                f"/deals/{deal_id}/cash-flows",
                {"period": "2027-01", "amount": "100000", "cash_flow_type": "projected", "category": "noi"},
            )
            router.handle(
                "POST",
                f"/deals/{deal_id}/cash-flows",
                {"period": "2027-01", "amount": "90000", "cash_flow_type": "actual", "category": "noi"},
            )
            imported_cash_flows = router.handle(
                "POST",
                f"/deals/{deal_id}/cash-flow-imports",
                {
                    "content_base64": base64.b64encode(
                        b"period,category,amount,cash_flow_type\n2027-02,noi,95000,actual\n2027-02,noi,105000,projected\nbad,noi,nope,actual\n"
                    ).decode(),
                    "default_type": "actual",
                },
            )
            self.assertEqual(imported_cash_flows.status, 201)
            self.assertEqual(imported_cash_flows.body["imported_rows"], 2)
            self.assertEqual(len(imported_cash_flows.body["skipped_rows"]), 1)
            self.assertEqual(imported_cash_flows.body["deal"]["actual_cash_flows"][1]["amount"]["value"], "95000")
            self.assertEqual(imported_cash_flows.body["deal"]["projected_cash_flows"][1]["amount"]["value"], "105000")
            imported_bank_statement = router.handle(
                "POST",
                f"/deals/{deal_id}/bank-statement-imports",
                {
                    "content_base64": base64.b64encode(
                        b"date,description,deposit,withdrawal\n2027-03-05,Rent collection,142000,\n2027-03-06,Repair invoice,,25000\n"
                    ).decode()
                },
            )
            self.assertEqual(imported_bank_statement.status, 201)
            self.assertEqual(imported_bank_statement.body["imported_rows"], 2)
            self.assertEqual(imported_bank_statement.body["deal"]["actual_cash_flows"][2]["amount"]["value"], "142000")
            self.assertEqual(imported_bank_statement.body["deal"]["actual_cash_flows"][3]["amount"]["value"], "-25000")
            rent_roll = router.handle(
                "POST",
                f"/deals/{deal_id}/rent-roll",
                {
                    "as_of_date": "2027-01-31",
                    "unit": "101",
                    "tenant_name": "Shop Tenant",
                    "monthly_rent": "2000",
                    "market_rent": "2200",
                    "source_name": "rent-roll.xlsx",
                    "source_kind": "spreadsheet",
                    "sheet": "Rent Roll",
                    "cell": "B2",
                },
            )
            self.assertEqual(rent_roll.status, 201)
            self.assertEqual(rent_roll.body["rent_roll"][0]["source"]["cell"], "B2")
            obligation = router.handle(
                "POST",
                f"/deals/{deal_id}/obligations",
                {
                    "title": "Fund capital call",
                    "due_date": "2027-02-01",
                    "obligation_type": "capital_call",
                    "amount": "250000",
                },
            )
            self.assertEqual(obligation.status, 201)
            self.assertEqual(obligation.body["obligations"][0]["obligation_type"], "capital_call")
            imported_obligations = router.handle(
                "POST",
                f"/deals/{deal_id}/obligation-imports",
                {
                    "content_base64": base64.b64encode(
                        b"title,due_date,obligation_type,amount,source,owner\n"
                        b"File zoning appeal,2027-01-10,legal_deadline,,legal tracker,counsel\n"
                        b"Insurance certificate,2027-01-20,document_expiration,,data room,analyst\n"
                        b"Broken row,,capital_call,100,fund notice,principal\n"
                    ).decode()
                },
            )
            self.assertEqual(imported_obligations.status, 201)
            self.assertEqual(imported_obligations.body["imported_rows"], 2)
            self.assertEqual(len(imported_obligations.body["skipped_rows"]), 1)
            self.assertEqual(imported_obligations.body["deal"]["obligations"][1]["obligation_type"], "legal_deadline")
            monitored = router.handle("POST", f"/deals/{deal_id}/monitoring")
            self.assertGreaterEqual(len(monitored.body["alerts"]), 1)
            memo = router.handle("GET", f"/deals/{deal_id}/memo")
            self.assertIn("Investment Committee Memo", memo.body["markdown"])
            monthly = router.handle("POST", f"/deals/{deal_id}/reports/monthly-performance", {"period": "2027-01"})
            self.assertIn("Monthly Performance Report", monthly.body["markdown"])
            self.assertIn("Variance: -10000", monthly.body["markdown"])
            summary = router.handle("GET", "/portfolio/summary")
            self.assertEqual(summary.body["deal_count"], 1)
            self.assertEqual(summary.body["current_portfolio_value"], "10000000")
            self.assertGreaterEqual(summary.body["open_alert_count"], 1)
            self.assertEqual(summary.body["exposure_by_sponsor"], {"unknown": 1})
            self.assertIn("debt_maturity_schedule", summary.body)
            qa = router.handle("POST", "/portfolio/questions", {"question": "What are the open alerts?"})
            self.assertEqual(qa.status, 200)
            self.assertEqual(qa.body["answer_type"], "open_alerts")
            self.assertEqual(qa.body["rows"][0]["deal_name"], "API Monitoring Deal")

    def test_development_and_lender_report_routes(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            router = ApiRouter(repository)
            deal_id = router.handle("POST", "/deals", {"name": "Report API Deal"}).body["id"]
            deal = repository.get(deal_id)
            deal.debt_terms.append(DebtTerms(lender="Bank", debt_amount=Decimal("7000000"), covenant_dscr=Decimal("1.20")))
            deal.assumptions.append(Assumption("current_noi", Decimal("1200000"), "Latest actuals"))
            deal.assumptions.append(Assumption("annual_debt_service", Decimal("900000"), "Loan schedule"))
            repository.save(deal)

            development = router.handle("GET", f"/deals/{deal_id}/reports/development-progress")
            asset_monitoring = router.handle("GET", f"/deals/{deal_id}/reports/asset-monitoring")
            lender = router.handle("GET", f"/deals/{deal_id}/reports/lender-covenants")

            self.assertIn("Development Progress Report", development.body["markdown"])
            self.assertIn("Asset Monitoring Report", asset_monitoring.body["markdown"])
            self.assertIn("Lender Covenant Report", lender.body["markdown"])
            self.assertIn("current DSCR", lender.body["markdown"])

    def test_scenario_assumption_update_route_records_audit(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            router = ApiRouter(repository)
            deal_id = router.handle("POST", "/deals", {"name": "Scenario API Deal"}).body["id"]
            deal = repository.get(deal_id)
            scenario = Scenario("Base", ScenarioType.ANALYST_BASE_CASE)
            scenario.assumptions.append(Assumption("rent_growth", "0.03", "Original"))
            scenario.outputs["irr"] = "0.14"
            deal.scenarios.append(scenario)
            repository.save(deal)

            response = router.handle(
                "POST",
                f"/deals/{deal_id}/scenarios/{scenario.id}/assumptions",
                {
                    "name": "rent_growth",
                    "value": "0.025",
                    "actor": "analyst",
                    "rationale": "Updated lease assumptions",
                    "revised_outputs": {"irr": "0.12"},
                },
            )

            self.assertEqual(response.status, 200)
            self.assertEqual(response.body["scenarios"][0]["assumptions"][0]["value"], "0.025")
            self.assertEqual(response.body["audit_log"][-1]["action"], "update_scenario_assumption")

    def test_data_room_import_route_attaches_zipped_documents(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))
            deal_id = router.handle("POST", "/deals", {"name": "Data Room API Deal"}).body["id"]

            response = router.handle(
                "POST",
                f"/deals/{deal_id}/data-room",
                {
                    "content_base64": base64.b64encode(_zip_bytes({"om.pdf": b"pdf", "rent-roll.csv": b"csv"})).decode(),
                    "uploaded_by": "analyst",
                },
            )

            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["documents_imported"], 2)
            self.assertEqual(response.body["deal"]["documents"][1]["document_type"], "csv")

    def test_folder_import_route_attaches_local_documents(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))
            deal_id = router.handle("POST", "/deals", {"name": "Folder API Deal"}).body["id"]
            folder = Path(directory) / "folder-room"
            folder.mkdir()
            (folder / "om.pdf").write_bytes(b"pdf")

            response = router.handle(
                "POST",
                f"/deals/{deal_id}/data-room-folder",
                {"folder_path": str(folder), "uploaded_by": "analyst"},
            )

            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["documents_imported"], 1)
            self.assertEqual(response.body["deal"]["documents"][0]["name"], "om.pdf")

    def test_email_import_route_creates_deal_and_attaches_documents(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))

            response = router.handle(
                "POST",
                "/emails/import",
                {
                    "content_base64": base64.b64encode(
                        _email_bytes("Email API Deal", {"om.pdf": b"pdf", "rent-roll.csv": b"csv"})
                    ).decode(),
                    "uploaded_by": "analyst",
                    "owner": "associate",
                },
            )

            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["subject"], "Email API Deal")
            self.assertEqual(response.body["attachments_imported"], 2)
            self.assertEqual(response.body["deal"]["identity"]["source"], "broker@example.test")
            self.assertEqual(response.body["deal"]["identity"]["owner"], "associate")
            self.assertEqual(response.body["deal"]["documents"][1]["document_type"], "csv")

    def test_crm_import_route_creates_pipeline_deals(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))

            response = router.handle(
                "POST",
                "/crm/import",
                {
                    "content_base64": base64.b64encode(
                        b"deal_name,property_address,asset_class,stage\nCRM API Deal,1 CRM Way,office,screening\n"
                    ).decode(),
                    "default_owner": "analyst",
                },
            )

            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["imported_rows"], 1)
            self.assertEqual(response.body["deals"][0]["identity"]["name"], "CRM API Deal")
            self.assertEqual(response.body["deals"][0]["identity"]["owner"], "analyst")
            self.assertEqual(response.body["deals"][0]["status"], "screening")

    def test_deal_email_route_attaches_documents_to_existing_deal(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))
            deal_id = router.handle("POST", "/deals", {"name": "Existing Email API Deal"}).body["id"]

            response = router.handle(
                "POST",
                f"/deals/{deal_id}/email",
                {
                    "content_base64": base64.b64encode(_email_bytes("Followup", {"../om.pdf": b"pdf"})).decode(),
                    "uploaded_by": "analyst",
                },
            )

            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["attachments_imported"], 1)
            self.assertEqual(response.body["deal"]["documents"][0]["name"], "om.pdf")

    def test_comment_and_approval_routes(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))
            deal_id = router.handle("POST", "/deals", {"name": "Approval API Deal"}).body["id"]

            commented = router.handle(
                "POST",
                f"/deals/{deal_id}/comments",
                {"author": "advisor", "body": "Check zoning memo."},
            )
            self.assertEqual(commented.status, 201)
            self.assertEqual(commented.body["comments"][0]["body"], "Check zoning memo.")
            approval = router.handle(
                "POST",
                f"/deals/{deal_id}/approval-requests",
                {"title": "Approve watchlist", "requested_by": "analyst", "approver": "principal"},
            )
            approval_id = approval.body["approval_requests"][0]["id"]
            decided = router.handle(
                "POST",
                f"/deals/{deal_id}/approval-decisions",
                {"approval_id": approval_id, "approved": True, "note": "Approved."},
            )
            self.assertEqual(decided.body["approval_requests"][0]["status"], "approved")

    def test_unknown_route_returns_404(self) -> None:
        with TemporaryDirectory() as directory:
            router = ApiRouter(JsonDealRepository(directory))

            response = router.handle("GET", "/missing")

            self.assertEqual(response.status, 404)


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

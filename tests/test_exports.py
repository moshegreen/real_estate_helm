import zipfile
from decimal import Decimal
from io import BytesIO
from unittest import TestCase

from real_estate_helm import Deal, DealIdentity
from real_estate_helm.exports import render_cash_flow_xlsx, render_deal_summary_pdf, render_ic_memo_pptx


class ExportRendererTests(TestCase):
    def test_deal_summary_pdf_has_pdf_signature(self) -> None:
        pdf = render_deal_summary_pdf(Deal(DealIdentity("PDF Deal")))

        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertIn(b"%%EOF", pdf)

    def test_cash_flow_xlsx_contains_workbook_and_sheet(self) -> None:
        xlsx = render_cash_flow_xlsx(
            [
                {
                    "period": "2027-01",
                    "category": "noi",
                    "projected": Decimal("100"),
                    "actual": Decimal("90"),
                    "variance": Decimal("-10"),
                    "variance_percent": Decimal("-0.1"),
                }
            ]
        )

        with zipfile.ZipFile(BytesIO(xlsx)) as archive:
            names = set(archive.namelist())
            sheet = archive.read("xl/worksheets/sheet1.xml").decode()

        self.assertIn("xl/workbook.xml", names)
        self.assertIn("2027-01", sheet)
        self.assertIn("variance_percent", sheet)

    def test_ic_memo_pptx_contains_slide(self) -> None:
        pptx = render_ic_memo_pptx(Deal(DealIdentity("Deck Deal")))

        with zipfile.ZipFile(BytesIO(pptx)) as archive:
            names = set(archive.namelist())
            slide = archive.read("ppt/slides/slide1.xml").decode()

        self.assertIn("ppt/presentation.xml", names)
        self.assertIn("IC Memo: Deck Deal", slide)

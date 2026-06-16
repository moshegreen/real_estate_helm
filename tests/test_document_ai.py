from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import Deal, DealIdentity, DocumentReference, SourceKind
from real_estate_helm.extraction import (
    calibrate_proposals,
    DocumentSummary,
    ExtractionProposal,
    ExtractionService,
    HttpJsonDocumentExtractionProvider,
    HttpJsonDocumentSummaryProvider,
    StaticDocumentExtractionProvider,
    StaticDocumentSummaryProvider,
)
from real_estate_helm.repository import JsonDealRepository


class DocumentAiProviderTests(TestCase):
    def test_static_extraction_provider_feeds_human_review_queue(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("AI Deal"))
            repository.save(deal)
            provider = StaticDocumentExtractionProvider(
                [
                    ExtractionProposal(
                        "purchase_price",
                        "10000000",
                        0.82,
                        DocumentReference(SourceKind.DOCUMENT, "om.pdf", page=3),
                    )
                ]
            )

            count = ExtractionService(repository).extract_document(
                deal.id,
                document_name="om.pdf",
                content=b"pdf bytes",
                provider=provider,
            )

            self.assertEqual(count, 1)
            self.assertEqual(repository.get(deal.id).extracted_facts[0].status, "pending")

    def test_static_summary_provider_returns_risks(self) -> None:
        summary = DocumentSummary(
            "Offering Memo",
            "Sponsor projects rent growth above market.",
            ["Rent growth assumption may be aggressive"],
            DocumentReference(SourceKind.DOCUMENT, "om.pdf", page=1),
        )

        result = StaticDocumentSummaryProvider(summary).summarize("om.pdf", b"pdf")

        self.assertEqual(result.risks, ["Rent growth assumption may be aggressive"])

    def test_http_json_extraction_provider_maps_payload_and_auth_headers(self) -> None:
        seen = {}

        def fetcher(url, headers, payload):
            seen["url"] = url
            seen["headers"] = headers
            seen["payload"] = payload
            return {
                "provider_reliability": 0.9,
                "proposals": [
                    {
                        "field_name": "purchase_price",
                        "value": "10000000",
                        "confidence": 0.8,
                        "source": {"page": 4, "context": "Purchase price table"},
                    }
                ],
            }

        proposals = HttpJsonDocumentExtractionProvider(
            "https://ocr.example.test/extract",
            api_key="secret",
            fetcher=fetcher,
        ).extract("om.pdf", b"pdf")

        self.assertEqual(seen["url"], "https://ocr.example.test/extract")
        self.assertEqual(seen["headers"]["authorization"], "Bearer secret")
        self.assertEqual(seen["payload"]["content_base64"], "cGRm")
        self.assertEqual(proposals[0].field_name, "purchase_price")
        self.assertEqual(proposals[0].source.page, 4)
        self.assertEqual(proposals[0].confidence, 0.77)

    def test_http_json_summary_provider_maps_risks_and_source(self) -> None:
        provider = HttpJsonDocumentSummaryProvider(
            "https://llm.example.test/summarize",
            fetcher=lambda url, headers, payload: {
                "title": "Offering Memo",
                "summary": "Sponsor projects aggressive rent growth.",
                "risks": ["Rent growth"],
                "source": {"page": 1, "context": "Executive summary"},
            },
        )

        summary = provider.summarize("om.pdf", b"pdf")

        self.assertEqual(summary.title, "Offering Memo")
        self.assertEqual(summary.risks, ["Rent growth"])
        self.assertEqual(summary.source.page, 1)

    def test_confidence_calibration_rewards_precise_sources_and_penalizes_vague_sources(self) -> None:
        precise = ExtractionProposal("noi", "1200000", 0.9, DocumentReference(SourceKind.DOCUMENT, "om.pdf", page=14))
        vague = ExtractionProposal("noi", "1200000", 0.9, DocumentReference(SourceKind.DOCUMENT, "om.pdf"))

        calibrated = calibrate_proposals([precise, vague], provider_reliability=0.8)

        self.assertEqual(calibrated[0].confidence, 0.77)
        self.assertEqual(calibrated[1].confidence, 0.57)

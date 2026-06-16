from unittest import TestCase

from real_estate_helm import AddFactRequest, CreateDealRequest, ValidationError


class SchemaValidationTests(TestCase):
    def test_create_deal_requires_name(self) -> None:
        with self.assertRaises(ValidationError):
            CreateDealRequest.parse({})

    def test_add_fact_rejects_invalid_confidence(self) -> None:
        with self.assertRaises(ValidationError):
            AddFactRequest.parse(
                {
                    "field_name": "noi",
                    "value": 1,
                    "confidence": 2,
                    "source_name": "manual",
                }
            )

    def test_api_returns_validation_error_for_bad_payload(self) -> None:
        from tempfile import TemporaryDirectory

        from real_estate_helm.api import ApiRouter
        from real_estate_helm.repository import JsonDealRepository

        with TemporaryDirectory() as directory:
            response = ApiRouter(JsonDealRepository(directory)).handle("POST", "/deals", {})

            self.assertEqual(response.status, 422)
            self.assertEqual(response.body["error"], "validation_error")

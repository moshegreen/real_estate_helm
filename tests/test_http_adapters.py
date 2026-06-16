from unittest import TestCase

from real_estate_helm.adapters import (
    HttpJsonGeocoder,
    HttpJsonImageryProvider,
    HttpJsonLocationContextProvider,
    HttpJsonMarketCompProvider,
    HttpJsonNewsProvider,
    HttpJsonPermitProvider,
    HttpJsonPropertyDataProvider,
    HttpJsonWebSourceProvider,
)
from real_estate_helm import LocationContextType, NewsClassification


class HttpAdapterTests(TestCase):
    def test_http_geocoder_maps_json_to_coordinates_and_auth_header(self) -> None:
        seen = {}

        def fetcher(url, headers):
            seen["url"] = url
            seen["headers"] = headers
            return {"latitude": 40.0, "longitude": -74.0}

        coordinates = HttpJsonGeocoder("https://geo.example.test?q={query}", api_key="secret", fetcher=fetcher).geocode(
            "10 Main Street"
        )

        self.assertEqual(coordinates.latitude, 40.0)
        self.assertIn("10+Main+Street", seen["url"])
        self.assertEqual(seen["headers"]["authorization"], "Bearer secret")

    def test_http_market_comps_and_news_map_payloads(self) -> None:
        comp_provider = HttpJsonMarketCompProvider(
            "https://comps.example.test?q={query}&asset={asset_type}",
            fetcher=lambda url, headers: {"comps": [{"name": "Sale", "value": "12000000", "comp_type": "sale"}]},
        )
        news_provider = HttpJsonNewsProvider(
            "https://news.example.test?q={query}",
            fetcher=lambda url, headers: {
                "news": [
                    {
                        "title": "Permit approved",
                        "url": "https://example.test",
                        "classification": "material_positive",
                    }
                ]
            },
        )

        self.assertEqual(comp_provider.comps_for("10 Main")[0].name, "Sale")
        self.assertEqual(news_provider.news_for("10 Main")[0].classification, NewsClassification.MATERIAL_POSITIVE)

    def test_http_imagery_and_web_sources_map_payloads(self) -> None:
        imagery = HttpJsonImageryProvider(
            "https://image.example.test?q={query}",
            fetcher=lambda url, headers: {
                "snapshots": [{"captured_at": "2027-01-01", "storage_uri": "s3://snap.jpg", "source": "sentinel"}]
            },
        )
        sources = HttpJsonWebSourceProvider(
            "https://sources.example.test?q={query}",
            fetcher=lambda url, headers: {
                "sources": [{"title": "Permit portal", "url": "https://example.test", "source_type": "permit"}]
            },
        )

        self.assertEqual(imagery.snapshots_for("10 Main")[0].source, "sentinel")
        self.assertEqual(sources.sources_for("10 Main")[0].source_type, "permit")

    def test_http_property_data_and_permit_providers_map_payloads(self) -> None:
        property_data = HttpJsonPropertyDataProvider(
            "https://property.example.test?q={query}",
            fetcher=lambda url, headers: {
                "property_records": [
                    {
                        "source": "assessor",
                        "parcel_id": "123-abc",
                        "assessed_value": "10000000",
                        "zoning": "TOD",
                        "flood_zone": "X",
                    }
                ]
            },
        )
        permits = HttpJsonPermitProvider(
            "https://permits.example.test?q={query}",
            fetcher=lambda url, headers: {
                "permits": [
                    {
                        "permit_number": "P-1",
                        "permit_type": "building",
                        "status": "issued",
                        "issued_date": "2027-01-02",
                    }
                ]
            },
        )

        self.assertEqual(property_data.property_records_for("10 Main")[0].zoning, "TOD")
        self.assertEqual(permits.permits_for("10 Main")[0].permit_number, "P-1")

    def test_http_location_context_provider_maps_payload(self) -> None:
        provider = HttpJsonLocationContextProvider(
            "https://context.example.test?q={query}",
            fetcher=lambda url, headers: {
                "location_context": [
                    {
                        "item_type": "transit",
                        "name": "Central Station",
                        "distance_miles": 0.4,
                        "source": "maps",
                        "latitude": 32.1,
                        "longitude": 34.8,
                    }
                ]
            },
        )

        items = provider.context_for("10 Main")

        self.assertEqual(items[0].item_type, LocationContextType.TRANSIT)
        self.assertEqual(items[0].coordinates.latitude, 32.1)

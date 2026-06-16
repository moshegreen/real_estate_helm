from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import (
    Address,
    Asset,
    Coordinates,
    Deal,
    DealIdentity,
    ImagerySnapshot,
    LocationContextItem,
    LocationContextType,
    MarketComp,
    NewsClassification,
    NewsEvent,
    PermitEvent,
    PropertyRecord,
    WebSource,
)
from real_estate_helm.adapters import (
    StaticGeocoder,
    StaticImageryProvider,
    StaticLocationContextProvider,
    StaticMarketCompProvider,
    StaticNewsProvider,
    StaticPermitProvider,
    StaticPropertyDataProvider,
    StaticWebSourceProvider,
)
from real_estate_helm.enrichment import EnrichmentService
from real_estate_helm.repository import JsonDealRepository


class EnrichmentServiceTests(TestCase):
    def test_static_providers_enrich_location_and_market_context(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity("Transit Apartments"))
            deal.assets.append(Asset("Transit Apartments", address=Address("10 Station Road"), asset_type="multifamily"))
            repository.save(deal)
            service = EnrichmentService(
                repository,
                geocoder=StaticGeocoder({"10 Station Road": Coordinates(40.0, -74.0)}),
                market_comps=StaticMarketCompProvider(
                    {"10 Station Road": [MarketComp("Nearby sale", "sale", Decimal("22000000"))]}
                ),
                news=StaticNewsProvider(
                    {
                        "10 Station Road": [
                            NewsEvent(
                                "Station expansion approved",
                                "https://example.test/station",
                                NewsClassification.MATERIAL_POSITIVE,
                            )
                        ]
                    }
                ),
                imagery=StaticImageryProvider(
                    {"10 Station Road": [ImagerySnapshot("2027-01-01", "s3://image.jpg", "sentinel")]}
                ),
                web_sources=StaticWebSourceProvider(
                    {"10 Station Road": [WebSource("Planning portal", "https://example.test/plan", "permit")]}
                ),
                property_data=StaticPropertyDataProvider(
                    {"10 Station Road": [PropertyRecord("assessor", parcel_id="123-abc", zoning="TOD")]}
                ),
                permits=StaticPermitProvider(
                    {"10 Station Road": [PermitEvent("P-1", "building", "issued", issued_date="2027-01-02")]}
                ),
                location_context=StaticLocationContextProvider(
                    {"10 Station Road": [LocationContextItem(LocationContextType.TRANSIT, "Station", 0.2, "maps")]}
                ),
            )

            self.assertEqual(service.enrich_location(deal.id), 1)
            counts = service.enrich_market_context(deal.id)
            restored = repository.get(deal.id)

            self.assertEqual(restored.assets[0].coordinates.latitude, 40.0)
            self.assertEqual(counts["market_comps"], 1)
            self.assertEqual(restored.news_events[0].classification, NewsClassification.MATERIAL_POSITIVE)
            self.assertEqual(restored.imagery_snapshots[0].source, "sentinel")
            self.assertEqual(restored.web_sources[0].source_type, "permit")
            self.assertEqual(counts["property_records"], 1)
            self.assertEqual(counts["permit_events"], 1)
            self.assertEqual(counts["location_context"], 1)
            self.assertEqual(restored.property_records[0].zoning, "TOD")
            self.assertEqual(restored.location_context[0].item_type, LocationContextType.TRANSIT)
            self.assertEqual(restored.permit_events[0].permit_number, "P-1")

"""Deal enrichment workflows built on provider adapters."""

from __future__ import annotations

from real_estate_helm.adapters import (
    Geocoder,
    ImageryProvider,
    LocationContextProvider,
    MarketCompProvider,
    NewsProvider,
    PermitProvider,
    PropertyDataProvider,
    WebSourceProvider,
)
from real_estate_helm.repository import JsonDealRepository


class EnrichmentService:
    def __init__(
        self,
        repository: JsonDealRepository,
        *,
        geocoder: Geocoder | None = None,
        market_comps: MarketCompProvider | None = None,
        news: NewsProvider | None = None,
        imagery: ImageryProvider | None = None,
        web_sources: WebSourceProvider | None = None,
        property_data: PropertyDataProvider | None = None,
        permits: PermitProvider | None = None,
        location_context: LocationContextProvider | None = None,
    ) -> None:
        self.repository = repository
        self.geocoder = geocoder
        self.market_comps = market_comps
        self.news = news
        self.imagery = imagery
        self.web_sources = web_sources
        self.property_data = property_data
        self.permits = permits
        self.location_context = location_context

    def enrich_location(self, deal_id: str) -> int:
        if self.geocoder is None:
            return 0
        deal = self.repository.get(deal_id)
        updated = 0
        for asset in deal.assets:
            if asset.coordinates is None and asset.address is not None:
                coordinates = self.geocoder.geocode(asset.address.line1)
                if coordinates is not None:
                    asset.coordinates = coordinates
                    updated += 1
        if updated:
            self.repository.save(deal)
        return updated

    def enrich_market_context(self, deal_id: str) -> dict[str, int]:
        deal = self.repository.get(deal_id)
        counts = {
            "market_comps": 0,
            "news_events": 0,
            "imagery_snapshots": 0,
            "web_sources": 0,
            "property_records": 0,
            "permit_events": 0,
            "location_context": 0,
        }
        for asset in deal.assets:
            if asset.address is None:
                continue
            query = asset.address.line1
            if self.market_comps is not None:
                items = self.market_comps.comps_for(query, asset.asset_type)
                deal.market_comps.extend(items)
                counts["market_comps"] += len(items)
            if self.news is not None:
                items = self.news.news_for(query)
                deal.news_events.extend(items)
                counts["news_events"] += len(items)
            if self.imagery is not None:
                items = self.imagery.snapshots_for(query)
                deal.imagery_snapshots.extend(items)
                counts["imagery_snapshots"] += len(items)
            if self.web_sources is not None:
                items = self.web_sources.sources_for(query)
                deal.web_sources.extend(items)
                counts["web_sources"] += len(items)
            if self.property_data is not None:
                items = self.property_data.property_records_for(query)
                deal.property_records.extend(items)
                counts["property_records"] += len(items)
            if self.permits is not None:
                items = self.permits.permits_for(query)
                deal.permit_events.extend(items)
                counts["permit_events"] += len(items)
            if self.location_context is not None:
                items = self.location_context.context_for(query)
                deal.location_context.extend(items)
                counts["location_context"] += len(items)
        if any(counts.values()):
            self.repository.save(deal)
        return counts

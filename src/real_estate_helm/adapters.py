"""Provider adapter contracts for external enrichment data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from real_estate_helm.domain import (
    Coordinates,
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


class Geocoder(Protocol):
    def geocode(self, address: str) -> Coordinates | None:
        """Return coordinates for an address, or None when unavailable."""


class MarketCompProvider(Protocol):
    def comps_for(self, address: str, asset_type: str | None = None) -> list[MarketComp]:
        """Return comparable sales, rents, or listings."""


class NewsProvider(Protocol):
    def news_for(self, query: str) -> list[NewsEvent]:
        """Return classified local news events."""


class ImageryProvider(Protocol):
    def snapshots_for(self, address: str) -> list[ImagerySnapshot]:
        """Return available satellite or site imagery snapshots."""


class WebSourceProvider(Protocol):
    def sources_for(self, query: str) -> list[WebSource]:
        """Return relevant web sources for the deal or asset."""


class PropertyDataProvider(Protocol):
    def property_records_for(self, address: str) -> list[PropertyRecord]:
        """Return assessor, parcel, zoning, flood, and physical property records."""


class PermitProvider(Protocol):
    def permits_for(self, address: str) -> list[PermitEvent]:
        """Return permit and planning-board activity for a property."""


class LocationContextProvider(Protocol):
    def context_for(self, address: str) -> list[LocationContextItem]:
        """Return nearby roads, transit, schools, employment centers, risks, and competing properties."""


@dataclass(frozen=True)
class StaticGeocoder:
    records: dict[str, Coordinates]

    def geocode(self, address: str) -> Coordinates | None:
        return self.records.get(address)


@dataclass(frozen=True)
class StaticMarketCompProvider:
    records: dict[str, list[MarketComp]]

    def comps_for(self, address: str, asset_type: str | None = None) -> list[MarketComp]:
        comps = self.records.get(address, [])
        if asset_type is None:
            return list(comps)
        return [comp for comp in comps if comp.comp_type == asset_type or comp.comp_type in {"sale", "rent"}]


@dataclass(frozen=True)
class StaticNewsProvider:
    records: dict[str, list[NewsEvent]]

    def news_for(self, query: str) -> list[NewsEvent]:
        return list(self.records.get(query, []))


@dataclass(frozen=True)
class StaticImageryProvider:
    records: dict[str, list[ImagerySnapshot]]

    def snapshots_for(self, address: str) -> list[ImagerySnapshot]:
        return list(self.records.get(address, []))


@dataclass(frozen=True)
class StaticWebSourceProvider:
    records: dict[str, list[WebSource]]

    def sources_for(self, query: str) -> list[WebSource]:
        return list(self.records.get(query, []))


@dataclass(frozen=True)
class StaticPropertyDataProvider:
    records: dict[str, list[PropertyRecord]]

    def property_records_for(self, address: str) -> list[PropertyRecord]:
        return list(self.records.get(address, []))


@dataclass(frozen=True)
class StaticPermitProvider:
    records: dict[str, list[PermitEvent]]

    def permits_for(self, address: str) -> list[PermitEvent]:
        return list(self.records.get(address, []))


@dataclass(frozen=True)
class StaticLocationContextProvider:
    records: dict[str, list[LocationContextItem]]

    def context_for(self, address: str) -> list[LocationContextItem]:
        return list(self.records.get(address, []))


JsonFetcher = Callable[[str, dict[str, str]], dict[str, Any]]


def default_json_fetcher(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True)
class HttpJsonGeocoder:
    url_template: str
    api_key: str | None = None
    fetcher: JsonFetcher = default_json_fetcher

    def geocode(self, address: str) -> Coordinates | None:
        payload = self.fetcher(self.url_template.format(query=quote_plus(address)), _headers(self.api_key))
        if payload.get("latitude") is None or payload.get("longitude") is None:
            return None
        return Coordinates(float(payload["latitude"]), float(payload["longitude"]))


@dataclass(frozen=True)
class HttpJsonMarketCompProvider:
    url_template: str
    api_key: str | None = None
    fetcher: JsonFetcher = default_json_fetcher

    def comps_for(self, address: str, asset_type: str | None = None) -> list[MarketComp]:
        payload = self.fetcher(
            self.url_template.format(query=quote_plus(address), asset_type=quote_plus(asset_type or "")),
            _headers(self.api_key),
        )
        return [
            MarketComp(
                name=item["name"],
                comp_type=item.get("comp_type", "sale"),
                value=item["value"],
                address=item.get("address"),
                distance_miles=item.get("distance_miles"),
                source=item.get("source"),
            )
            for item in payload.get("comps", [])
        ]


@dataclass(frozen=True)
class HttpJsonNewsProvider:
    url_template: str
    api_key: str | None = None
    fetcher: JsonFetcher = default_json_fetcher

    def news_for(self, query: str) -> list[NewsEvent]:
        payload = self.fetcher(self.url_template.format(query=quote_plus(query)), _headers(self.api_key))
        return [
            NewsEvent(
                title=item["title"],
                url=item["url"],
                classification=NewsClassification(item.get("classification", NewsClassification.WATCH.value)),
                published_at=item.get("published_at"),
                summary=item.get("summary"),
            )
            for item in payload.get("news", [])
        ]


@dataclass(frozen=True)
class HttpJsonImageryProvider:
    url_template: str
    api_key: str | None = None
    fetcher: JsonFetcher = default_json_fetcher

    def snapshots_for(self, address: str) -> list[ImagerySnapshot]:
        payload = self.fetcher(self.url_template.format(query=quote_plus(address)), _headers(self.api_key))
        return [
            ImagerySnapshot(
                captured_at=item["captured_at"],
                storage_uri=item["storage_uri"],
                source=item.get("source", "http_json"),
                notes=item.get("notes"),
            )
            for item in payload.get("snapshots", [])
        ]


@dataclass(frozen=True)
class HttpJsonWebSourceProvider:
    url_template: str
    api_key: str | None = None
    fetcher: JsonFetcher = default_json_fetcher

    def sources_for(self, query: str) -> list[WebSource]:
        payload = self.fetcher(self.url_template.format(query=quote_plus(query)), _headers(self.api_key))
        return [
            WebSource(
                title=item["title"],
                url=item["url"],
                source_type=item.get("source_type", "web"),
            )
            for item in payload.get("sources", [])
        ]


@dataclass(frozen=True)
class HttpJsonPropertyDataProvider:
    url_template: str
    api_key: str | None = None
    fetcher: JsonFetcher = default_json_fetcher

    def property_records_for(self, address: str) -> list[PropertyRecord]:
        payload = self.fetcher(self.url_template.format(query=quote_plus(address)), _headers(self.api_key))
        return [
            PropertyRecord(
                source=item.get("source", "http_json"),
                parcel_id=item.get("parcel_id"),
                assessed_value=item.get("assessed_value"),
                owner_name=item.get("owner_name"),
                zoning=item.get("zoning"),
                flood_zone=item.get("flood_zone"),
                year_built=item.get("year_built"),
                building_size=item.get("building_size"),
                land_size=item.get("land_size"),
            )
            for item in payload.get("property_records", [])
        ]


@dataclass(frozen=True)
class HttpJsonPermitProvider:
    url_template: str
    api_key: str | None = None
    fetcher: JsonFetcher = default_json_fetcher

    def permits_for(self, address: str) -> list[PermitEvent]:
        payload = self.fetcher(self.url_template.format(query=quote_plus(address)), _headers(self.api_key))
        return [
            PermitEvent(
                permit_number=item["permit_number"],
                permit_type=item.get("permit_type", "unknown"),
                status=item.get("status", "unknown"),
                filed_date=item.get("filed_date"),
                issued_date=item.get("issued_date"),
                description=item.get("description"),
                source_url=item.get("source_url"),
            )
            for item in payload.get("permits", [])
        ]


@dataclass(frozen=True)
class HttpJsonLocationContextProvider:
    url_template: str
    api_key: str | None = None
    fetcher: JsonFetcher = default_json_fetcher

    def context_for(self, address: str) -> list[LocationContextItem]:
        payload = self.fetcher(self.url_template.format(query=quote_plus(address)), _headers(self.api_key))
        return [
            LocationContextItem(
                item_type=LocationContextType(item.get("item_type", LocationContextType.OTHER.value)),
                name=item["name"],
                distance_miles=item.get("distance_miles"),
                source=item.get("source"),
                notes=item.get("notes"),
                coordinates=Coordinates(float(item["latitude"]), float(item["longitude"]))
                if item.get("latitude") is not None and item.get("longitude") is not None
                else None,
            )
            for item in payload.get("location_context", [])
        ]


def _headers(api_key: str | None) -> dict[str, str]:
    headers = {"accept": "application/json"}
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    return headers

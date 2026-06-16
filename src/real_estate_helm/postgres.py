"""PostgreSQL persistence mapping for the normalized schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from real_estate_helm.domain import Deal
from real_estate_helm.serialization import deal_to_dict


@dataclass(frozen=True)
class SqlStatement:
    sql: str
    params: tuple[Any, ...]


class PostgresDealSqlMapper:
    """Build parameterized SQL statements for persisting a deal.

    A runtime adapter can execute these statements with psycopg or SQLAlchemy.
    Keeping mapping generation separate makes it testable without a database.
    """

    def upsert_deal(self, deal: Deal) -> list[SqlStatement]:
        payload = deal_to_dict(deal)
        statements = [
            SqlStatement(
                """
                INSERT INTO deals (id, name, status, asset_type, source, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                  name = EXCLUDED.name,
                  status = EXCLUDED.status,
                  asset_type = EXCLUDED.asset_type,
                  source = EXCLUDED.source,
                  updated_at = EXCLUDED.updated_at
                """.strip(),
                (
                    payload["id"],
                    payload["identity"]["name"],
                    payload["status"],
                    payload["identity"]["asset_type"],
                    payload["identity"]["source"],
                    payload["received_at"],
                    payload["received_at"],
                ),
            )
        ]
        statements.extend(self._asset_statements(payload))
        statements.extend(self._document_statements(payload))
        statements.extend(self._fact_statements(payload))
        statements.extend(self._assumption_statements(payload))
        statements.extend(self._scenario_statements(payload))
        statements.extend(self._rent_roll_statements(payload))
        statements.extend(self._alert_statements(payload))
        return statements

    def _asset_statements(self, payload: dict[str, Any]) -> list[SqlStatement]:
        return [
            SqlStatement(
                """
                INSERT INTO assets (id, deal_id, name, address, city, state, country, parcel_id, asset_type, unit_count, building_size, land_size, year_built)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, asset_type = EXCLUDED.asset_type
                """.strip(),
                (
                    asset["id"],
                    payload["id"],
                    asset["name"],
                    asset["address"]["line1"] if asset.get("address") else None,
                    asset["address"]["city"] if asset.get("address") else None,
                    asset["address"]["state"] if asset.get("address") else None,
                    asset["address"]["country"] if asset.get("address") else None,
                    asset.get("parcel_id"),
                    asset.get("asset_type"),
                    asset.get("unit_count"),
                    asset.get("building_size"),
                    asset.get("land_size"),
                    asset.get("year_built"),
                ),
            )
            for asset in payload["assets"]
        ]

    def _document_statements(self, payload: dict[str, Any]) -> list[SqlStatement]:
        return [
            SqlStatement(
                """
                INSERT INTO documents (id, deal_id, name, document_type, storage_uri, sha256, uploaded_by, uploaded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET storage_uri = EXCLUDED.storage_uri, sha256 = EXCLUDED.sha256
                """.strip(),
                (
                    document["id"],
                    payload["id"],
                    document["name"],
                    document["document_type"],
                    document["storage_uri"],
                    document["sha256"],
                    document["uploaded_by"],
                    document["uploaded_at"]["value"],
                ),
            )
            for document in payload["documents"]
        ]

    def _fact_statements(self, payload: dict[str, Any]) -> list[SqlStatement]:
        return [
            SqlStatement(
                """
                INSERT INTO extracted_facts (id, deal_id, field_name, value, confidence, status, source, extracted_at, reviewed_at, reviewer, review_note)
                VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET value = EXCLUDED.value, status = EXCLUDED.status
                """.strip(),
                (
                    fact["id"],
                    payload["id"],
                    fact["field_name"],
                    _json_param(fact["value"]),
                    fact["confidence"],
                    fact["status"],
                    _json_param(fact["source"]),
                    fact["extracted_at"],
                    fact["reviewed_at"],
                    fact["reviewer"],
                    fact["review_note"],
                ),
            )
            for fact in payload["extracted_facts"]
        ]

    def _assumption_statements(self, payload: dict[str, Any]) -> list[SqlStatement]:
        return [
            SqlStatement(
                """
                INSERT INTO assumptions (id, deal_id, scenario_id, name, value, rationale, source_fact_id, created_at)
                VALUES (%s, %s, NULL, %s, %s::jsonb, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET value = EXCLUDED.value, rationale = EXCLUDED.rationale
                """.strip(),
                (
                    assumption["id"],
                    payload["id"],
                    assumption["name"],
                    _json_param(assumption["value"]),
                    assumption["rationale"],
                    assumption["source_fact_id"],
                    _timestamp_param(assumption["created_at"]),
                ),
            )
            for assumption in payload["assumptions"]
        ]

    def _scenario_statements(self, payload: dict[str, Any]) -> list[SqlStatement]:
        statements = []
        for scenario in payload["scenarios"]:
            statements.append(
                SqlStatement(
                    """
                    INSERT INTO scenarios (id, deal_id, name, scenario_type, outputs, created_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (id) DO UPDATE SET outputs = EXCLUDED.outputs
                    """.strip(),
                    (
                        scenario["id"],
                        payload["id"],
                        scenario["name"],
                        scenario["scenario_type"],
                        _json_param(scenario["outputs"]),
                        payload["received_at"],
                    ),
                )
            )
            for metric_name, value in scenario["outputs"].items():
                statements.append(
                    SqlStatement(
                        """
                        INSERT INTO scenario_outputs (id, scenario_id, metric_name, value, calculated_at)
                        VALUES (gen_random_uuid(), %s, %s, %s::jsonb, %s)
                        """.strip(),
                        (scenario["id"], metric_name, _json_param(value), payload["received_at"]),
                    )
                )
        return statements

    def _alert_statements(self, payload: dict[str, Any]) -> list[SqlStatement]:
        return [
            SqlStatement(
                """
                INSERT INTO alerts (id, deal_id, severity, category, title, description, source, financial_impact, recommended_action, owner, due_date, status, created_at, resolved_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, resolved_at = EXCLUDED.resolved_at
                """.strip(),
                (
                    alert["id"],
                    payload["id"],
                    alert["severity"],
                    alert["category"],
                    alert["title"],
                    alert["description"],
                    alert["source"],
                    alert["financial_impact"],
                    alert["recommended_action"],
                    alert["owner"],
                    alert["due_date"],
                    alert["status"],
                    _timestamp_param(alert["created_at"]),
                    _timestamp_param(alert["resolved_at"]) if alert["resolved_at"] else None,
                ),
            )
            for alert in payload["alerts"]
        ]

    def _rent_roll_statements(self, payload: dict[str, Any]) -> list[SqlStatement]:
        return [
            SqlStatement(
                """
                INSERT INTO rent_rolls (id, deal_id, as_of_date, unit, tenant_name, monthly_rent, market_rent, occupied, concessions, bad_debt, lease_start, lease_end, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                  tenant_name = EXCLUDED.tenant_name,
                  monthly_rent = EXCLUDED.monthly_rent,
                  market_rent = EXCLUDED.market_rent,
                  occupied = EXCLUDED.occupied,
                  concessions = EXCLUDED.concessions,
                  bad_debt = EXCLUDED.bad_debt,
                  lease_start = EXCLUDED.lease_start,
                  lease_end = EXCLUDED.lease_end,
                  source = EXCLUDED.source
                """.strip(),
                (
                    row["id"],
                    payload["id"],
                    row["as_of_date"],
                    row["unit"],
                    row["tenant_name"],
                    _decimal_param(row["monthly_rent"]),
                    _decimal_param(row["market_rent"]),
                    row["occupied"],
                    _decimal_param(row["concessions"]),
                    _decimal_param(row["bad_debt"]),
                    row["lease_start"],
                    row["lease_end"],
                    _json_param(row["source"]),
                ),
            )
            for row in payload["rent_roll"]
        ]


def _json_param(value: Any) -> str:
    import json

    return json.dumps(value, sort_keys=True)


def _timestamp_param(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def _decimal_param(value: Any) -> Any:
    if isinstance(value, dict) and value.get("__type__") == "decimal":
        return value["value"]
    return value


class PostgresMigrationRunner:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def apply_schema(self, schema_path: Path | str) -> None:
        sql = Path(schema_path).read_text()
        with self.connection.cursor() as cursor:
            cursor.execute(sql)
        self.connection.commit()


class PostgresDealRepository:
    """DB-API execution adapter for PostgreSQL deal writes."""

    def __init__(self, connection: Any, mapper: PostgresDealSqlMapper | None = None) -> None:
        self.connection = connection
        self.mapper = mapper or PostgresDealSqlMapper()

    def save(self, deal: Deal) -> int:
        statements = self.mapper.upsert_deal(deal)
        with self.connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement.sql, statement.params)
        self.connection.commit()
        return len(statements)

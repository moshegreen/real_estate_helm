"""Scenario comparison and version helpers."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from real_estate_helm.domain import Assumption, Scenario, ScenarioType
from real_estate_helm.underwriting import variance, variance_percent


@dataclass(frozen=True)
class ScenarioDiff:
    metric: str
    left_value: Any
    right_value: Any
    delta: Any
    delta_percent: Any | None = None


def clone_scenario_version(
    scenario: Scenario,
    *,
    name: str,
    scenario_type: ScenarioType | None = None,
) -> Scenario:
    return Scenario(
        name=name,
        scenario_type=scenario_type or scenario.scenario_type,
        assumptions=[
            Assumption(
                name=assumption.name,
                value=assumption.value,
                rationale=f"Copied from scenario {scenario.name}: {assumption.rationale}",
                source_fact_id=assumption.source_fact_id,
            )
            for assumption in scenario.assumptions
        ],
        outputs=dict(scenario.outputs),
    )


def compare_scenario_outputs(left: Scenario, right: Scenario) -> list[ScenarioDiff]:
    metrics = sorted(set(left.outputs) | set(right.outputs))
    diffs = []
    for metric in metrics:
        left_value = left.outputs.get(metric)
        right_value = right.outputs.get(metric)
        delta = None
        delta_percent = None
        if _is_number(left_value) and _is_number(right_value):
            delta = variance(right_value, left_value)
            delta_percent = variance_percent(right_value, left_value) if Decimal(str(left_value)) != 0 else None
        diffs.append(ScenarioDiff(metric, left_value, right_value, delta, delta_percent))
    return diffs


def compare_assumptions(left: Scenario, right: Scenario) -> list[ScenarioDiff]:
    left_values = {assumption.name: assumption.value for assumption in left.assumptions}
    right_values = {assumption.name: assumption.value for assumption in right.assumptions}
    names = sorted(set(left_values) | set(right_values))
    return [
        ScenarioDiff(
            metric=name,
            left_value=left_values.get(name),
            right_value=right_values.get(name),
            delta=variance(right_values[name], left_values[name])
            if _is_number(left_values.get(name)) and _is_number(right_values.get(name))
            else None,
            delta_percent=variance_percent(right_values[name], left_values[name])
            if _is_number(left_values.get(name))
            and _is_number(right_values.get(name))
            and Decimal(str(left_values[name])) != 0
            else None,
        )
        for name in names
    ]


def scenario_export_rows(scenario: Scenario) -> list[dict[str, Any]]:
    rows = [
        {
            "section": "assumption",
            "name": assumption.name,
            "value": assumption.value,
            "rationale": assumption.rationale,
        }
        for assumption in scenario.assumptions
    ]
    rows.extend(
        {
            "section": "output",
            "name": metric,
            "value": value,
            "rationale": "",
        }
        for metric, value in sorted(scenario.outputs.items())
    )
    return rows


def export_scenario_csv(scenario: Scenario) -> str:
    output = io.StringIO()
    fieldnames = ["section", "name", "value", "rationale"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in scenario_export_rows(scenario):
        writer.writerow(row)
    return output.getvalue()


def _is_number(value: Any) -> bool:
    try:
        Decimal(str(value))
    except Exception:
        return False
    return value is not None

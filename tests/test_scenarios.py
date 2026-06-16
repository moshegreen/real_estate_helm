from decimal import Decimal
from unittest import TestCase

from real_estate_helm import Assumption, Scenario, ScenarioType
from real_estate_helm.scenarios import (
    clone_scenario_version,
    compare_assumptions,
    compare_scenario_outputs,
    export_scenario_csv,
    scenario_export_rows,
)


class ScenarioEngineTests(TestCase):
    def test_clone_scenario_version_preserves_independent_assumptions_and_outputs(self) -> None:
        base = Scenario("Base", ScenarioType.ANALYST_BASE_CASE)
        base.assumptions.append(Assumption("rent_growth", Decimal("0.03"), "Market rent trend"))
        base.outputs["irr"] = Decimal("0.14")

        reforecast = clone_scenario_version(base, name="Current Reforecast", scenario_type=ScenarioType.CURRENT_REFORECAST)
        reforecast.assumptions[0] = Assumption("rent_growth", Decimal("0.02"), "Updated reforecast")
        reforecast.outputs["irr"] = Decimal("0.11")

        self.assertEqual(base.assumptions[0].value, Decimal("0.03"))
        self.assertEqual(reforecast.scenario_type, ScenarioType.CURRENT_REFORECAST)
        self.assertEqual(reforecast.outputs["irr"], Decimal("0.11"))

    def test_compare_scenario_outputs_and_assumptions(self) -> None:
        sponsor = Scenario("Sponsor", ScenarioType.SPONSOR_CASE)
        sponsor.assumptions.append(Assumption("exit_cap_rate", Decimal("0.0525"), "Sponsor model"))
        sponsor.outputs["irr"] = Decimal("0.18")
        base = Scenario("Base", ScenarioType.ANALYST_BASE_CASE)
        base.assumptions.append(Assumption("exit_cap_rate", Decimal("0.0575"), "Internal comps"))
        base.outputs["irr"] = Decimal("0.14")

        output_diff = compare_scenario_outputs(sponsor, base)[0]
        assumption_diff = compare_assumptions(sponsor, base)[0]

        self.assertEqual(output_diff.metric, "irr")
        self.assertEqual(output_diff.delta, Decimal("-0.04"))
        self.assertEqual(assumption_diff.metric, "exit_cap_rate")
        self.assertEqual(assumption_diff.delta, Decimal("0.0050"))

    def test_scenario_export_rows_and_csv_include_assumptions_and_outputs(self) -> None:
        base = Scenario("Base", ScenarioType.ANALYST_BASE_CASE)
        base.assumptions.append(Assumption("rent_growth", Decimal("0.03"), "Market rent trend"))
        base.outputs["irr"] = Decimal("0.14")

        rows = scenario_export_rows(base)
        csv_text = export_scenario_csv(base)

        self.assertEqual(rows[0]["section"], "assumption")
        self.assertEqual(rows[1]["section"], "output")
        self.assertIn("section,name,value,rationale", csv_text)
        self.assertIn("assumption,rent_growth,0.03,Market rent trend", csv_text)
        self.assertIn("output,irr,0.14,", csv_text)

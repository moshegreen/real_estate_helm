from datetime import date
from decimal import Decimal
from unittest import TestCase

from real_estate_helm import (
    Alert,
    AlertSeverity,
    Assumption,
    Address,
    Asset,
    CapexItem,
    CashFlowRecord,
    CashFlowType,
    Coordinates,
    Deal,
    DealIdentity,
    DealStatus,
    DebtTerms,
    DevelopmentBudget,
    DevelopmentMilestone,
    DocumentReference,
    ExtractedFact,
    FactReviewStatus,
    InvestmentDecision,
    Lease,
    LocationContextItem,
    LocationContextType,
    MilestoneStatus,
    MarketComp,
    NewsClassification,
    NewsEvent,
    Obligation,
    ObligationType,
    PermitEvent,
    PropertyRecord,
    RentRollEntry,
    Scenario,
    ScenarioType,
    SourceKind,
    Tenant,
    UserRole,
)
from real_estate_helm.analytics import (
    actual_vs_underwritten,
    assets_within_radius,
    bad_debt_total,
    cash_flow_variances,
    concessions_total,
    distance_km,
    exposure_by_asset_type,
    exposure_by_geography,
    exposure_by_sponsor,
    lease_expiry_schedule,
    market_rent_gap,
    occupancy_rate,
    open_alerts,
    portfolio_dashboard_metrics,
    rejected_deal_hindsight,
    rejected_deals,
    rent_roll_occupancy_rate,
    tenant_concentration,
    vacancy_rate,
    weighted_average_lease_term,
)
from real_estate_helm.monitoring import (
    add_new_alerts,
    cash_flow_variance_alerts,
    competing_development_alerts,
    debt_maturity_alerts,
    development_delay_alerts,
    dscr_covenant_alerts,
    contingency_consumption_alerts,
    comparable_sale_alerts,
    insurance_cost_alerts,
    local_news_alerts,
    monitoring_alerts,
    obligation_alerts,
    permit_risk_alerts,
    property_assessment_alerts,
    sponsor_litigation_alerts,
    tenant_credit_alerts,
)
from real_estate_helm.reporting import (
    export_cash_flow_variance_csv,
    export_deal_json,
    generate_development_progress_report_markdown,
    generate_ic_memo_markdown,
    generate_lender_covenant_report_markdown,
    generate_monthly_performance_report_markdown,
    generate_monitoring_report_markdown,
    generate_portfolio_report_markdown,
    generate_rejected_deal_review_markdown,
)
from real_estate_helm.security import can, require
from real_estate_helm.underwriting import (
    debt_service_coverage_ratio,
    development_budget_total,
    equity_multiple,
    total_profit,
    variance,
    variance_percent,
)


class AnalyticsMonitoringReportingTests(TestCase):
    def test_underwriting_and_cash_flow_variance_metrics(self) -> None:
        self.assertEqual(debt_service_coverage_ratio(1200000, 1000000), Decimal("1.2"))
        self.assertEqual(equity_multiple(4500000, 3000000), Decimal("1.5"))
        self.assertEqual(total_profit(4500000, 3000000), Decimal("1500000"))
        self.assertEqual(variance(920000, 1000000), Decimal("-80000"))
        self.assertEqual(variance_percent(920000, 1000000), Decimal("-0.08"))
        self.assertEqual(
            development_budget_total(land_cost=1, hard_costs=2, soft_costs=3, contingency=4),
            Decimal("10"),
        )

    def test_portfolio_analytics_and_alert_rules(self) -> None:
        deal = Deal(DealIdentity("Oak Retail", asset_type="retail"))
        deal.projected_cash_flows.append(CashFlowRecord("2027-01", Decimal("100000"), CashFlowType.PROJECTED, "noi"))
        deal.actual_cash_flows.append(CashFlowRecord("2027-01", Decimal("90000"), CashFlowType.ACTUAL, "noi"))
        deal.development_milestones.append(
            DevelopmentMilestone("Foundation complete", "2027-01-15", MilestoneStatus.ON_TRACK)
        )
        rejected = Deal(DealIdentity("Pine Office", asset_type="office"))
        rejected.reject("principal", "Market risk")

        rows = cash_flow_variances(deal)
        self.assertEqual(rows[0]["variance_percent"], Decimal("-0.1"))
        new_alerts = cash_flow_variance_alerts(deal)
        new_alerts.extend(development_delay_alerts(deal, today=date(2027, 2, 1)))
        self.assertEqual(add_new_alerts(deal, new_alerts), 2)

        self.assertEqual(exposure_by_asset_type([deal, rejected]), {"retail": 1, "office": 1})
        self.assertEqual(len(open_alerts([deal, rejected])), 2)
        self.assertEqual(rejected_deals([deal, rejected]), [rejected])

    def test_portfolio_dashboard_metrics_include_plan_level_summary_fields(self) -> None:
        deal = Deal(DealIdentity("Dashboard Deal", asset_type="retail", sponsor="SponsorCo"))
        deal.assumptions.append(Assumption("current_value", Decimal("12000000"), "Latest valuation"))
        deal.assumptions.append(Assumption("equity_invested", Decimal("4000000"), "Capital account"))
        deal.assumptions.append(Assumption("unrealized_gain", Decimal("1000000"), "Current valuation"))
        deal.debt_terms.append(DebtTerms(lender="Bank", debt_amount=Decimal("7000000"), maturity_date="2027-06-01"))
        deal.obligations.append(
            Obligation("Fund draw", "2026-07-15", ObligationType.CAPITAL_CALL, amount=Decimal("250000"))
        )
        scenario = Scenario("Base", ScenarioType.ANALYST_BASE_CASE)
        scenario.outputs["irr"] = Decimal("0.14")
        scenario.outputs["equity_multiple"] = Decimal("1.8")
        deal.scenarios.append(scenario)

        metrics = portfolio_dashboard_metrics([deal])

        self.assertEqual(metrics["current_portfolio_value"], Decimal("12000000"))
        self.assertEqual(metrics["equity_invested"], Decimal("4000000"))
        self.assertEqual(metrics["unrealized_gains"], Decimal("1000000"))
        self.assertEqual(exposure_by_sponsor([deal]), {"SponsorCo": 1})
        self.assertEqual(metrics["exposure_by_sponsor"], {"SponsorCo": 1})
        self.assertEqual(metrics["debt_maturity_schedule"][0]["maturity_date"], "2027-06-01")
        self.assertEqual(metrics["upcoming_capital_calls"][0]["amount"], Decimal("250000"))
        self.assertEqual(metrics["projected_irr_by_deal"][0]["value"], Decimal("0.14"))

    def test_ic_memo_includes_sources_scenarios_alerts_and_decisions(self) -> None:
        deal = Deal(
            DealIdentity(
                "Harbor Apartments",
                address="10 Harbor Way",
                asset_type="multifamily",
                sponsor="SponsorCo",
                broker="Metro Capital",
            )
        )
        deal.assets.append(
            Asset(
                "Harbor Apartments",
                address=Address("10 Harbor Way"),
                coordinates=Coordinates(32.1, 34.8),
                asset_type="multifamily",
                unit_count=120,
            )
        )
        fact = ExtractedFact(
            "current_noi",
            Decimal("1200000"),
            DocumentReference(SourceKind.DOCUMENT, "om.pdf", page=14),
            0.95,
        )
        deal.add_extracted_fact(fact)
        deal.review_fact(fact.id, FactReviewStatus.ACCEPTED, "analyst")
        deal.assumptions.append(Assumption("investment_thesis", "Transit-oriented multifamily with below-market rents", "IC draft"))
        deal.assumptions.append(Assumption("purchase_price", Decimal("18500000"), "Broker guidance"))
        deal.assumptions.append(Assumption("equity_required", Decimal("6500000"), "Sources and uses"))
        deal.assumptions.append(Assumption("rent_growth_sensitivity", "Downside at 1 percent", "Sensitivity case"))
        deal.assumptions.append(Assumption("recommendation", "Proceed to investment committee", "Base case clears hurdle"))
        deal.assumptions.append(Assumption("exit_cap_rate", Decimal("0.0575"), "Comparable sales"))
        deal.debt_terms.append(DebtTerms(lender="Bank", debt_amount=Decimal("12000000"), interest_rate=Decimal("0.06"), maturity_date="2030-01-01"))
        deal.market_comps.append(MarketComp("Nearby sale", "sale", Decimal("19000000"), distance_miles=0.5, source="broker"))
        deal.location_context.append(LocationContextItem(LocationContextType.TRANSIT, "Light rail stop", 0.2, "maps"))
        scenario = Scenario("Base Case", ScenarioType.ANALYST_BASE_CASE)
        scenario.set_output("irr", Decimal("0.14"))
        scenario.set_output("equity_multiple", Decimal("1.7"))
        deal.scenarios.append(scenario)
        deal.alerts.append(Alert("DSCR watch", AlertSeverity.HIGH, "debt", "model", "DSCR is near covenant"))
        deal.investment_decisions.append(InvestmentDecision("proceed", "principal", "Risk-adjusted return is acceptable."))
        deal.change_status(DealStatus.INVESTMENT_COMMITTEE, "analyst", "Ready for IC")

        memo = generate_ic_memo_markdown(deal)

        self.assertIn("# Investment Committee Memo: Harbor Apartments", memo)
        self.assertIn("## Investment Thesis", memo)
        self.assertIn("Transit-oriented multifamily", memo)
        self.assertIn("## Sources and Uses", memo)
        self.assertIn("purchase_price: 18500000", memo)
        self.assertIn("## Debt Terms", memo)
        self.assertIn("Bank: amount 12000000", memo)
        self.assertIn("## Projected Returns", memo)
        self.assertIn("Base Case: irr: 0.14, equity_multiple: 1.7", memo)
        self.assertIn("## Sensitivity Snapshot", memo)
        self.assertIn("rent_growth_sensitivity", memo)
        self.assertIn("## Comparable Deals", memo)
        self.assertIn("Nearby sale", memo)
        self.assertIn("## Map and Local Market Context", memo)
        self.assertIn("Light rail stop", memo)
        self.assertIn("## Recommendation", memo)
        self.assertIn("proceed: Risk-adjusted return is acceptable.", memo)
        self.assertIn("current_noi: 1200000 (om.pdf, page 14)", memo)
        self.assertIn("Base Case", memo)
        self.assertIn("DSCR watch", memo)
        self.assertIn("Human approval required", memo)
        self.assertIn('"identity"', export_deal_json(deal))

    def test_role_permissions(self) -> None:
        self.assertTrue(can(UserRole.ADMIN, "admin"))
        self.assertTrue(can(UserRole.ANALYST, "write"))
        self.assertFalse(can(UserRole.READ_ONLY_VIEWER, "write"))
        with self.assertRaises(PermissionError):
            require(UserRole.EXTERNAL_ADVISOR, "approve")

    def test_rejected_hindsight_and_actual_vs_underwritten(self) -> None:
        rejected = Deal(DealIdentity("Passed Deal"))
        rejected.assumptions.append(Assumption("proposed_price", Decimal("10000000"), "Broker whisper price"))
        rejected.market_comps.append(MarketComp("Later sale", "later_sale", Decimal("12000000")))
        rejected.reject("principal", "Too small")

        base = Scenario("Base", ScenarioType.ANALYST_BASE_CASE)
        base.outputs["noi"] = Decimal("1000000")
        actuals = Scenario("Actuals", ScenarioType.ACTUALS)
        actuals.outputs["noi"] = Decimal("900000")
        rejected.scenarios.extend([base, actuals])

        hindsight = rejected_deal_hindsight([rejected])
        learning = actual_vs_underwritten(rejected, "noi")

        self.assertEqual(hindsight[0]["missed_gain"], Decimal("2000000"))
        self.assertEqual(learning["variance"], Decimal("-100000"))
        self.assertEqual(learning["variance_percent"], Decimal("-0.1"))

    def test_cash_flow_variance_csv_export(self) -> None:
        rows = [
            {
                "period": "2027-01",
                "category": "noi",
                "projected": Decimal("100"),
                "actual": Decimal("90"),
                "variance": Decimal("-10"),
                "variance_percent": Decimal("-0.1"),
            }
        ]

        csv_text = export_cash_flow_variance_csv(rows)

        self.assertIn("period,category,projected,actual,variance,variance_percent", csv_text)
        self.assertIn("2027-01,noi,100,90,-10,-0.1", csv_text)

    def test_portfolio_monitoring_and_rejected_review_reports(self) -> None:
        active = Deal(DealIdentity("Active Deal", asset_type="retail"))
        active.assets.append(Asset("Active Deal", address=Address("1 Main", state="TX"), asset_type="retail"))
        active.projected_cash_flows.append(CashFlowRecord("2027-01", Decimal("100"), CashFlowType.PROJECTED, "noi"))
        active.actual_cash_flows.append(CashFlowRecord("2027-01", Decimal("90"), CashFlowType.ACTUAL, "noi"))
        active.debt_terms.append(DebtTerms(lender="Bank", maturity_date="2027-06-01", covenant_dscr=Decimal("1.20")))
        active.development_milestones.append(DevelopmentMilestone("Permit approval", "2027-03-01", MilestoneStatus.ON_TRACK))
        active.alerts.append(Alert("NOI below budget", AlertSeverity.HIGH, "cash_flow", "import", "NOI is low"))
        rejected = Deal(DealIdentity("Rejected Deal"))
        rejected.assumptions.append(Assumption("proposed_price", Decimal("100"), "Broker"))
        rejected.market_comps.append(MarketComp("Later sale", "later_sale", Decimal("120")))
        rejected.reject("principal", "Too small")

        portfolio = generate_portfolio_report_markdown([active, rejected])
        monitoring = generate_monitoring_report_markdown(active)
        rejected_review = generate_rejected_deal_review_markdown([active, rejected])

        self.assertIn("# Portfolio Report", portfolio)
        self.assertIn("- retail: 1", portfolio)
        self.assertIn("NOI below budget", monitoring)
        self.assertIn("Debt Covenant Watch", monitoring)
        self.assertIn("Rejected Deal", rejected_review)
        self.assertIn("missed gain 20", rejected_review)

    def test_monthly_development_and_lender_reports(self) -> None:
        deal = Deal(DealIdentity("Reporting Deal"))
        deal.projected_cash_flows.append(CashFlowRecord("2027-01", Decimal("100000"), CashFlowType.PROJECTED, "noi"))
        deal.actual_cash_flows.append(CashFlowRecord("2027-01", Decimal("88000"), CashFlowType.ACTUAL, "noi"))
        deal.development_budgets.append(
            DevelopmentBudget("Phase 1", land_cost=Decimal("100"), hard_costs=Decimal("200"), soft_costs=Decimal("50"), contingency=Decimal("25"))
        )
        deal.development_milestones.append(
            DevelopmentMilestone("Permit approval", "2027-03-01", MilestoneStatus.DELAYED)
        )
        deal.capex_items.append(CapexItem("Roof", Decimal("10000"), actual_amount=Decimal("12000")))
        deal.debt_terms.append(DebtTerms(lender="Bank", debt_amount=Decimal("7000000"), covenant_dscr=Decimal("1.20")))
        deal.assumptions.append(Assumption("current_noi", Decimal("1200000"), "Latest actuals"))
        deal.assumptions.append(Assumption("annual_debt_service", Decimal("900000"), "Loan schedule"))

        monthly = generate_monthly_performance_report_markdown(deal, period="2027-01")
        development = generate_development_progress_report_markdown(deal)
        lender = generate_lender_covenant_report_markdown(deal)

        self.assertIn("# Monthly Performance Report: Reporting Deal", monthly)
        self.assertIn("Variance: -12000", monthly)
        self.assertIn("# Development Progress Report: Reporting Deal", development)
        self.assertIn("Phase 1: total 375", development)
        self.assertIn("Roof: budget 10000, actual 12000, variance 2000", development)
        self.assertIn("# Lender Covenant Report: Reporting Deal", lender)
        self.assertIn("current DSCR 1.333333333333333333333333333", lender)

    def test_geospatial_portfolio_queries(self) -> None:
        deal = Deal(DealIdentity("Geo Deal"))
        near = Asset(
            "Near Asset",
            address=Address("1 Main", city="New York", state="NY"),
            coordinates=Coordinates(40.7128, -74.0060),
        )
        far = Asset(
            "Far Asset",
            address=Address("2 Market", city="San Francisco", state="CA"),
            coordinates=Coordinates(37.7749, -122.4194),
        )
        deal.assets.extend([near, far])

        matches = assets_within_radius([deal], Coordinates(40.7130, -74.0062), 1)

        self.assertLess(distance_km(near.coordinates, Coordinates(40.7130, -74.0062)), 1)
        self.assertEqual(matches[0][1].name, "Near Asset")
        self.assertEqual(exposure_by_geography([deal]), {"NY": 1, "CA": 1})

    def test_debt_maturity_and_dscr_alerts(self) -> None:
        deal = Deal(DealIdentity("Debt Deal"))
        deal.debt_terms.append(
            DebtTerms(lender="Bank", maturity_date="2027-06-01", covenant_dscr=Decimal("1.20"))
        )

        maturity_alerts = debt_maturity_alerts(deal, today=date(2027, 1, 1), window_days=180)
        covenant_alerts = dscr_covenant_alerts(
            deal,
            annual_debt_service_by_lender={"Bank": Decimal("1000000")},
            noi_by_lender={"Bank": Decimal("1100000")},
        )

        self.assertEqual(maturity_alerts[0].category, "debt")
        self.assertEqual(covenant_alerts[0].severity, AlertSeverity.CRITICAL)

    def test_obligation_alerts_cover_deadlines_expirations_and_capital_calls(self) -> None:
        deal = Deal(DealIdentity("Obligation Deal"))
        deal.obligations.extend(
            [
                Obligation("File zoning appeal", "2027-01-10", ObligationType.LEGAL_DEADLINE, owner="counsel"),
                Obligation("Insurance certificate", "2026-12-20", ObligationType.DOCUMENT_EXPIRATION),
                Obligation("Fund draw 3", "2027-02-01", ObligationType.CAPITAL_CALL, amount=Decimal("250000")),
            ]
        )

        alerts = obligation_alerts(deal, today=date(2027, 1, 1), window_days=45)

        self.assertEqual([alert.category for alert in alerts], ["legal_deadline", "document_expiration", "capital_call"])
        self.assertEqual(alerts[1].severity, AlertSeverity.CRITICAL)
        self.assertEqual(alerts[2].financial_impact, Decimal("250000"))

    def test_insurance_and_contingency_alerts(self) -> None:
        deal = Deal(DealIdentity("Cost Risk Deal"))
        deal.assumptions.append(Assumption("insurance_budget", Decimal("100000"), "Budget"))
        deal.assumptions.append(Assumption("insurance_premium", Decimal("125000"), "Renewal quote"))
        deal.development_budgets.append(DevelopmentBudget("Phase 1", contingency=Decimal("100000")))
        deal.capex_items.append(CapexItem("Site work", Decimal("500000"), actual_amount=Decimal("575000")))

        insurance_alerts = insurance_cost_alerts(deal)
        contingency_alerts = contingency_consumption_alerts(deal)

        self.assertEqual(insurance_alerts[0].category, "insurance")
        self.assertEqual(insurance_alerts[0].financial_impact, Decimal("25000"))
        self.assertEqual(contingency_alerts[0].category, "development_budget")
        self.assertEqual(contingency_alerts[0].financial_impact, Decimal("75000"))

    def test_market_news_permit_and_property_feed_alerts(self) -> None:
        deal = Deal(DealIdentity("Feed Deal"))
        deal.assumptions.append(Assumption("assessed_value", Decimal("10000000"), "Tax underwriting"))
        deal.assumptions.append(Assumption("exit_value", Decimal("20000000"), "Base case"))
        deal.property_records.append(PropertyRecord("assessor", assessed_value=Decimal("11500000")))
        deal.market_comps.append(MarketComp("Distressed sale", "sale", Decimal("17000000"), source="broker"))
        deal.permit_events.append(PermitEvent("P-1", "building", "denied", description="Board denial"))
        deal.news_events.append(
            NewsEvent(
                "Planning board opposition",
                "https://example.test/news",
                NewsClassification.MATERIAL_NEGATIVE,
                summary="Neighbors oppose rezoning.",
            )
        )

        self.assertEqual(local_news_alerts(deal)[0].category, "local_news")
        self.assertEqual(permit_risk_alerts(deal)[0].category, "permit")
        self.assertEqual(property_assessment_alerts(deal)[0].financial_impact, Decimal("1500000"))
        self.assertEqual(comparable_sale_alerts(deal)[0].financial_impact, Decimal("-3000000"))
        self.assertEqual(len(monitoring_alerts(deal)), 4)

    def test_sponsor_tenant_and_competing_development_alerts(self) -> None:
        deal = Deal(DealIdentity("Specific Risk Deal", sponsor="SponsorCo"))
        deal.tenants.append(Tenant("Anchor Retailer", credit_notes="Bankruptcy watchlist after missed supplier payments."))
        deal.news_events.append(
            NewsEvent(
                "SponsorCo faces lawsuit over prior project",
                "https://example.test/sponsor",
                NewsClassification.WATCH,
                summary="SponsorCo is named in court litigation related to a prior development.",
            )
        )
        deal.location_context.append(
            LocationContextItem(
                LocationContextType.COMPETING_PROPERTY,
                "New mixed-use tower",
                distance_miles=0.7,
                source="planning portal",
                notes="Competing rental supply under construction.",
            )
        )

        sponsor_alerts = sponsor_litigation_alerts(deal)
        tenant_alerts = tenant_credit_alerts(deal)
        supply_alerts = competing_development_alerts(deal)

        self.assertEqual(sponsor_alerts[0].category, "sponsor_risk")
        self.assertEqual(tenant_alerts[0].category, "tenant_credit")
        self.assertEqual(supply_alerts[0].category, "market_supply")
        self.assertGreaterEqual(len(monitoring_alerts(deal)), 3)

    def test_income_asset_lease_and_tenant_analytics(self) -> None:
        deal = Deal(DealIdentity("Retail Center"))
        deal.assets.append(Asset("Retail Center", unit_count=4))
        anchor = Tenant("Anchor Grocer")
        shop = Tenant("Coffee Shop")
        deal.tenants.extend([anchor, shop])
        deal.leases.append(Lease(anchor.id, unit="A", end_date="2029-01-01", annual_rent=Decimal("300000")))
        deal.leases.append(Lease(shop.id, unit="B", end_date="2027-01-01", annual_rent=Decimal("100000")))

        concentration = tenant_concentration(deal)

        self.assertEqual(occupancy_rate(deal), Decimal("0.5"))
        self.assertEqual(lease_expiry_schedule(deal), {"2027": 1, "2029": 1})
        self.assertEqual(concentration[0]["tenant_name"], "Anchor Grocer")
        self.assertEqual(concentration[0]["percent_of_rent"], Decimal("0.75"))
        self.assertEqual(
            weighted_average_lease_term(deal, as_of=date(2026, 1, 1)).quantize(Decimal("0.01")),
            Decimal("2.50"),
        )

    def test_rent_roll_operating_metrics(self) -> None:
        deal = Deal(DealIdentity("Rent Roll Deal"))
        deal.rent_roll.extend(
            [
                RentRollEntry(
                    "2027-01-31",
                    "101",
                    tenant_name="Tenant A",
                    monthly_rent=Decimal("2000"),
                    market_rent=Decimal("2200"),
                    concessions=Decimal("100"),
                ),
                RentRollEntry(
                    "2027-01-31",
                    "102",
                    monthly_rent=Decimal("0"),
                    market_rent=Decimal("2100"),
                    occupied=False,
                    bad_debt=Decimal("50"),
                ),
            ]
        )

        gap = market_rent_gap(deal, as_of_date="2027-01-31")

        self.assertEqual(rent_roll_occupancy_rate(deal, as_of_date="2027-01-31"), Decimal("0.5"))
        self.assertEqual(occupancy_rate(deal), Decimal("0.5"))
        self.assertEqual(vacancy_rate(deal, as_of_date="2027-01-31"), Decimal("0.5"))
        self.assertEqual(gap["gap"], Decimal("2300"))
        self.assertEqual(concessions_total(deal), Decimal("100"))
        self.assertEqual(bad_debt_total(deal), Decimal("50"))

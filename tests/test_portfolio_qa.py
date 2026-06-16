from decimal import Decimal
from unittest import TestCase

from real_estate_helm import (
    Alert,
    AlertSeverity,
    Assumption,
    Deal,
    DealIdentity,
    DealStatus,
    MarketComp,
    Scenario,
    ScenarioType,
)
from real_estate_helm.portfolio_qa import PortfolioQuestionAnswerer


class PortfolioQuestionAnswererTests(TestCase):
    def test_answers_open_alert_questions_from_structured_alerts(self) -> None:
        deal = Deal(DealIdentity("Alert Deal"))
        deal.alerts.append(Alert("DSCR below covenant", AlertSeverity.CRITICAL, "debt", "model", "DSCR is low"))

        answer = PortfolioQuestionAnswerer().answer([deal], "What are the urgent open alerts?")

        self.assertEqual(answer.answer_type, "open_alerts")
        self.assertEqual(answer.rows[0]["deal_name"], "Alert Deal")
        self.assertEqual(answer.rows[0]["severity"], "critical")

    def test_answers_rejected_deal_questions_with_positive_missed_gain(self) -> None:
        rejected = Deal(DealIdentity("Passed Deal"))
        rejected.assumptions.append(Assumption("proposed_price", Decimal("100"), "Broker whisper"))
        rejected.market_comps.append(MarketComp("Later sale", "later_sale", Decimal("130")))
        rejected.reject("principal", "Too small")

        answer = PortfolioQuestionAnswerer().answer([rejected], "Which rejected deals should we reopen?")

        self.assertEqual(answer.answer_type, "rejected_deal_hindsight")
        self.assertEqual(answer.to_dict()["rows"][0]["missed_gain"], "30")

    def test_answers_exposure_status_and_actual_vs_underwritten_questions(self) -> None:
        deal = Deal(DealIdentity("Sponsor Deal", asset_type="retail", sponsor="SponsorCo"))
        deal.change_status(DealStatus.WATCHLIST, "analyst", "Track")
        base = Scenario("Base", ScenarioType.ANALYST_BASE_CASE)
        base.outputs["noi"] = Decimal("100")
        actuals = Scenario("Actuals", ScenarioType.ACTUALS)
        actuals.outputs["noi"] = Decimal("90")
        deal.scenarios.extend([base, actuals])
        answerer = PortfolioQuestionAnswerer()

        self.assertEqual(answerer.answer([deal], "Exposure by sponsor").rows, [{"name": "SponsorCo", "count": 1}])
        self.assertEqual(answerer.answer([deal], "Pipeline status").rows, [{"name": "watchlist", "count": 1}])
        variance = answerer.answer([deal], "Actual vs underwritten NOI").to_dict()["rows"][0]
        self.assertEqual(variance["variance"], "-10")
        learning = answerer.answer([deal], "What did the forecast learning loop show?").to_dict()
        self.assertEqual(learning["answer_type"], "forecast_vs_actual_learning")
        self.assertEqual(learning["rows"][0]["direction"], "underwritten_aggressive")

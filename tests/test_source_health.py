from unittest import TestCase

from real_estate_helm import Deal, DealIdentity
from real_estate_helm.monitoring import source_health_alerts


class SourceHealthTests(TestCase):
    def test_source_health_alerts_only_for_unhealthy_sources(self) -> None:
        alerts = source_health_alerts(Deal(DealIdentity("Source Deal")), {"news": False, "maps": True})

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].category, "source_health")
        self.assertIn("news", alerts[0].title)

from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import DealStatus
from real_estate_helm.crm_import import CrmImportService
from real_estate_helm.repository import JsonDealRepository


class CrmImportServiceTests(TestCase):
    def test_import_csv_creates_deals_from_pipeline_rows(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)

            result = CrmImportService(repository).import_csv(
                "\n".join(
                    [
                        "deal_name,property_address,asset_class,sponsor,broker,owner,stage",
                        "Harbor CRM Deal,10 Harbor Way,multifamily,SponsorCo,BrokerCo,analyst,underwriting",
                        ",Missing Name,office,SponsorCo,BrokerCo,analyst,screening",
                    ]
                ),
                default_owner="fallback",
            )

            deal = repository.get(result.deal_ids[0])
            self.assertEqual(result.imported_rows, 1)
            self.assertEqual(len(result.skipped_rows), 1)
            self.assertEqual(deal.identity.name, "Harbor CRM Deal")
            self.assertEqual(deal.identity.address, "10 Harbor Way")
            self.assertEqual(deal.identity.asset_type, "multifamily")
            self.assertEqual(deal.identity.source, "crm_export")
            self.assertEqual(deal.status, DealStatus.UNDERWRITING)

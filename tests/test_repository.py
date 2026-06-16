from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm import Assumption, Deal, DealIdentity, DealStatus
from real_estate_helm.repository import JsonDealRepository
from real_estate_helm.underwriting import cap_rate


class JsonDealRepositoryTests(TestCase):
    def test_save_get_list_and_filter_deals(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            acquired = Deal(
                DealIdentity(
                    name="Oak Retail Center",
                    address="100 Oak Street",
                    asset_type="retail",
                    sponsor="North Star",
                )
            )
            acquired.change_status(DealStatus.ACQUIRED, "principal", "Closed")
            rejected = Deal(
                DealIdentity(
                    name="Maple Multifamily",
                    address="200 Maple Avenue",
                    asset_type="multifamily",
                    broker="Urban Brokers",
                )
            )
            rejected.reject("principal", "Cap rate too thin")

            repository.save(acquired)
            repository.save(rejected)

            restored = repository.get(acquired.id)
            self.assertEqual(restored.identity.name, "Oak Retail Center")
            self.assertEqual(restored.status, DealStatus.ACQUIRED)
            self.assertEqual(len(repository.list()), 2)
            self.assertEqual([deal.id for deal in repository.list(status=DealStatus.REJECTED)], [rejected.id])
            self.assertEqual([deal.id for deal in repository.search("urban")], [rejected.id])

    def test_repository_preserves_decimal_outputs(self) -> None:
        with TemporaryDirectory() as directory:
            repository = JsonDealRepository(directory)
            deal = Deal(DealIdentity(name="Cedar Office"))
            deal.assumptions.append(
                Assumption("going_in_cap_rate", cap_rate(750000, 12500000), "NOI / price")
            )

            repository.save(deal)
            restored = repository.get(deal.id)

            self.assertEqual(restored.assumptions[0].value, Decimal("0.06"))

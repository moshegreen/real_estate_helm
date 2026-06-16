from tempfile import TemporaryDirectory
from unittest import TestCase

from real_estate_helm.fastapi_app import create_app
from real_estate_helm.repository import JsonDealRepository


class FakeFastAPI:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.routes = []

    def get(self, path):
        def decorator(func):
            self.routes.append(("GET", path, func))
            return func

        return decorator

    def post(self, path, status_code=200):
        def decorator(func):
            self.routes.append(("POST", path, func, status_code))
            return func

        return decorator


class FastApiAppFactoryTests(TestCase):
    def test_create_app_registers_core_routes_with_factory(self) -> None:
        with TemporaryDirectory() as directory:
            app = create_app(JsonDealRepository(directory), fastapi_factory=FakeFastAPI)

            registered = {(route[0], route[1]) for route in app.routes}

            self.assertEqual(app.kwargs["title"], "Real Estate Helm")
            self.assertIn(("GET", "/health"), registered)
            self.assertIn(("GET", "/deals"), registered)
            self.assertIn(("POST", "/deals"), registered)
            self.assertIn(("GET", "/portfolio/summary"), registered)

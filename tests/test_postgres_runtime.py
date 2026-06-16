from pathlib import Path
from unittest import TestCase

from real_estate_helm import Deal, DealIdentity
from real_estate_helm.postgres import PostgresDealRepository, PostgresMigrationRunner


class FakeCursor:
    def __init__(self) -> None:
        self.executed = []

    def execute(self, sql, params=None) -> None:
        self.executed.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self) -> None:
        self.commits += 1


class PostgresRuntimeTests(TestCase):
    def test_migration_runner_executes_schema_and_commits(self) -> None:
        connection = FakeConnection()
        schema_path = Path(__file__).resolve().parents[1] / "schema" / "postgres.sql"

        PostgresMigrationRunner(connection).apply_schema(schema_path)

        self.assertIn("CREATE TABLE deals", connection.cursor_instance.executed[0][0])
        self.assertEqual(connection.commits, 1)

    def test_repository_executes_mapper_statements_and_commits(self) -> None:
        connection = FakeConnection()
        deal = Deal(DealIdentity("Runtime SQL Deal"))

        count = PostgresDealRepository(connection).save(deal)

        self.assertEqual(count, 1)
        self.assertIn("INSERT INTO deals", connection.cursor_instance.executed[0][0])
        self.assertEqual(connection.commits, 1)

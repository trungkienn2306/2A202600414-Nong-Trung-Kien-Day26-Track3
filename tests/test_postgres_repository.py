from __future__ import annotations

import os

import psycopg
import pytest

from src.init_postgres import create_postgres_database
from src.repository import PostgresRepository
from src.validation import ValidationError

pytestmark = pytest.mark.postgres


@pytest.fixture()
def postgres_repository():
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        pytest.skip("POSTGRES_DSN is not set")
    try:
        create_postgres_database(dsn, allow_destructive_reset=True)
    except psycopg.Error as error:
        pytest.skip(f"PostgreSQL is not reachable: {error}")
    return PostgresRepository(dsn)


def test_postgres_schema_matches_lab_tables(postgres_repository):
    schema = postgres_repository.full_schema()

    assert set(schema) == {"courses", "enrollments", "students"}
    assert postgres_repository.table_schema("students")[0]["name"] == "id"


def test_postgres_search_filters_orders_and_paginates(postgres_repository):
    result = postgres_repository.search(
        "students",
        filters={"cohort": "A1"},
        columns=["name", "score"],
        limit=1,
        order_by="score",
        descending=True,
    )

    assert result["rows"] == [{"name": "Binh Tran", "score": 91.0}]


def test_postgres_insert_returns_inserted_payload(postgres_repository):
    result = postgres_repository.insert(
        "students",
        {
            "name": "Postgres Student",
            "cohort": "PG",
            "age": 24,
            "email": "postgres.student@example.com",
            "score": 94.0,
        },
    )

    assert result["inserted"]["id"] > 0
    assert result["inserted"]["name"] == "Postgres Student"


def test_postgres_aggregate_groups_results(postgres_repository):
    postgres_repository.insert(
        "students",
        {
            "name": "Postgres Student",
            "cohort": "PG",
            "age": 24,
            "email": "postgres.student@example.com",
            "score": 94.0,
        },
    )

    result = postgres_repository.aggregate("students", "avg", "score", group_by="cohort")
    rows_by_cohort = {row["cohort"]: row["value"] for row in result["rows"]}

    assert rows_by_cohort["A1"] == pytest.approx(89.75)
    assert rows_by_cohort["PG"] == pytest.approx(94.0)


def test_postgres_rejects_invalid_requests(postgres_repository):
    with pytest.raises(ValidationError, match="Unknown table"):
        postgres_repository.search("missing")
    with pytest.raises(ValidationError, match="Unsupported aggregate"):
        postgres_repository.aggregate("students", "median", "score")
    with pytest.raises(ValidationError, match="requires a numeric column"):
        postgres_repository.aggregate("students", "avg", "name")

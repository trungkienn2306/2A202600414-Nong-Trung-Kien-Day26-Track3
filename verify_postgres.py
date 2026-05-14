from __future__ import annotations

import os

from src.init_postgres import create_postgres_database
from src.repository import PostgresRepository


def main() -> None:
    dsn = os.environ["POSTGRES_DSN"]
    create_postgres_database(dsn, allow_destructive_reset=True)
    repository = PostgresRepository(dsn)

    print("POSTGRES_TABLES:", repository.list_tables())
    print("POSTGRES_SCHEMA_TABLES:", sorted(repository.full_schema()))
    print(
        "POSTGRES_SEARCH_OK:",
        repository.search(
            "students",
            filters={"cohort": "A1"},
            columns=["name", "score"],
            limit=2,
            order_by="score",
            descending=True,
        ),
    )
    print(
        "POSTGRES_INSERT_OK:",
        repository.insert(
            "students",
            {
                "name": "Postgres Verify Student",
                "cohort": "PG",
                "age": 24,
                "email": "postgres.verify@example.com",
                "score": 94.0,
            },
        ),
    )
    print(
        "POSTGRES_AGGREGATE_OK:",
        repository.aggregate("students", "avg", "score", group_by="cohort"),
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import pytest

from src.validation import ValidationError


def test_search_filters_orders_and_paginates(repository):
    result = repository.search(
        "students",
        filters={"cohort": "A1"},
        columns=["name", "score"],
        limit=1,
        offset=0,
        order_by="score",
        descending=True,
    )

    assert result["count"] == 1
    assert result["rows"] == [{"name": "Binh Tran", "score": 91.0}]


def test_search_supports_like_and_in_filters(repository):
    result = repository.search(
        "students",
        filters=[
            {"column": "name", "operator": "like", "value": "%n%"},
            {"column": "cohort", "operator": "in", "value": ["A1", "B2"]},
        ],
        columns=["name", "cohort"],
        order_by="name",
    )

    assert result["count"] == 3
    assert {row["cohort"] for row in result["rows"]} == {"A1", "B2"}


def test_insert_returns_inserted_payload(repository):
    result = repository.insert(
        "students",
        {
            "name": "Kien Nong",
            "cohort": "D4",
            "age": 23,
            "email": "kien@example.com",
            "score": 99.0,
        },
    )

    assert result["inserted"]["id"] > 0
    assert result["inserted"]["name"] == "Kien Nong"
    assert repository.search("students", filters={"email": "kien@example.com"})["count"] == 1


@pytest.mark.parametrize(
    ("metric", "column", "expected"),
    [
        ("count", None, 5),
        ("avg", "score", 87.25),
        ("sum", "score", 436.25),
        ("min", "score", 77.0),
        ("max", "score", 95.5),
    ],
)
def test_aggregate_metrics(repository, metric, column, expected):
    result = repository.aggregate("students", metric, column)

    assert result["rows"] == [{"value": expected}]


def test_aggregate_groups_results(repository):
    result = repository.aggregate("students", "avg", "score", group_by="cohort")

    assert result["rows"] == [
        {"cohort": "A1", "value": 89.75},
        {"cohort": "B2", "value": 80.625},
        {"cohort": "C3", "value": 95.5},
    ]


def test_invalid_table_column_operator_and_aggregate_are_rejected(repository):
    with pytest.raises(ValidationError, match="Unknown table"):
        repository.search("missing")
    with pytest.raises(ValidationError, match="Unknown filter column"):
        repository.search("students", filters={"missing": "x"})
    with pytest.raises(ValidationError, match="Unsupported operator"):
        repository.search("students", filters={"score": {"operator": "between", "value": [1, 2]}})
    with pytest.raises(ValidationError, match="Unsupported aggregate"):
        repository.aggregate("students", "median", "score")


def test_bad_insert_and_bad_aggregate_are_rejected(repository):
    with pytest.raises(ValidationError, match="values must not be empty"):
        repository.insert("students", {})
    with pytest.raises(ValidationError, match="requires a numeric column"):
        repository.aggregate("students", "avg", "name")

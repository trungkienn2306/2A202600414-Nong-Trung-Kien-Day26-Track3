from __future__ import annotations

from typing import Any, NoReturn, Protocol


class DatabaseRepository(Protocol):
    def full_schema(self) -> dict[str, list[dict[str, Any]]]: ...

    def table_schema(self, table: str) -> list[dict[str, Any]]: ...

    def search(
        self,
        table: str,
        filters: Any = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]: ...

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]: ...

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: Any = None,
        group_by: str | list[str] | None = None,
    ) -> dict[str, Any]: ...


class PostgresRepository:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _unsupported(self) -> NoReturn:
        raise NotImplementedError(
            "PostgreSQL uses the same DatabaseRepository interface; install a PostgreSQL adapter to enable it."
        )

    def full_schema(self) -> dict[str, list[dict[str, Any]]]:
        self._unsupported()

    def table_schema(self, table: str) -> list[dict[str, Any]]:
        self._unsupported()

    def search(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._unsupported()

    def insert(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._unsupported()

    def aggregate(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._unsupported()

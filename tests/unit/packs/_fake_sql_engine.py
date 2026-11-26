"""Lightweight fake SQLAlchemy AsyncEngine/Result helpers for Story 31.4 branch coverage."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any


class FakeSqlResult:
    """Minimal mimic of SQLAlchemy `Result` supporting scalar, tuple & mapping methods."""

    def __init__(
        self,
        *,
        rows: list[Any] | None = None,
        mappings: list[dict[str, Any]] | None = None,
        scalar_val: Any = None,
        has_scalar: bool = False,
    ) -> None:
        self._rows = rows or []
        self._mappings = mappings or []
        self._scalar = scalar_val
        self._has_scalar = has_scalar

    def mappings(self) -> FakeSqlResult:
        return self

    def __iter__(self) -> Iterator[Any]:
        return iter(self.all())

    def all(self) -> list[Any]:
        return list(self._mappings if self._mappings else self._rows)

    def fetchall(self) -> list[Any]:
        return list(self._rows)

    def first(self) -> Any:
        items = self._mappings if self._mappings else self._rows
        return items[0] if items else None

    def one(self) -> Any:
        items = self._mappings if self._mappings else self._rows
        return items[0]

    def scalar(self) -> Any:
        if self._has_scalar or self._scalar is not None:
            return self._scalar
        return self._rows[0][0] if self._rows else None

    def scalar_one(self) -> Any:
        return self._scalar if (self._has_scalar or self._scalar is not None) else self._rows[0][0]

    def scalar_one_or_none(self) -> Any:
        return self.scalar()

    def scalars(self) -> list[Any]:
        return [r[0] if isinstance(r, tuple) else r for r in self._rows]


class _FakeConn:
    def __init__(
        self,
        handler: Callable[[str, dict[str, Any]], FakeSqlResult],
        *,
        commit_exc: Exception | None = None,
    ) -> None:
        self._handler = handler
        self._commit_exc = commit_exc

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> FakeSqlResult:
        return self._handler(str(stmt), params or {})


class _FakeCtx:
    def __init__(self, conn: _FakeConn, *, raise_on_exit: Exception | None = None) -> None:
        self._conn = conn
        self._raise_on_exit = raise_on_exit

    async def __aenter__(self) -> _FakeConn:
        return self._conn

    async def __aexit__(self, exc_type: Any, _exc: Any, _tb: Any) -> None:
        if exc_type is None and self._raise_on_exit is not None:
            raise self._raise_on_exit


class FakeSqlEngine:
    """Fake `AsyncEngine` dispatching queries to a test handler."""

    def __init__(
        self,
        handler: Callable[[str, dict[str, Any]], FakeSqlResult],
        *,
        commit_exc: Exception | None = None,
    ) -> None:
        self._handler = handler
        self._commit_exc = commit_exc

    def connect(self) -> _FakeCtx:
        return _FakeCtx(_FakeConn(self._handler))

    def begin(self) -> _FakeCtx:
        return _FakeCtx(_FakeConn(self._handler), raise_on_exit=self._commit_exc)


__all__ = ["FakeSqlEngine", "FakeSqlResult"]

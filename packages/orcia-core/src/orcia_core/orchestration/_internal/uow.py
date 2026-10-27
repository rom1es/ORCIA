"""SQLAlchemy 2.1 Asyncio Unit of Work backed by DBOS `AsyncSQLAlchemyDatasource` (`ARCH-P1`)."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, Literal, TypeVar

from dbos import AsyncSQLAlchemyDatasource
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

R = TypeVar("R")
IsolationLevel = Literal["SERIALIZABLE", "REPEATABLE READ", "READ COMMITTED"]


class DbosSqlAlchemyUnitOfWork:
    """SQLAlchemy 2.1 Asyncio Unit of Work backed by DBOS `AsyncSQLAlchemyDatasource`.

    Provides a unified session management pattern (`ARCH-P1`, `C2`) that works transparently:
    - **Inside a `@DBOS.workflow()`**: executes the callback in `async with session.begin():`,
      flushes domain rows, and commits the step checkpoint into `<schema>.datasource_outputs`
      in the exact same PostgreSQL ACID transaction.
    - **Outside a workflow (FastAPI HTTP request)**: executes the callback in
      `async with session.begin():` without workflow checkpoint overhead.

    Note discovered during Story 3.2s (`ARCH-P2-SPIKE`):
    `PostgresAsyncDatasource._create_engine` rewrites `database_url` to `postgresql+psycopg`
    when `engine=None`. Passing an explicit `AsyncEngine` created via
    `create_async_engine("postgresql+asyncpg://...")` preserves the `asyncpg` driver.
    """

    def __init__(self, datasource: AsyncSQLAlchemyDatasource) -> None:
        self._datasource = datasource

    @classmethod
    async def create(
        cls,
        async_database_url: str,
        *,
        engine: AsyncEngine | None = None,
        engine_kwargs: dict[str, Any] | None = None,
        schema: str = "dbos",
        run_migrations: bool = True,
    ) -> DbosSqlAlchemyUnitOfWork:
        resolved_engine = (
            engine
            if engine is not None
            else create_async_engine(async_database_url, **(engine_kwargs or {}))
        )
        datasource = await AsyncSQLAlchemyDatasource.create(
            database_url=async_database_url,
            engine=resolved_engine,
            schema=schema,
            run_migrations=run_migrations,
        )
        return cls(datasource)

    @property
    def datasource(self) -> AsyncSQLAlchemyDatasource:
        return self._datasource

    @property
    def engine(self) -> AsyncEngine:
        return self._datasource.engine

    @property
    def session(self) -> AsyncSession:
        """Return the active `AsyncSession` bound to the current transaction."""
        return self._datasource.sql_session()

    async def run_transaction(
        self,
        func: Callable[..., Coroutine[Any, Any, R]],
        *args: Any,
        name: str | None = None,
        isolation_level: IsolationLevel = "READ COMMITTED",
        **kwargs: Any,
    ) -> R:
        """Execute an async repository callback inside an atomic SQLAlchemy + DBOS transaction."""
        options: dict[str, Any] = {"isolation_level": isolation_level}
        if name is not None:
            options["name"] = name
        return await self._datasource.run_tx_step_async(
            options,  # type: ignore[arg-type]
            func,
            *args,
            **kwargs,
        )

    async def close(self) -> None:
        await self._datasource.engine.dispose()

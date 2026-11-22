"""PG18 relational loaders for ontology relations, axioms & governance snapshot (`Story 26.5`)."""

from __future__ import annotations

import asyncio
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.ontology._internal.sql_ontology_mappers import (
    row_to_axiom,
    row_to_concept,
    row_to_relation,
)
from orcia_core.ontology._internal.sql_ontology_queries import (
    SQL_LIST_ACTIVE_CONCEPTS,
    SQL_LIST_AXIOMS,
    SQL_LIST_RELATIONS,
)
from orcia_core.ontology.impact_and_promotion import OntologyGovernanceService
from orcia_core.ontology.models import OntologyAxiomEntity, OntologyRelationEntity

_READY_ONTOLOGY_ENGINES: set[int] = set()


async def _ensure_ontology_tables_ready(engine: AsyncEngine) -> tuple[bool, bool, bool]:
    if id(engine) in _READY_ONTOLOGY_ENGINES:
        return True, True, True
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                sa.text(
                    "SELECT to_regclass('public.ontology_concepts'), "
                    "to_regclass('public.ontology_relations'), "
                    "to_regclass('public.ontology_axioms')"
                )
            )
        ).one()
    c_ok, r_ok, a_ok = row[0] is not None, row[1] is not None, row[2] is not None
    if c_ok and r_ok and a_ok:
        _READY_ONTOLOGY_ENGINES.add(id(engine))
    return c_ok, r_ok, a_ok


async def _query_rows(engine: AsyncEngine, stmt: Any) -> list[Any]:
    async with engine.connect() as conn:
        return list(await conn.execute(stmt))


async def list_relations_pg(engine: AsyncEngine) -> list[OntologyRelationEntity]:
    """Return all ontology relations persisted in PostgreSQL 18."""
    _, r_ok, _ = await _ensure_ontology_tables_ready(engine)
    if not r_ok:
        return []
    rows = await _query_rows(engine, SQL_LIST_RELATIONS)
    return [row_to_relation(r) for r in rows]


async def list_axioms_pg(engine: AsyncEngine) -> list[OntologyAxiomEntity]:
    """Return all ontology axioms persisted in PostgreSQL 18."""
    _, _, a_ok = await _ensure_ontology_tables_ready(engine)
    if not a_ok:
        return []
    rows = await _query_rows(engine, SQL_LIST_AXIOMS)
    return [row_to_axiom(r) for r in rows]


async def load_ontology_governance_service_pg(engine: AsyncEngine) -> OntologyGovernanceService:
    """Hydrate `OntologyGovernanceService` from PG18 tables in 1 concurrent roundtrip."""
    c_ok, r_ok, a_ok = await _ensure_ontology_tables_ready(engine)
    if not c_ok:
        return OntologyGovernanceService()
    c_rows, r_rows, a_rows = await asyncio.gather(
        _query_rows(engine, SQL_LIST_ACTIVE_CONCEPTS),
        _query_rows(engine, SQL_LIST_RELATIONS) if r_ok else asyncio.sleep(0, result=[]),
        _query_rows(engine, SQL_LIST_AXIOMS) if a_ok else asyncio.sleep(0, result=[]),
    )
    concepts = tuple(row_to_concept(r) for r in c_rows)
    if not concepts:
        return OntologyGovernanceService()
    relations = tuple(row_to_relation(r) for r in r_rows)
    axioms = tuple(row_to_axiom(r) for r in a_rows)
    return OntologyGovernanceService(concepts=concepts, relations=relations, axioms=axioms)


__all__ = [
    "list_axioms_pg",
    "list_relations_pg",
    "load_ontology_governance_service_pg",
]

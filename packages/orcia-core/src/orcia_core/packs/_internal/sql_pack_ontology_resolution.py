"""Flat Priority-Ordered Workspace Pack Ontology, DNA & Instructions (`R4`, `Story 31.3`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.ontology import (
    OntologyHierarchyResolver,
    ResolvedOntologySnapshot,
    list_axioms_pg,
    list_concepts_pg,
    list_relations_pg,
)
from orcia_core.packs._internal._sql_pack_flat_loaders import (
    load_flat_broker_policies,
    load_flat_dna_mechanisms,
    load_flat_pack_instructions,
)


@dataclass(frozen=True, slots=True)
class WorkspacePackEffectiveResolution:
    """Flat workspace resolution across ontology, DNA mechanisms, policies & instructions."""

    workspace_id: str
    active_pack_priorities: dict[str, int]
    active_pack_slugs: tuple[str, ...]
    ontology_snapshot: ResolvedOntologySnapshot
    dna_mechanisms: tuple[dict[str, Any], ...]
    broker_policies: tuple[dict[str, Any], ...]
    instructions: tuple[dict[str, Any], ...]


async def _fetch_workspace_pack_context(
    conn: AsyncConnection,
    workspace_id: str,
) -> tuple[str, dict[str, int], dict[str, int], tuple[str, ...]]:
    clean_ws = workspace_id.strip()
    ws_row = (
        await conn.execute(
            sa.text(
                "SELECT id::text FROM workspaces "
                "WHERE id::text = :ws OR LOWER(slug) = LOWER(:ws) LIMIT 1"
            ),
            {"ws": clean_ws},
        )
    ).first()
    resolved_ws = str(ws_row[0]) if ws_row and ws_row[0] else clean_ws

    reg = (
        await conn.execute(sa.text("SELECT to_regclass('public.workspace_pack_activations')"))
    ).scalar()
    priorities_by_slug: dict[str, int] = {}
    priorities_by_bundle: dict[str, int] = {}
    active_slugs: list[str] = []
    if reg is not None:
        rows = (
            await conn.execute(
                sa.text(
                    "SELECT wpa.pack_bundle_id::text, dpb.slug, wpa.priority_order "
                    "FROM workspace_pack_activations wpa "
                    "JOIN declarative_pack_bundles dpb ON dpb.id = wpa.pack_bundle_id "
                    "LEFT JOIN workspaces w ON w.id = wpa.workspace_id "
                    "WHERE wpa.is_active = TRUE "
                    "  AND (wpa.workspace_id::text = :ws OR LOWER(w.slug) = LOWER(:ws) "
                    "       OR wpa.workspace_id::text = :rws) "
                    "ORDER BY wpa.priority_order ASC NULLS LAST, dpb.slug ASC"
                ),
                {"ws": clean_ws, "rws": resolved_ws},
            )
        ).fetchall()
        for idx, row in enumerate(rows, start=1):
            bid = str(row[0])
            pslug = str(row[1]).strip().lower()
            prio = int(row[2]) if row[2] is not None else idx
            priorities_by_slug[pslug] = prio
            priorities_by_bundle[bid] = prio
            active_slugs.append(pslug)
    return resolved_ws, priorities_by_slug, priorities_by_bundle, tuple(active_slugs)


async def load_workspace_active_pack_priorities_pg(
    engine: AsyncEngine,
    workspace_id: str,
) -> tuple[dict[str, int], tuple[str, ...]]:
    """Return `(active_priorities_by_slug, active_pack_slugs_ordered)` for a workspace."""
    async with engine.connect() as conn:
        _, prios, _, slugs = await _fetch_workspace_pack_context(conn, workspace_id)
    return prios, slugs


async def resolve_workspace_pack_ontology_pg(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    enterprise_scope_id: str = "scope-global",
    domain_scope_id: str = "",
    team_chain_scope_ids: tuple[str, ...] = (),
    run_scope_id: str | None = None,
) -> WorkspacePackEffectiveResolution:
    """Resolve effective workspace ontology, DNA, broker policies & instructions flatly."""
    async with engine.connect() as conn:
        (
            resolved_ws,
            prio_by_slug,
            prio_by_bundle,
            active_slugs,
        ) = await _fetch_workspace_pack_context(conn, workspace_id)
        dna = await load_flat_dna_mechanisms(conn, prio_by_bundle)
        policies = await load_flat_broker_policies(conn, prio_by_bundle)
        instructions = await load_flat_pack_instructions(conn, resolved_ws, prio_by_bundle)

    concepts = tuple(await list_concepts_pg(engine))
    relations = tuple(await list_relations_pg(engine))
    axioms = tuple(await list_axioms_pg(engine))
    snapshot = OntologyHierarchyResolver.resolve_effective_ontology(
        concepts=concepts,
        relations=relations,
        axioms=axioms,
        enterprise_scope_id=enterprise_scope_id,
        domain_scope_id=domain_scope_id,
        team_chain_scope_ids=team_chain_scope_ids,
        workspace_scope_id=resolved_ws,
        run_scope_id=run_scope_id,
        active_pack_priorities=prio_by_slug,
    )
    return WorkspacePackEffectiveResolution(
        workspace_id=resolved_ws,
        active_pack_priorities=prio_by_slug,
        active_pack_slugs=active_slugs,
        ontology_snapshot=snapshot,
        dna_mechanisms=dna,
        broker_policies=policies,
        instructions=instructions,
    )


__all__ = [
    "WorkspacePackEffectiveResolution",
    "load_workspace_active_pack_priorities_pg",
    "resolve_workspace_pack_ontology_pg",
]

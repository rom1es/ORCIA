"""SQL materialization for pack ontology concepts, relations, and axioms (`<= 300 L`)."""

from __future__ import annotations

import json

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection
from uuid_utils import uuid7

from orcia_core.packs.models import LoadedPackBundleV2


async def materialize_pack_ontology(
    conn: AsyncConnection,
    *,
    bundle_id: str,
    bundle: LoadedPackBundleV2,
) -> None:
    """Materialize glossary concepts, relations, and axioms into ontology tables."""
    slug = bundle.manifest.slug.strip()
    glossary = bundle.glossary if isinstance(bundle.glossary, dict) else {}
    raw_terms = glossary.get("terms") or glossary.get("concepts") or []
    terms = [t for t in raw_terms if isinstance(t, dict)] if isinstance(raw_terms, list) else []

    concept_ids_by_key: dict[str, str] = {}
    kept_concept_keys: list[str] = []
    for item in terms:
        raw_key = str(item.get("key") or item.get("concept_key") or item.get("label") or "").strip()
        if not raw_key:
            continue
        ckey = f"pack:{slug}:{raw_key}"[:128]
        term = str(item.get("label") or item.get("canonical_term") or raw_key).strip()[:255]
        defn = str(item.get("definition") or item.get("definition_text") or term)
        synonyms = item.get("synonyms") or []
        banned = item.get("banned_terms") or []
        profiles = item.get("profile_translations") or {}
        schema = item.get("expected_schema") or {}
        kept_concept_keys.append(ckey)
        row = (
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO ontology_concepts (
                        id, concept_key, canonical_term, level, scope_id, definition_text,
                        synonyms_jsonb, banned_terms_jsonb, profile_translations_jsonb,
                        expected_schema_jsonb, snapshot_branch_status, pack_bundle_id
                    )
                    VALUES (
                        CAST(:id AS uuid), :concept_key, :canonical_term, '2_DOMAIN', :scope_id,
                        :definition_text, CAST(:synonyms AS jsonb), CAST(:banned AS jsonb),
                        CAST(:profiles AS jsonb), CAST(:schema AS jsonb), 'ACTIVE',
                        CAST(:bid AS uuid)
                    )
                    ON CONFLICT (pack_bundle_id, concept_key)
                    WHERE pack_bundle_id IS NOT NULL DO UPDATE SET
                        canonical_term = EXCLUDED.canonical_term,
                        level = EXCLUDED.level,
                        scope_id = EXCLUDED.scope_id,
                        definition_text = EXCLUDED.definition_text,
                        synonyms_jsonb = EXCLUDED.synonyms_jsonb,
                        banned_terms_jsonb = EXCLUDED.banned_terms_jsonb,
                        profile_translations_jsonb = EXCLUDED.profile_translations_jsonb,
                        expected_schema_jsonb = EXCLUDED.expected_schema_jsonb,
                        snapshot_branch_status = 'ACTIVE'
                    RETURNING id::text
                    """
                ),
                {
                    "id": str(uuid7()),
                    "concept_key": ckey,
                    "canonical_term": term,
                    "scope_id": slug[:128],
                    "definition_text": defn,
                    "synonyms": json.dumps(list(synonyms) if isinstance(synonyms, list) else []),
                    "banned": json.dumps(list(banned) if isinstance(banned, list) else []),
                    "profiles": json.dumps(dict(profiles) if isinstance(profiles, dict) else {}),
                    "schema": json.dumps(dict(schema) if isinstance(schema, dict) else {}),
                    "bid": bundle_id,
                },
            )
        ).scalar_one()
        concept_ids_by_key[raw_key] = str(row)
        concept_ids_by_key[term] = str(row)

    raw_rels = glossary.get("relations") or []
    rels = [r for r in raw_rels if isinstance(r, dict)] if isinstance(raw_rels, list) else []
    kept_rel_keys: list[str] = []
    for idx, rel in enumerate(rels):
        src_k = str(rel.get("source") or rel.get("source_term") or "").strip()
        tgt_k = str(rel.get("target") or rel.get("target_term") or "").strip()
        src_id = concept_ids_by_key.get(src_k)
        tgt_id = concept_ids_by_key.get(tgt_k)
        if not src_id or not tgt_id:
            continue
        rkey = str(rel.get("relation_key") or f"pack:{slug}:rel:{idx}:{src_k}:{tgt_k}")[:128]
        kept_rel_keys.append(rkey)
        await conn.execute(
            sa.text(
                """
                INSERT INTO ontology_relations (
                    id, relation_key, source_concept_id, target_concept_id,
                    relation_type, cardinality, pack_bundle_id
                )
                VALUES (
                    CAST(:id AS uuid), :rkey, CAST(:src AS uuid), CAST(:tgt AS uuid),
                    :rtype, :card, CAST(:bid AS uuid)
                )
                ON CONFLICT (pack_bundle_id, relation_key)
                WHERE pack_bundle_id IS NOT NULL DO UPDATE SET
                    source_concept_id = EXCLUDED.source_concept_id,
                    target_concept_id = EXCLUDED.target_concept_id,
                    relation_type = EXCLUDED.relation_type,
                    cardinality = EXCLUDED.cardinality
                """
            ),
            {
                "id": str(uuid7()),
                "rkey": rkey,
                "src": src_id,
                "tgt": tgt_id,
                "rtype": str(rel.get("relation_type") or "RELATES_TO")[:64],
                "card": str(rel.get("cardinality") or "1..N")[:32],
                "bid": bundle_id,
            },
        )

    raw_axioms = glossary.get("axioms") or []
    axioms = [a for a in raw_axioms if isinstance(a, dict)] if isinstance(raw_axioms, list) else []
    kept_axiom_keys: list[str] = []
    for idx, ax in enumerate(axioms):
        ck = str(ax.get("concept_key") or ax.get("term") or "").strip()
        cid = concept_ids_by_key.get(ck)
        if not cid:
            continue
        akey = str(ax.get("axiom_key") or f"pack:{slug}:ax:{idx}:{ck}")[:128]
        kept_axiom_keys.append(akey)
        await conn.execute(
            sa.text(
                """
                INSERT INTO ontology_axioms (
                    id, axiom_key, concept_id, level, scope_id,
                    rule_expression, immutable, pack_bundle_id
                )
                VALUES (
                    CAST(:id AS uuid), :akey, CAST(:cid AS uuid), '2_DOMAIN', :scope_id,
                    :expr, :imm, CAST(:bid AS uuid)
                )
                ON CONFLICT (pack_bundle_id, axiom_key)
                WHERE pack_bundle_id IS NOT NULL DO UPDATE SET
                    concept_id = EXCLUDED.concept_id,
                    rule_expression = EXCLUDED.rule_expression,
                    immutable = EXCLUDED.immutable
                """
            ),
            {
                "id": str(uuid7()),
                "akey": akey,
                "cid": cid,
                "scope_id": slug[:128],
                "expr": str(ax.get("rule_expression") or ""),
                "imm": bool(ax.get("immutable", True)),
                "bid": bundle_id,
            },
        )

    await conn.execute(
        sa.text(
            "DELETE FROM ontology_axioms WHERE pack_bundle_id = CAST(:bid AS uuid) "
            "AND NOT (axiom_key = ANY(:kept))"
        ),
        {"bid": bundle_id, "kept": kept_axiom_keys},
    )
    await conn.execute(
        sa.text(
            "DELETE FROM ontology_relations WHERE pack_bundle_id = CAST(:bid AS uuid) "
            "AND NOT (relation_key = ANY(:kept))"
        ),
        {"bid": bundle_id, "kept": kept_rel_keys},
    )
    await conn.execute(
        sa.text(
            "DELETE FROM ontology_concepts WHERE pack_bundle_id = CAST(:bid AS uuid) "
            "AND NOT (concept_key = ANY(:kept))"
        ),
        {"bid": bundle_id, "kept": kept_concept_keys},
    )


__all__ = ["materialize_pack_ontology"]

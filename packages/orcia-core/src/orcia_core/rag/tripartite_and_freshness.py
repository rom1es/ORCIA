"""Tripartite Traceability Graph (`1..N`) and `data-freshness` Brick (Story 2.4, AD-8).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import re
from typing import Literal

from orcia_core.domain.identifiers import new_uuid7_str
from orcia_core.rag.hybrid_rag_service import RRF_K, HybridRagService
from orcia_core.rag.models import (
    DocVsCodeAuditFinding,
    KbStaleAlertEntity,
    TripartiteNodeType,
    TripartiteRelationType,
    TripartiteTraceEdgeEntity,
)

JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-[0-9]+)\b")


def extract_jira_issue_keys(text: str) -> tuple[str, ...]:
    """Extract unique Jira issue keys (`[A-Z][A-Z0-9]+-[0-9]+`) preserving appearance order."""
    seen: dict[str, None] = {}
    for match in JIRA_KEY_RE.finditer(text):
        seen[match.group(1)] = None
    return tuple(seen.keys())


class TripartiteGraphAndFreshnessService:
    """Builds `Confluence 1..N <-> Jira 1..N <-> Git 1..N <-> Ontology` & evaluates freshness."""

    def __init__(
        self,
        *,
        rag_service: HybridRagService,
        edges: tuple[TripartiteTraceEdgeEntity, ...] = (),
        alerts: tuple[KbStaleAlertEntity, ...] = (),
    ) -> None:
        self._rag = rag_service
        self._edges: list[TripartiteTraceEdgeEntity] = list(edges)
        self._alerts: list[KbStaleAlertEntity] = list(alerts)

    def list_edges(
        self, *, workspace_id: str | None = None
    ) -> tuple[TripartiteTraceEdgeEntity, ...]:
        if workspace_id is None:
            return tuple(self._edges)
        return tuple(e for e in self._edges if e.workspace_id == workspace_id)

    def list_alerts(self, *, workspace_id: str | None = None) -> tuple[KbStaleAlertEntity, ...]:
        if workspace_id is None:
            return tuple(self._alerts)
        return tuple(a for a in self._alerts if a.workspace_id == workspace_id)

    def _append_edge(
        self,
        *,
        created: list[TripartiteTraceEdgeEntity],
        existing_keys: set[str],
        edge_key: str,
        workspace_id: str,
        source_uri: str,
        source_node_type: TripartiteNodeType,
        target_uri: str,
        target_node_type: TripartiteNodeType,
        relation_type: TripartiteRelationType,
        jira_issue_key: str | None,
    ) -> None:
        if edge_key in existing_keys:
            return
        edge = TripartiteTraceEdgeEntity(
            id=new_uuid7_str(),
            edge_key=edge_key,
            workspace_id=workspace_id,
            source_uri=source_uri,
            source_node_type=source_node_type,
            target_uri=target_uri,
            target_node_type=target_node_type,
            relation_type=relation_type,
            jira_issue_key=jira_issue_key,
        )
        self._edges.append(edge)
        created.append(edge)
        existing_keys.add(edge_key)

    def register_cross_source_traceability(
        self,
        *,
        workspace_id: str,
        confluence_uri: str,
        confluence_text: str,
        git_repo_uri: str,
        git_symbol: str,
        commit_message: str,
        ontology_concept_key: str | None = None,
        fixed_jira_keys: tuple[str, ...] = (),
        blocked_jira_keys: tuple[str, ...] = (),
    ) -> tuple[TripartiteTraceEdgeEntity, ...]:
        """Extract Jira keys (`[A-Z][A-Z0-9]+-[0-9]+`) and link Confluence, Jira, Git & Ontology.

        Emits all 6 relation types: `DOCUMENTS`, `SPECIFIES`, `FIXES`, `BLOCKS`,
        `IMPLEMENTS_ISSUE`, and `AFFECTS_CONCEPT` (`Story 2.4 AC1`).
        """
        created: list[TripartiteTraceEdgeEntity] = []
        existing_keys = {e.edge_key for e in self._edges}

        doc_jira_keys = extract_jira_issue_keys(confluence_text)
        git_jira_keys = extract_jira_issue_keys(commit_message)
        all_jira_keys = tuple(dict.fromkeys((*doc_jira_keys, *git_jira_keys)))
        git_uri = f"{git_repo_uri}#{git_symbol}"

        # 1. Confluence DOCUMENTS Git symbol
        self._append_edge(
            created=created,
            existing_keys=existing_keys,
            edge_key=f"trace-doc-git-{confluence_uri}-{git_uri}",
            workspace_id=workspace_id,
            source_uri=confluence_uri,
            source_node_type="CONFLUENCE_PAGE",
            target_uri=git_uri,
            target_node_type="GIT_SYMBOL",
            relation_type="DOCUMENTS",
            jira_issue_key=all_jira_keys[0] if all_jira_keys else None,
        )

        # 2. Confluence SPECIFIES Jira issue
        for j_key in doc_jira_keys:
            self._append_edge(
                created=created,
                existing_keys=existing_keys,
                edge_key=f"trace-doc-jira-{confluence_uri}-{j_key}",
                workspace_id=workspace_id,
                source_uri=confluence_uri,
                source_node_type="CONFLUENCE_PAGE",
                target_uri=f"jira://issues/{j_key}",
                target_node_type="JIRA_ISSUE",
                relation_type="SPECIFIES",
                jira_issue_key=j_key,
            )

        # 3. Git symbol IMPLEMENTS_ISSUE Jira issue
        for j_key in all_jira_keys:
            self._append_edge(
                created=created,
                existing_keys=existing_keys,
                edge_key=f"trace-git-jira-{git_uri}-{j_key}",
                workspace_id=workspace_id,
                source_uri=git_uri,
                source_node_type="GIT_SYMBOL",
                target_uri=f"jira://issues/{j_key}",
                target_node_type="JIRA_ISSUE",
                relation_type="IMPLEMENTS_ISSUE",
                jira_issue_key=j_key,
            )

        # 4. Jira FIXES / BLOCKS relationships
        primary_jira = all_jira_keys[0] if all_jira_keys else None
        if primary_jira:
            for fixed_key in fixed_jira_keys:
                self._append_edge(
                    created=created,
                    existing_keys=existing_keys,
                    edge_key=f"trace-jira-fixes-{primary_jira}-{fixed_key}",
                    workspace_id=workspace_id,
                    source_uri=f"jira://issues/{primary_jira}",
                    source_node_type="JIRA_ISSUE",
                    target_uri=f"jira://issues/{fixed_key}",
                    target_node_type="JIRA_ISSUE",
                    relation_type="FIXES",
                    jira_issue_key=primary_jira,
                )
            for blocked_key in blocked_jira_keys:
                self._append_edge(
                    created=created,
                    existing_keys=existing_keys,
                    edge_key=f"trace-jira-blocks-{primary_jira}-{blocked_key}",
                    workspace_id=workspace_id,
                    source_uri=f"jira://issues/{primary_jira}",
                    source_node_type="JIRA_ISSUE",
                    target_uri=f"jira://issues/{blocked_key}",
                    target_node_type="JIRA_ISSUE",
                    relation_type="BLOCKS",
                    jira_issue_key=primary_jira,
                )

        # 5. Git symbol AFFECTS_CONCEPT Ontology concept
        if ontology_concept_key:
            self._append_edge(
                created=created,
                existing_keys=existing_keys,
                edge_key=f"trace-git-concept-{git_uri}-{ontology_concept_key}",
                workspace_id=workspace_id,
                source_uri=git_uri,
                source_node_type="GIT_SYMBOL",
                target_uri=f"orcia://ontology/concepts/{ontology_concept_key}",
                target_node_type="ONTOLOGY_CONCEPT",
                relation_type="AFFECTS_CONCEPT",
                jira_issue_key=primary_jira,
            )

        return tuple(created)

    def evaluate_data_freshness(
        self,
        *,
        workspace_id: str,
        doc_key: str,
        age_days: int,
        contradicting_done_jira_key: str | None = None,
        impacted_active_run_ids: tuple[str, ...] = (),
    ) -> KbStaleAlertEntity | None:
        """`data-freshness` brick: raise `[STALE_WARNING]` if TTL exceeded or Jira contradicted."""
        docs = {d.doc_key: d for d in self._rag.list_documents(workspace_id=workspace_id)}
        doc = docs.get(doc_key)
        if doc is None:
            return None

        ttl_expired = age_days > doc.freshness_ttl_days
        if not ttl_expired and contradicting_done_jira_key is None:
            return None

        self._rag.mark_document_stale(doc_key=doc_key, age_days=age_days)
        reason: Literal["TTL_EXPIRED", "NEWER_JIRA_CONTRADICTION"] = (
            "NEWER_JIRA_CONTRADICTION" if contradicting_done_jira_key is not None else "TTL_EXPIRED"
        )
        alert = KbStaleAlertEntity(
            id=new_uuid7_str(),
            alert_key=f"stale-{doc_key}-{reason.lower()}",
            workspace_id=workspace_id,
            document_key=doc_key,
            source_uri=doc.source_uri,
            alert_reason=reason,
            diagnostic_marker="[STALE_WARNING]",
            justifying_jira_key=contradicting_done_jira_key,
            impacted_run_ids=impacted_active_run_ids,
            resolved=False,
        )
        self._alerts = [a for a in self._alerts if a.alert_key != alert.alert_key]
        self._alerts.append(alert)
        return alert

    def audit_doc_vs_code_divergence(
        self,
        *,
        confluence_uri: str,
        git_repo_uri: str,
        git_symbol: str,
        doc_rule_summary: str,
        code_rule_summary: str,
        newer_done_jira_key: str | None = None,
    ) -> DocVsCodeAuditFinding:
        """Qualify Doc vs Code divergence using Tripartite Graph (`[DOC_OBSOLETE_SUSPECTED]`)."""
        if doc_rule_summary.strip() == code_rule_summary.strip():
            return DocVsCodeAuditFinding(
                confluence_uri=confluence_uri,
                git_repo_uri=git_repo_uri,
                git_symbol=git_symbol,
                qualification_marker="[ALIGNED]",
                justifying_jira_key=None,
                explanation="La spécification Confluence et le symbole Git AST sont alignés.",
            )

        if newer_done_jira_key is not None:
            return DocVsCodeAuditFinding(
                confluence_uri=confluence_uri,
                git_repo_uri=git_repo_uri,
                git_symbol=git_symbol,
                qualification_marker="[DOC_OBSOLETE_SUSPECTED]",
                justifying_jira_key=newer_done_jira_key,
                explanation=(
                    f"Divergence Confluence ({doc_rule_summary}) vs Git ({code_rule_summary}) "
                    f"justifiée par le ticket Jira Done ({newer_done_jira_key})."
                ),
            )

        return DocVsCodeAuditFinding(
            confluence_uri=confluence_uri,
            git_repo_uri=git_repo_uri,
            git_symbol=git_symbol,
            qualification_marker="[BUG_CODE_SUSPECTED]",
            justifying_jira_key=None,
            explanation=(
                f"Divergence non justifiée par un ticket Jira : Confluence spécifie "
                f"'{doc_rule_summary}' tandis que le code applique '{code_rule_summary}'."
            ),
        )


__all__ = [
    "HybridRagService",
    "JIRA_KEY_RE",
    "RRF_K",
    "TripartiteGraphAndFreshnessService",
    "extract_jira_issue_keys",
]

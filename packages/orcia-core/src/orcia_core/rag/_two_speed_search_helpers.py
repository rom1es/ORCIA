"""Speed 1 & Speed 2 scoring helpers for `TwoSpeedFederatedSearchService` (`Story 9.3`)."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from orcia_core.rag._rag_locales import get_rag_locale_bundle
from orcia_core.rag._two_speed_search_models import (
    FederatedSearchCandidate,
    FederatedSearchHit,
    SearchScopeMode,
    normalize_search_query,
)
from orcia_core.rag.indexer_and_rrf import cosine_similarity
from orcia_core.rag.models import DocVsCodeAuditFinding


def prepare_authorized_and_speed1_hits(
    *,
    candidates: Sequence[FederatedSearchCandidate],
    query: str,
    scope: SearchScopeMode,
    active_workspace_id: str,
    active_screen_route: str,
    user_role: str,
    extra_candidates: Sequence[FederatedSearchCandidate],
    user_id: str = "",
    authorized_workspace_ids: Collection[str] | None = None,
    restricted_workspace_ids: Collection[str] | None = None,
) -> tuple[
    str,
    list[str],
    list[FederatedSearchCandidate],
    list[FederatedSearchHit],
    set[str],
]:
    """Filter candidates by RBAC/scope and score Speed 1 lexical matches."""
    norm_q = normalize_search_query(query)
    words = [w for w in norm_q.split(" ") if w]
    merged_candidates: list[FederatedSearchCandidate] = list(candidates)
    seen_ids = {c.item_id for c in merged_candidates}
    for cand in extra_candidates:
        if cand.item_id not in seen_ids:
            merged_candidates.append(cand)
            seen_ids.add(cand.item_id)

    clean_ws = active_workspace_id.strip()
    is_global_or_empty_ws = not clean_ws or clean_ws in ("scope-global", "GLOBAL")
    auth_ws_set = (
        frozenset(authorized_workspace_ids) if authorized_workspace_ids is not None else None
    )
    restricted_ws_set = (
        frozenset(restricted_workspace_ids) if restricted_workspace_ids is not None else frozenset()
    )
    authorized: list[FederatedSearchCandidate] = []
    for cand in merged_candidates:
        if user_role not in cand.allowed_roles:
            continue
        if cand.allowed_user_ids is not None and user_id not in cand.allowed_user_ids:
            continue
        if cand.workspace_id not in ("", "GLOBAL", "scope-global"):
            is_restricted_ws = cand.workspace_id in restricted_ws_set or cand.visibility_mode in (
                "CONFIDENTIAL_RESTRICTED",
                "PRIVATE_USER",
            )
            if is_restricted_ws and (auth_ws_set is None or cand.workspace_id not in auth_ws_set):
                continue
            if (
                restricted_workspace_ids is None
                and auth_ws_set is not None
                and cand.workspace_id not in auth_ws_set
            ):
                continue
        cand_matches_ws = cand.workspace_id in (clean_ws, "GLOBAL")
        if scope == "SCREEN" and (
            (not is_global_or_empty_ws and not cand_matches_ws)
            or cand.screen_route != active_screen_route
        ):
            continue
        if scope == "WORKSPACE" and not is_global_or_empty_ws and not cand_matches_ws:
            continue
        authorized.append(cand)

    speed1_hits: list[FederatedSearchHit] = []
    speed1_ids: set[str] = set()
    for cand in authorized:
        haystack = f"{cand.title} {cand.snippet}".lower()
        matched_tokens = sum(1 for w in words if w in haystack)
        if not words or matched_tokens == len(words) or (norm_q and norm_q in haystack):
            score = 1.0 + (0.1 * matched_tokens)
            speed1_ids.add(cand.item_id)
            speed1_hits.append(
                FederatedSearchHit(
                    item_id=cand.item_id,
                    family=cand.family,
                    title=cand.title,
                    snippet=cand.snippet,
                    workspace_id=cand.workspace_id,
                    screen_route=cand.screen_route,
                    deep_link_uri=cand.deep_link_uri,
                    speed_tier=1,
                    locked_top=True,
                    score=round(score, 4),
                    badge=None,
                    highlight_duration_ms=2000,
                    opens_contextual_help_column=(cand.family == "HELP_ACTIONS"),
                )
            )
    return norm_q, words, authorized, speed1_hits, speed1_ids


def compute_speed2_semantic_hits(
    *,
    authorized: list[FederatedSearchCandidate],
    speed1_ids: set[str],
    query_embedding: tuple[float, ...],
    locale: str = "fr",
) -> tuple[FederatedSearchHit, ...]:
    """Score Speed 2 semantic matches with localized near-match badge."""
    semantic_badge = get_rag_locale_bundle(locale).semantic_badge
    speed2_candidates: list[FederatedSearchHit] = []
    for cand in authorized:
        if cand.item_id in speed1_ids:
            continue
        if cand.embedding is not None:
            sim = max(0.01, (cosine_similarity(query_embedding, cand.embedding) + 1.0) / 2.0)
        else:
            sim = 0.5
        speed2_candidates.append(
            FederatedSearchHit(
                item_id=cand.item_id,
                family=cand.family,
                title=cand.title,
                snippet=cand.snippet,
                workspace_id=cand.workspace_id,
                screen_route=cand.screen_route,
                deep_link_uri=cand.deep_link_uri,
                speed_tier=2,
                locked_top=False,
                score=round(sim, 4),
                badge=semantic_badge,
                highlight_duration_ms=2000,
                opens_contextual_help_column=(cand.family == "HELP_ACTIONS"),
            )
        )
    speed2_candidates.sort(key=lambda item: -item.score)
    return tuple(speed2_candidates)


def evaluate_doc_vs_code_divergence(
    *,
    confluence_uri: str,
    git_repo_uri: str,
    git_symbol: str,
    doc_rule_summary: str,
    code_rule_summary: str,
    newer_done_jira_key: str | None = None,
    locale: str = "fr",
) -> DocVsCodeAuditFinding:
    """Qualify Doc vs Code divergence using Tripartite Graph."""
    bundle = get_rag_locale_bundle(locale)
    if doc_rule_summary.strip() == code_rule_summary.strip():
        return DocVsCodeAuditFinding(
            confluence_uri=confluence_uri,
            git_repo_uri=git_repo_uri,
            git_symbol=git_symbol,
            qualification_marker="[ALIGNED]",
            justifying_jira_key=None,
            explanation=bundle.tripartite_aligned,
        )
    if newer_done_jira_key is not None:
        return DocVsCodeAuditFinding(
            confluence_uri=confluence_uri,
            git_repo_uri=git_repo_uri,
            git_symbol=git_symbol,
            qualification_marker="[DOC_OBSOLETE_SUSPECTED]",
            justifying_jira_key=newer_done_jira_key,
            explanation=bundle.tripartite_obsolete_tpl.format(
                doc_summary=doc_rule_summary,
                code_summary=code_rule_summary,
                jira_key=newer_done_jira_key,
            ),
        )
    return DocVsCodeAuditFinding(
        confluence_uri=confluence_uri,
        git_repo_uri=git_repo_uri,
        git_symbol=git_symbol,
        qualification_marker="[BUG_CODE_SUSPECTED]",
        justifying_jira_key=None,
        explanation=bundle.tripartite_bug_tpl.format(
            doc_summary=doc_rule_summary,
            code_summary=code_rule_summary,
        ),
    )

"""Topological ordering for organizational unit dictionaries in setup configurations.

Pure domain helper (`AD-6`, `Story 17.2`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def sort_org_unit_dicts_topologically(
    raw_units: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Sort setup `org_units` dicts topologically so every parent precedes its children."""
    items = [dict(u) for u in raw_units]
    by_ref: dict[str, int] = {}
    for idx, item in enumerate(items):
        uid = str(item.get("id") or "").strip()
        uslug = str(item.get("slug") or "").strip()
        if uid:
            by_ref[uid] = idx
        if uslug and uslug not in by_ref:
            by_ref[uslug] = idx

    emitted: set[int] = set()
    visiting: set[int] = set()
    ordered: list[dict[str, object]] = []

    def _emit(idx: int) -> None:
        if idx in emitted or idx in visiting:
            return
        visiting.add(idx)
        parent_ref = str(items[idx].get("parentId") or items[idx].get("parent_id") or "").strip()
        if parent_ref and parent_ref != "scope-global" and parent_ref in by_ref:
            parent_idx = by_ref[parent_ref]
            if parent_idx != idx:
                _emit(parent_idx)
        visiting.discard(idx)
        emitted.add(idx)
        ordered.append(items[idx])

    # Visit BUs first so root/sub-BUs precede teams deterministically
    sorted_indices = sorted(
        range(len(items)),
        key=lambda i: (
            0
            if str(items[i].get("level") or items[i].get("unit_type") or "BU").upper() == "BU"
            else 1,
            i,
        ),
    )
    for idx in sorted_indices:
        _emit(idx)
    return ordered


__all__ = ["sort_org_unit_dicts_topologically"]

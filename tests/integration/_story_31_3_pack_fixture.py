"""Test archive builder helper for Story 31.3 PG18 integration tests."""

from __future__ import annotations

import io
import zipfile

import yaml


def build_overlapping_pack_zip(*, slug: str, definition: str, instr_text: str) -> bytes:
    """Build a declarative pack ZIP with overlapping agent, skill, glossary, and DNA assets."""
    buf = io.BytesIO()
    apm = yaml.safe_dump(
        {
            "name": slug,
            "version": "1.0.0",
            "description": f"Pack {slug}",
            "x-orcia": {
                "slug": slug,
                "bundle_kind": "IMPORTED",
                "scope_type": "WORKSPACE",
                "scope_id": "global",
                "status": "PUBLISHED",
            },
        }
    )
    agent = (
        f"---\nname: {slug} Reviewer\ndescription: Reviews\n"
        "x-orcia:\n  posture: PRODUCER\n  human_partner_role: TECH_LEAD\n"
        f"---\nFollow {slug} review standards.\n"
    )
    skill = (
        f"---\nname: {slug} Compliance Check\ndescription: Checks\n"
        "x-orcia:\n  command_handle: /compliance-check\n"
        f"---\nExecute {slug} compliance check.\n"
    )
    glossary = yaml.safe_dump(
        {
            "terms": [
                {
                    "key": "release-gate",
                    "label": "Release Gate",
                    "definition": definition,
                    "synonyms": ["Gate"],
                }
            ]
        }
    )
    instr = f"---\napplyTo: '**/*'\ndescription: {slug} release rules\n---\n{instr_text}\n"
    mech_star = (
        "def evaluate(doc):\n"
        f"    st = 'PASS' if str(doc.get('pack', '')) == {slug!r} else 'FAIL'\n"
        "    orcia_sys.emit_verdict('GATE', st, 'Pack gate')\n"
    )
    mech_yaml = yaml.safe_dump(
        {
            "mechanism_slug": "gate_check",
            "name": f"{slug} Gate Check",
            "passing_test_payload": {"pack": slug},
            "failing_test_payload": {"pack": "other"},
        }
    )
    policy = (
        "---\nuri_pattern: mcp://gate/check\nconnector_scheme: mcp\n"
        "required_role: WORKSPACE_MEMBER\nsla_hours: 12\n---\nApprove check.\n"
    )
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel, body in (
            ("apm.yml", apm),
            ("agents/reviewer.agent.md", agent),
            ("skills/compliance-check/SKILL.md", skill),
            ("ontology/glossary.yaml", glossary),
            ("instructions/release.instructions.md", instr),
            ("ontology/mechanisms/gate_check.star", mech_star),
            ("ontology/mechanisms/gate_check.yaml", mech_yaml),
            ("policies/gate-policy.policy.md", policy),
        ):
            zf.writestr(rel, body)
    return buf.getvalue()

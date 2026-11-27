"""Story 31.1 Layer 1a unit tests for `ApmPackCodec` decoding, readiness, and lockfiles."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from orcia_core.packs import (
    ApmPackCodec,
    PackBundleKind,
    PackInvalidArchiveError,
    PackReadinessStatus,
    PackSourceOrigin,
    build_lockfile_dict,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKS_ROOT = REPO_ROOT / "packs"


def _build_zip_from_files(files: dict[str, bytes], *, prefix: str = "demo-pack") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in files.items():
            arc = f"{prefix}/{rel_path}" if prefix else rel_path
            zf.writestr(arc, content)
    return buf.getvalue()


def _sample_apm_files(*, include_lock: bool = True) -> dict[str, bytes]:
    apm_yml = {
        "name": "demo-pack",
        "version": "1.2.0",
        "description": "APM superset demo pack",
        "author": "orcia-team@example.org",
        "license": "Apache-2.0",
        "mcp": {"servers": {"tracker": {"transport": "stdio"}}},
        "x-orcia": {
            "id": "orcia-pack-demo",
            "slug": "demo-pack",
            "title_en": "Demo APM Pack",
            "title_fr": "Pack Demo APM",
            "rbac_namespace": "demo",
            "bundle_kind": "IMPORTED",
            "connector_slots": [
                {
                    "slot_key": "issue_tracker",
                    "scheme": "jira",
                    "connector_kind": "jira",
                    "source_nature": "ISSUE_TRACKER",
                    "required_access": ["read", "write_preview"],
                    "required": True,
                }
            ],
            "quick_actions": [
                {
                    "id": "qa-demo",
                    "label": "Run Demo Workflow",
                    "target_workflow_slug": "wf-demo",
                }
            ],
        },
    }
    agent_md = (
        "---\n"
        "name: Demo Reviewer\n"
        "description: Reviews specs deterministically\n"
        "x-orcia:\n"
        "  posture: CO_PILOT\n"
        "  llm_model_tier: complex\n"
        "  skill_refs:\n"
        "    - orcia://packs/demo-pack/skills/check-dor@1.2.0\n"
        "  connector_slots:\n"
        "    - slot://issue_tracker\n"
        "---\n"
        "# Reviewer Prompt\n\nInspect all requirements.\n"
    )
    external_agent_md = (
        "---\n"
        "name: External Community Agent\n"
        "description: Lacks x-orcia governance block\n"
        "---\n"
        "Do generic community review.\n"
    )
    skill_md = (
        "---\n"
        "name: Check DoR\n"
        "description: Validates Definition of Ready\n"
        "x-orcia:\n"
        "  command_handle: check-dor\n"
        "  is_si_write: false\n"
        "  human_authored_required: true\n"
        "  input_parameters:\n"
        "    - name: ticket_key\n"
        "      required: true\n"
        "---\n"
        "Verify INVEST criteria.\n"
    )
    instr_md = "---\napplyTo: '**/*.md'\ndescription: Markdown rules\n---\nAlways use headings.\n"
    wf_path = PACKS_ROOT / "orcia-docs" / "workflows" / "wf-generate-orcia-documentation.yaml"
    wf_yaml = wf_path.read_text(encoding="utf-8")
    vsm_path = PACKS_ROOT / "sdlc" / "workflows" / "vsm-mon-compte-idea-to-prod.yaml"
    vsm_yaml = vsm_path.read_text(encoding="utf-8")
    glossary_yaml = "domain: demo\nterms:\n  - key: DOR\n    label: Definition of Ready\n"
    star_code = (
        "def evaluate(payload):\n"
        "    title = payload.get('title', '')\n"
        "    ok = len(title) >= 5\n"
        "    orcia_sys.assert_rule(\n"
        "        rule_id='TITLE_MIN_LEN',\n"
        "        condition=ok,\n"
        "        message='Title must be >= 5 chars',\n"
        "    )\n"
    )
    star_meta = {
        "mechanism_slug": "check-title",
        "name": "Title Length Check",
        "passing_test_payload": {"title": "Valid Title"},
        "failing_test_payload": {"title": "No"},
    }
    gate_yaml = (
        "id: gate-demo\nrunner_plugin_id: markdown_contract_runner\nmin_chars_per_section: 10\n"
    )
    policy_md = (
        "---\n"
        "policy_key: jira-read-policy\n"
        "uri_pattern: 'jira://projects/*'\n"
        "connector_scheme: jira\n"
        "required_role: demo:reader\n"
        "approver_team: secops\n"
        "sla_hours: 12\n"
        "---\n"
        "Request Jira project read access.\n"
    )
    help_fr = "---\ntitle: Aide Demo\nbound_routes:\n  - /settings/packs\n---\nContenu FR.\n"
    help_en = "---\ntitle: Demo Help\nbound_routes:\n  - /settings/packs\n---\nEN content.\n"

    files: dict[str, bytes] = {
        "apm.yml": yaml.safe_dump(apm_yml, sort_keys=False).encode("utf-8"),
        "agents/demo-reviewer.agent.md": agent_md.encode("utf-8"),
        ".apm/agents/community-helper.agent.md": external_agent_md.encode("utf-8"),
        "skills/check-dor/SKILL.md": skill_md.encode("utf-8"),
        "instructions/style.instructions.md": instr_md.encode("utf-8"),
        "workflows/wf-generate-orcia-documentation.yaml": wf_yaml.encode("utf-8"),
        "workflows/vsm-mon-compte-idea-to-prod.yaml": vsm_yaml.encode("utf-8"),
        "ontology/glossary.yaml": glossary_yaml.encode("utf-8"),
        "ontology/mechanisms/check-title.star": star_code.encode("utf-8"),
        "ontology/mechanisms/check-title.yaml": yaml.safe_dump(star_meta).encode("utf-8"),
        "gates/gate-demo.yaml": gate_yaml.encode("utf-8"),
        "policies/jira-read.policy.md": policy_md.encode("utf-8"),
        "help/fr/overview.md": help_fr.encode("utf-8"),
        "help/en/overview.md": help_en.encode("utf-8"),
    }
    if include_lock:
        lock_dict = build_lockfile_dict(files)
        files["apm.lock.yaml"] = yaml.safe_dump(lock_dict, sort_keys=True).encode("utf-8")
    return files


def test_apm_codec_decodes_superset_zip_and_dir_deterministically(tmp_path: Path) -> None:
    codec = ApmPackCodec()
    files = _sample_apm_files(include_lock=True)
    zip_bytes = _build_zip_from_files(files, prefix="demo-pack")

    bundle = codec.decode_zip_bytes(zip_bytes)
    assert bundle.manifest.slug == "demo-pack"
    assert bundle.manifest.version == "1.2.0"
    assert bundle.manifest.bundle_kind == PackBundleKind.IMPORTED
    assert bundle.manifest.source_origin == PackSourceOrigin.APM_ZIP
    assert len(bundle.manifest.declared_slots) == 1
    assert bundle.manifest.declared_slots[0].slot_key == "issue_tracker"
    assert bundle.lockfile is not None
    assert len(bundle.archive_sha256) == 64

    agents_by_slug = {a.slug: a for a in bundle.agents}
    assert set(agents_by_slug.keys()) == {"community-helper", "demo-reviewer"}
    assert agents_by_slug["demo-reviewer"].lifecycle_status == PackReadinessStatus.ACTIVE
    assert agents_by_slug["community-helper"].lifecycle_status == PackReadinessStatus.DRAFT

    assert len(bundle.skills) == 1
    assert bundle.skills[0].human_authored_required is True
    assert bundle.skills[0].lifecycle_status == PackReadinessStatus.ACTIVE
    assert len(bundle.instructions) == 1
    assert len(bundle.workflows) == 1
    assert len(bundle.vsm_specs) == 1
    assert bundle.glossary["domain"] == "demo"
    assert len(bundle.dna_mechanisms) == 1
    assert bundle.dna_mechanisms[0].mechanism_slug == "check-title"
    assert "gate-demo" in bundle.gates_specs
    assert len(bundle.policies) == 1
    assert len(bundle.help_articles) == 2

    zip1 = codec.encode_zip_bytes(bundle)
    zip2 = codec.encode_zip_bytes(bundle)
    assert zip1 == zip2
    assert hashlib.sha256(zip1).hexdigest() == bundle.archive_sha256

    pack_dir = tmp_path / "demo-pack"
    for rel, blob in files.items():
        dest = pack_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
    dir_bundle = codec.decode_directory(pack_dir)
    assert dir_bundle.archive_sha256 == bundle.archive_sha256

    draft_files = _sample_apm_files(include_lock=False)
    draft_files["agents/no-body.agent.md"] = (
        b"---\nname: Empty\nx-orcia:\n  posture: CO_PILOT\n---\n"
    )
    draft_files["agents/no-role.agent.md"] = (
        b"---\nname: NoRole\nx-orcia:\n  llm_model_tier: simple\n---\nHas body.\n"
    )
    draft_bundle = codec.decode_zip_bytes(_build_zip_from_files(draft_files))
    by_slug = {a.slug: a for a in draft_bundle.agents}
    assert by_slug["no-body"].lifecycle_status == PackReadinessStatus.DRAFT
    assert by_slug["no-role"].lifecycle_status == PackReadinessStatus.DRAFT


def test_apm_codec_supports_legacy_sdlc_and_orcia_docs_packs() -> None:
    codec = ApmPackCodec()
    sdlc = codec.decode_directory(PACKS_ROOT / "sdlc")
    docs = codec.decode_directory(PACKS_ROOT / "orcia-docs")

    assert sdlc.manifest.slug == "sdlc"
    assert sdlc.manifest.bundle_kind == PackBundleKind.SYSTEM
    assert len(sdlc.agents) == 4
    assert len(sdlc.skills) == 4
    assert len(sdlc.vsm_specs) == 1
    assert len(sdlc.workflows) == 4
    assert len(sdlc.help_articles) == 2

    assert docs.manifest.slug == "orcia-docs"
    assert len(docs.agents) == 1
    assert len(docs.workflows) == 1


def test_apm_codec_rejects_lockfile_tampering_missing_and_unlisted_files() -> None:
    codec = ApmPackCodec()
    files = _sample_apm_files(include_lock=True)
    files["agents/demo-reviewer.agent.md"] += b"\ntampered"
    with pytest.raises(PackInvalidArchiveError, match="(Byte size|SHA-256) mismatch"):
        codec.decode_zip_bytes(_build_zip_from_files(files))

    same_len_files = _sample_apm_files(include_lock=True)
    orig = same_len_files["instructions/style.instructions.md"]
    same_len_files["instructions/style.instructions.md"] = orig[:-1] + b"!"
    with pytest.raises(PackInvalidArchiveError, match="SHA-256 mismatch"):
        codec.decode_zip_bytes(_build_zip_from_files(same_len_files))

    missing_files = _sample_apm_files(include_lock=True)
    missing_files.pop("instructions/style.instructions.md")
    with pytest.raises(PackInvalidArchiveError, match="missing file"):
        codec.decode_zip_bytes(_build_zip_from_files(missing_files))

    extra_files = _sample_apm_files(include_lock=True)
    extra_files["agents/unlisted.agent.md"] = b"# extra"
    with pytest.raises(PackInvalidArchiveError, match="unlisted"):
        codec.decode_zip_bytes(_build_zip_from_files(extra_files))

    bad_bundle_sha = _sample_apm_files(include_lock=True)
    lock_doc = yaml.safe_load(bad_bundle_sha["apm.lock.yaml"].decode())
    lock_doc["bundle_sha256"] = "f" * 64
    bad_bundle_sha["apm.lock.yaml"] = yaml.safe_dump(lock_doc).encode()
    with pytest.raises(PackInvalidArchiveError, match="bundle_sha256"):
        codec.decode_zip_bytes(_build_zip_from_files(bad_bundle_sha))

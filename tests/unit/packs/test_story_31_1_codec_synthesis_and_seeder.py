"""Story 31.1 Layer 1a codec synthesis, malformed input, and seeder partial-index tests."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from orcia_core.bootstrap.seeder import (
    CATALOG_ITEMS_UPSERT_SPEC,
    HELP_ARTICLES_CATALOG_UPSERT_SPEC,
    PERMISSION_BROKER_POLICIES_UPSERT_SPEC,
    UpsertSpec,
    build_postgres_upsert_sql,
)
from orcia_core.packs import (
    ApmPackCodec,
    LoadedPackBundleV2,
    PackAgentSpec,
    PackDnaMechanismSpec,
    PackHelpArticleSpec,
    PackInstructionSpec,
    PackInvalidArchiveError,
    PackManifestV2,
    PackPolicySpec,
    PackSkillSpec,
)
from orcia_core.packs._internal._apm_bundle_synthesizer import _dump_frontmatter_md
from orcia_core.workflows.schemas_v2 import (
    DeterministicSubStepSpec,
    ValueStreamMapSpec,
    VsmStepNodeSpec,
    WorkflowDefinitionV2,
)


def _zip_of(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, data in entries.items():
            zf.writestr(path, data)
    return buf.getvalue()


@pytest.mark.parametrize(
    "entries",
    [
        {"README.md": b"missing manifest"},
        {"apm.yml": b"not: [valid: yaml"},
        {"apm.yml": b"- list-not-dict"},
        {"apm.yml": b"name: ''\nversion: ''"},
        {"pack.yaml": b"- not-dict"},
        {"pack.yaml": b"slug: x\nname: X"},
        {"apm.yml": b"name: x\nversion: 1.0.0", "apm.lock.yaml": b"- not-dict"},
        {"apm.yml": b"name: x\nversion: 1.0.0", "apm.lock.yaml": b"files: []"},
        {"apm.yml": b"name: x\nversion: 1.0.0", "agents/a.agent.md": b"---\nunterminated"},
        {"apm.yml": b"name: x\nversion: 1.0.0", "agents/a.agent.md": b"---\n- list\n---\nbody"},
        {"apm.yml": b"name: x\nversion: 1.0.0", "agents/a.agent.md": b"---\n[bad\n---\nbody"},
        {
            "apm.yml": b"name: x\nversion: 1.0.0",
            "policies/p.policy.md": b"---\nuri_pattern: x\n---\nhi",
        },
        {
            "apm.yml": b"name: x\nversion: 1.0.0",
            "policies/p.policy.md": (
                b"---\nuri_pattern: jira://x\nconnector_scheme: jira\n"
                b"required_role: r\nsla_hours: abc\n---\nhi"
            ),
        },
        {"apm.yml": b"name: x\nversion: 1.0.0", "agents/bad.agent.md": b"\xff\xfe"},
        {"apm.yml": b"name: x\nversion: 1.0.0", "ontology/mechanisms/bad.star": b"def f(:\n"},
        {
            "apm.yml": b"name: x\nversion: 1.0.0",
            "ontology/mechanisms/novec.star": b"def evaluate(p):\n    return 1\n",
            "ontology/mechanisms/novec.yaml": yaml.safe_dump(
                {"passing_test_payload": {"a": 1}}
            ).encode(),
        },
        {
            "apm.yml": b"name: x\nversion: 1.0.0",
            "ontology/mechanisms/always_pass.star": (
                b"def evaluate(p):\n"
                b"    orcia_sys.assert_rule(rule_id='R', condition=True, message='ok')\n"
            ),
            "ontology/mechanisms/always_pass.yaml": yaml.safe_dump(
                {"failing_test_payload": {"a": 1}}
            ).encode(),
        },
    ],
)
def test_apm_codec_rejects_malformed_manifests_frontmatter_and_vectors(
    entries: dict[str, bytes],
) -> None:
    codec = ApmPackCodec()
    with pytest.raises(PackInvalidArchiveError):
        codec.decode_zip_bytes(_zip_of(entries))


def test_apm_codec_directory_errors_and_structured_synthesis(tmp_path: Path) -> None:
    assert _dump_frontmatter_md({}, "plain body") == b"plain body"

    codec = ApmPackCodec()
    with pytest.raises(PackInvalidArchiveError, match="does not exist"):
        codec.decode_directory(tmp_path / "missing")
    with pytest.raises(PackInvalidArchiveError, match="empty"):
        codec.decode_zip_bytes(b"")

    sym_dir = tmp_path / "sym-pack"
    sym_dir.mkdir()
    (sym_dir / "apm.yml").write_text("name: sym\nversion: 1.0.0\n", encoding="utf-8")
    (sym_dir / "evil.md").symlink_to(sym_dir / "apm.yml")
    with pytest.raises(PackInvalidArchiveError, match="Symbolic link"):
        codec.decode_directory(sym_dir)

    bundle = LoadedPackBundleV2(
        manifest=PackManifestV2(slug="synth", name="Synth", version="1.0.0"),
        archive_sha256=hashlib.sha256(b"fb").hexdigest(),
        manifest_yaml="name: synth\nversion: 1.0.0\nx-orcia:\n  slug: synth\n",
        agents=[PackAgentSpec(slug="a1", name="Agent 1", instructions_markdown="Be helpful.")],
        skills=[PackSkillSpec(slug="s1", name="Skill 1", instructions_markdown="Check DoR.")],
        instructions=[PackInstructionSpec(slug="i1", body_markdown="Use headings.")],
        vsm_specs=[
            ValueStreamMapSpec(
                id="vsm-synth",
                pack_id="orcia-pack-synth",
                slug="synth-vsm",
                title="Synth VSM",
                subtitle="Sub",
                source_note="Note",
                guiding_principle="Principle",
                phases=[{"id": "p1", "num": "01", "label": "Phase 1", "color_token": "blue"}],
                nodes=[
                    VsmStepNodeSpec(
                        num="01",
                        phase_id="p1",
                        title="Step 1",
                        linked_workflow_id="wf-synth",
                        input_actuel="in",
                        input_ia="in-ia",
                        output_actuel="out",
                        output_ia="out-ia",
                        actor_actuel="Human",
                        actor_ia="Agent",
                        validation_actuel="Manual",
                        validation_ia="Auto",
                    )
                ],
            )
        ],
        workflows=[
            WorkflowDefinitionV2(
                id="wf-synth",
                pack_id="orcia-pack-synth",
                slug="wf-synth",
                title="Synth Workflow",
                sub_steps=[
                    DeterministicSubStepSpec(
                        id="sub-1",
                        name="Sub 1",
                        short_label="Sub 1",
                        trigger_condition_label="Start",
                        role_description="Analyze",
                        instruction_prompt_or_ref="pack://synth/agents/a1",
                        output_description="Summary",
                        checkpoint_label="Approve",
                    )
                ],
            )
        ],
        glossary={"domain": "synth", "terms": []},
        dna_mechanisms=[
            PackDnaMechanismSpec(
                mechanism_slug="m1",
                name="Mechanism One",
                starlark_source=(
                    "def evaluate(p):\n"
                    "    orcia_sys.assert_rule(\n"
                    "        rule_id='R', condition=bool(p.get('ok')), message='ok'\n"
                    "    )\n"
                ),
                source_sha256=hashlib.sha256(b"m1").hexdigest(),
                input_schema={"type": "object", "required": ["ok"]},
                output_schema={"type": "object"},
                passing_test_payload={"ok": True},
                failing_test_payload={"ok": False},
            )
        ],
        gates_specs={"g1": {"id": "g1"}, "g2": "# Gate md"},
        policies=[
            PackPolicySpec(
                policy_key="p1",
                uri_pattern="jira://*",
                connector_scheme="jira",
                required_role="po",
            )
        ],
        help_articles=[PackHelpArticleSpec(slug="h1", lang="fr", title="H1", body_markdown="Aide")],
        raw_files={},
    )
    zipped = codec.encode_zip_bytes(bundle)
    with zipfile.ZipFile(io.BytesIO(zipped), "r") as zf:
        names = set(zf.namelist())
        assert "synth/apm.yml" in names
        assert "synth/apm.lock.yaml" in names
        assert "synth/workflows/vsm-synth-vsm.yaml" in names
        assert "synth/workflows/wf-synth.yaml" in names
        assert "synth/ontology/mechanisms/m1.star" in names
        assert "synth/ontology/mechanisms/m1.yaml" in names
        assert "synth/policies/p1.policy.md" in names
        assert "synth/help/fr/h1.md" in names
    decoded = codec.decode_zip_bytes(zipped)
    assert decoded.manifest.slug == "synth"
    assert len(decoded.vsm_specs) == 1
    assert len(decoded.workflows) == 1
    assert len(decoded.dna_mechanisms) == 1
    mech = decoded.dna_mechanisms[0]
    assert mech.mechanism_slug == "m1"
    assert mech.name == "Mechanism One"
    assert mech.input_schema == {"type": "object", "required": ["ok"]}
    assert mech.output_schema == {"type": "object"}
    assert mech.passing_test_payload == {"ok": True}
    assert mech.failing_test_payload == {"ok": False}

    pass_only_zip = _zip_of(
        {
            "apm.yml": b"name: passonly\nversion: 1.0.0\n",
            "ontology/mechanisms/m_pass.star": (
                b"def evaluate(p):\n"
                b"    orcia_sys.assert_rule(\n"
                b"        rule_id='R', condition=bool(p.get('ok')), message='ok'\n"
                b"    )\n"
            ),
            "ontology/mechanisms/m_pass.yaml": yaml.safe_dump(
                {"passing_test_payload": {"ok": True}}
            ).encode(),
        }
    )
    assert len(codec.decode_zip_bytes(pass_only_zip).dna_mechanisms) == 1


def test_seeder_emit_partial_where_pack_bundle_is_null() -> None:
    for spec in (
        CATALOG_ITEMS_UPSERT_SPEC,
        PERMISSION_BROKER_POLICIES_UPSERT_SPEC,
        HELP_ARTICLES_CATALOG_UPSERT_SPEC,
    ):
        sql = build_postgres_upsert_sql(spec)
        assert "WHERE pack_bundle_id IS NULL DO UPDATE SET" in sql

    with pytest.raises(ValueError, match="Unsafe conflict_where predicate"):
        build_postgres_upsert_sql(
            UpsertSpec("catalog_items", ("resource_id",), ("title",), conflict_where="a = 1; DROP")
        )

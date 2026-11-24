"""SDLC Catalog Format (`BMAD_PACK`), Indexers (`orcia.indexers`) & Assistant Templates."""

from __future__ import annotations

from typing import Any

from orcia_connectors._sdlc_template_locales import (
    SECURITY_MOD_KEYWORDS,
    get_sdlc_doc_vs_code_copy,
)
from orcia_core.catalog.bmad_adapter import BmadSkillPackAdapter
from orcia_core.kernel.enums import DEFAULT_LOCALE
from orcia_core.rag.indexer_and_rrf import DifferentiatedIncrementalIndexer
from orcia_core.rag.tripartite_and_freshness import TripartiteGraphAndFreshnessService
from orcia_kernel.context_ports import (
    AssistantWorkflowBlueprint,
    AssistantWorkflowTemplatePort,
    IndexerRegimeDescriptor,
    register_assistant_template,
    register_indexer_regime,
)


def get_bmad_pack_format_adapter() -> type[BmadSkillPackAdapter]:
    """Return `BMAD_PACK` catalog format adapter registered via `orcia.catalog_formats`."""
    return BmadSkillPackAdapter


def get_git_code_ast_indexer() -> Any:
    """Return `index_git_ast_and_code_graph` registered via `orcia.indexers`."""
    register_indexer_regime(
        IndexerRegimeDescriptor(
            regime_key="CODE_AST_GRAPH",
            display_name="Git AST & Code Property Graph Indexer",
            pack_name="orcia-pack-sdlc",
            handler=DifferentiatedIncrementalIndexer.index_git_ast_and_code_graph,
        )
    )
    return DifferentiatedIncrementalIndexer.index_git_ast_and_code_graph


def get_jira_hybrid_indexer() -> Any:
    """Return `index_jira_reference_issue` registered via `orcia.indexers`."""
    register_indexer_regime(
        IndexerRegimeDescriptor(
            regime_key="JIRA_HYBRID",
            display_name="Jira Hybrid Reference Issue Indexer",
            pack_name="orcia-pack-sdlc",
            handler=DifferentiatedIncrementalIndexer.index_jira_reference_issue,
        )
    )
    return DifferentiatedIncrementalIndexer.index_jira_reference_issue


def get_tripartite_graph_indexer() -> type[TripartiteGraphAndFreshnessService]:
    """Return `TripartiteGraphAndFreshnessService` registered via `orcia.indexers`."""
    register_indexer_regime(
        IndexerRegimeDescriptor(
            regime_key="TRIPARTITE_GRAPH",
            display_name="Confluence <-> Jira <-> Git Tripartite Graph Indexer",
            pack_name="orcia-pack-sdlc",
            handler=TripartiteGraphAndFreshnessService,
        )
    )
    return TripartiteGraphAndFreshnessService


class SdlcDocVsCodeAuditAssistantTemplate(AssistantWorkflowTemplatePort):
    """SDLC workflow blueprint for Arthur (`UJ-10`): compare Confluence/Jira to `git://` code."""

    @property
    def template_key(self) -> str:
        return "sdlc-doc-vs-code-audit"

    def matches_intent(self, prompt_lower: str) -> bool:
        sdlc_keywords = ("confluence", "jira", "git", "codebase", "documentation", "doc")
        return any(kw in prompt_lower for kw in sdlc_keywords)

    def build_blueprint(
        self,
        *,
        workspace_id: str,
        modification_instruction: str | None = None,
    ) -> AssistantWorkflowBlueprint:
        copy = get_sdlc_doc_vs_code_copy(DEFAULT_LOCALE)
        include_security_step = bool(
            modification_instruction
            and any(kw in modification_instruction.lower() for kw in SECURITY_MOD_KEYWORDS)
        )
        steps_list: list[dict[str, Any]] = [
            {
                "step_key": "step_1_scope_anchor",
                "title": copy["step1_title"],
                "step_type": "AGENT",
                "human_authored_required": True,
                "agent_uri": "orcia://catalog/agents/doc-audit-framer@1.0.0",
                "depends_on": [],
            },
            {
                "step_key": "step_2_tripartite_extract",
                "title": copy["step2_title"],
                "step_type": "SKILL",
                "human_authored_required": False,
                "skill_uri": "orcia://catalog/skills/tripartite-extractor@1.0.0",
                "depends_on": ["step_1_scope_anchor"],
            },
            {
                "step_key": "step_3_drift_qualification",
                "title": copy["step3_title"],
                "step_type": "AGENT",
                "human_authored_required": False,
                "agent_uri": "orcia://catalog/agents/drift-qualifier@1.0.0",
                "depends_on": ["step_2_tripartite_extract"],
            },
        ]
        extra_yaml = ""
        final_dep = "step_3_drift_qualification"
        if include_security_step:
            steps_list.append(
                {
                    "step_key": "step_4_security_compliance_check",
                    "title": copy["step4_title"],
                    "step_type": "SKILL",
                    "human_authored_required": False,
                    "skill_uri": "orcia://skills/security-compliance-check",
                    "depends_on": ["step_3_drift_qualification"],
                }
            )
            final_dep = "step_4_security_compliance_check"
            extra_yaml = (
                '\n  - step_key: "step_4_security_compliance_check"\n'
                f'    title: "{copy["step4_title"]}"\n'
                '    step_type: "SKILL"\n'
                '    skill_uri: "orcia://skills/security-compliance-check"\n'
                "    depends_on:\n"
                '      - "step_3_drift_qualification"\n'
                f'    instructions: "{copy["step4_instr"]}" '
            )

        steps_list.append(
            {
                "step_key": "step_final_verification",
                "title": copy["final_title"],
                "step_type": "POST_ACTION_VERIFICATION",
                "human_authored_required": False,
                "skill_uri": "orcia://skills/audit-report-verifier",
                "depends_on": [final_dep],
            }
        )

        wf_uri = (
            f"orcia://workflows/{workspace_id}-doc-vs-code-audit-v2"
            if include_security_step
            else f"orcia://workflows/{workspace_id}-doc-vs-code-audit"
        )
        version = "1.1.0" if include_security_step else "1.0.0"
        manifest_yaml = (
            f'uri: "{wf_uri}"\n'
            f'title: "{copy["wf_title"]}"\n'
            f'description: "{copy["wf_desc"]}"\n'
            f'version: "{version}"\n'
            'criticality: "STANDARD"\n'
            'execution_regime: "BACKGROUND_FAST_PATH"\n'
            'tie_break_policy: "PAUSE_AND_ESCALATE"\n'
            'mode: "standard"\n'
            'adaptive_gate_policy: "STANDARD"\n'
            "max_cost_usd: 12.0\n"
            "steps:\n"
            '  - step_key: "step_1_scope_anchor"\n'
            f'    title: "{copy["step1_title"]}"\n'
            '    step_type: "AGENT"\n'
            '    agent_uri: "orcia://agents/doc-audit-framer"\n'
            "    human_authored_required: true\n"
            f'    instructions: "{copy["step1_instr"]}"\n'
            '  - step_key: "step_2_tripartite_extract"\n'
            f'    title: "{copy["step2_title"]}"\n'
            '    step_type: "SKILL"\n'
            '    skill_uri: "orcia://skills/tripartite-extractor"\n'
            "    depends_on:\n"
            '      - "step_1_scope_anchor"\n'
            f'    instructions: "{copy["step2_instr"]}"\n'
            '  - step_key: "step_3_drift_qualification"\n'
            f'    title: "{copy["step3_title"]}"\n'
            '    step_type: "AGENT"\n'
            '    agent_uri: "orcia://agents/drift-qualifier"\n'
            "    depends_on:\n"
            '      - "step_2_tripartite_extract"\n'
            f'    instructions: "{copy["step3_instr"]}"{extra_yaml}\n'
            '  - step_key: "step_final_verification"\n'
            f'    title: "{copy["final_title"]}"\n'
            '    step_type: "POST_ACTION_VERIFICATION"\n'
            "    depends_on:\n"
            f'      - "{final_dep}"\n'
            "    verification_window_seconds: 30\n"
            f'    instructions: "{copy["final_instr"]}"\n'
        )
        return AssistantWorkflowBlueprint(
            template_key=self.template_key,
            workflow_uri=wf_uri,
            title=copy["wf_title"],
            description=copy["blueprint_desc"],
            default_execution_regime="BACKGROUND_FAST_PATH",
            manifest_yaml=manifest_yaml,
            steps_summary=tuple(steps_list),
        )


def create_sdlc_assistant_template_plugin() -> SdlcDocVsCodeAuditAssistantTemplate:
    """Instantiate and register `SdlcDocVsCodeAuditAssistantTemplate` (`Story 3.3`, `AD-20`)."""
    tpl = SdlcDocVsCodeAuditAssistantTemplate()
    register_assistant_template(tpl)
    return tpl

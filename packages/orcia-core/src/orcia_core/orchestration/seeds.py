"""Orchestration Setup Service factory (`DEC-SEED-01`, `AD-16`, `AD-20`).

Zero demo datasets or SDLC vocabulary inside `orcia_core.orchestration.seeds` (`AC-E0`, `AC-E2`).
Reference workflow manifests and templates live in `orcia_core.bootstrap.orchestration_seeds`.
"""

from __future__ import annotations

import importlib
from typing import Any

from orcia_core.catalog.cas_resolver import FederatedUriResolver
from orcia_core.ontology import OntologyGovernanceService, build_seeded_ontology_service
from orcia_core.orchestration.models import (
    ArtifactTemplateDefinition,
    ArtifactTemplateSectionSpec,
)
from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import UserIdentity


def _load_bootstrap_orchestration_seeds() -> Any:
    return importlib.import_module("orcia_core.bootstrap.orchestration_seeds")


def __getattr__(name: str) -> Any:
    if name in (
        "DEFAULT_ADR_TEMPLATE_SEED",
        "DEFAULT_CHILD_SUB_WORKFLOW_YAML",
        "DEFAULT_LEAF_SUB_WORKFLOW_YAML",
        "DEFAULT_ROOT_WORKFLOW_YAML",
    ):
        return getattr(_load_bootstrap_orchestration_seeds(), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def build_default_orchestration_setup_service(
    *,
    evaluator: MatrixPermissionEvaluator | None = None,
    resolver: FederatedUriResolver | None = None,
    ontology_service: OntologyGovernanceService | None = None,
) -> WorkflowOrchestrationSetupService:
    """Build `WorkflowOrchestrationSetupService` hydrated from `orcia_core.bootstrap` seeds."""
    eval_instance = evaluator or build_default_auth_and_org_service().evaluator
    res_instance = resolver or FederatedUriResolver()
    ont_instance = ontology_service or build_seeded_ontology_service()
    boot = _load_bootstrap_orchestration_seeds()
    seed_tpl = boot.DEFAULT_ADR_TEMPLATE_SEED
    default_template = ArtifactTemplateDefinition(
        template_key=seed_tpl.template_key,
        uri=seed_tpl.uri,
        title=seed_tpl.title,
        version=seed_tpl.version,
        description=seed_tpl.description,
        required_variables=seed_tpl.required_variables,
        sections=tuple(
            ArtifactTemplateSectionSpec(
                section_key=sec.section_key,
                title=sec.title,
                markdown_body_template=sec.markdown_body_template,
                ontology_concept_term=sec.ontology_concept_term,
                human_authored_required=sec.human_authored_required,
                mandatory=sec.mandatory,
                max_words_chunk=sec.max_words_chunk,
            )
            for sec in seed_tpl.sections
        ),
    )

    svc = WorkflowOrchestrationSetupService(
        evaluator=eval_instance,
        resolver=res_instance,
        ontology_service=ont_instance,
        templates=(default_template,),
    )
    for raw_yaml in (
        boot.DEFAULT_LEAF_SUB_WORKFLOW_YAML,
        boot.DEFAULT_CHILD_SUB_WORKFLOW_YAML,
        boot.DEFAULT_ROOT_WORKFLOW_YAML,
    ):
        rep = svc.validate_workflow_manifest(
            raw_yaml, workspace_id="0192c4e0-0000-7000-8000-000000000201", raise_on_error=True
        )
        assert rep.workflow is not None
        svc.register_validated_workflow(rep.workflow)

    lead_user = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000603",
        email="marc.lead@orcia.io",
        display_name="Marc (Chef d'Équipe / Tech Lead)",
        auth_mode="HYBRID",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )
    svc.instantiate_workflow_run(
        lead_user,
        workflow_uri="orcia://workflows/claims-engineering-delivery",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
    )
    return svc


__all__ = [
    "build_default_orchestration_setup_service",
]

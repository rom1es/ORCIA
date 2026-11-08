---
document_type: BACKEND_TECHNICAL_SPECIFICATION
epic_id: EPIC-09
version: "2.0.0"
target_packages:
  - "packages/orcia-core/src/orcia_core/workflows/"
  - "packages/orcia-pack-sdlc/src/orcia_pack_sdlc/seeds/"
  - "apps/api/src/orcia_api/routers/workflows.py"
  - "apps/worker/src/orcia_worker/executors/"
---

# Architecture Backend & Modèles de Données (v2 Assainie)

Cette spécification intègre les 6 arbitrages architecturaux :
1. **Zéro fuite SDLC dans `packages/orcia-core`** : tous les schémas Core sont 100 % agnostiques.
2. **Séparation `ValueStreamMapSpec` (Cartographie Macro) vs `WorkflowDefinitionV2` (Workflow DBOS Unitaire)**.
3. **Remplacement de l'orchestrateur LLM par `DeterministicSubStep`** piloté par DBOS.
4. **Support explicite de `ExecutionMode.NATIVE_ORCIA` et `ExecutionMode.EXTERNAL_DELEGATED_GATE`**.
5. **Application stricte du `ClaimCheckPointer` (SeaweedFS S3)** pour interdire tout payload $> 4\text{ Ko}$ dans PostgreSQL.
6. **Clés d'idempotence indexées par `(run_id, node_id, iteration_index)`** pour supporter les boucles de retour sans effet de cache.

---

## 1. Pointeur Claim-Check & Schémas Agnostiques (`packages/orcia-core/src/orcia_core/workflows/schemas_v2.py`)

```python
from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, Field


class WorkflowLifecycleStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED_WHAT_IF = "validated_what_if"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ExecutionMode(StrEnum):
    NATIVE_ORCIA = "native_orcia"  # Exécuté par apps/worker + LiteLLM + Sandbox ORCIA
    EXTERNAL_DELEGATED_GATE = (
        "external_delegated"  # Exécuté hors ORCIA (IDE/SaaS) ; ORCIA = Context MCP + Gatekeeper
    )


class EffortLevel(StrEnum):
    DEFAULT = "default"
    LOW = "low"  # Rapide
    MEDIUM = "medium"  # Équilibré
    HIGH = "high"  # Approfondi


class ControlMaturityStatus(StrEnum):
    IN_PLACE = "place"  # En place (bloquant)
    TO_ADD = "ajouter"  # À ajouter (warning non-bloquant)
    HYPOTHESIS = "hypothese"  # Hypothèse à valider


class GateExecutionStrategy(StrEnum):
    FAIL_FAST = "fail_fast"  # Arrêt immédiat au 1er KO (ADR-06)
    AGGREGATED_AUDIT = "aggregated_audit"  # Exécute tout et agrège la matrice d'impact


class ClaimCheckPointer(BaseModel):
    """Référence immuable vers un artefact lourd stocké dans SeaweedFS (S3) — ADR-02 / ADR-10."""

    s3_uri: str = Field(..., pattern=r"^s3://orcia-artifacts/.+$")
    sha256: str = Field(..., min_length=64, max_length=64)
    byte_size: int = Field(..., ge=0)
    mime_type: str = "text/markdown"


class ContractParameter(BaseModel):
    """Paramètre d'entrée générique. Utilise catalog_entity_type pour vérifier l'existence dans le graphe sans couplage SDLC."""

    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    label: str
    scalar_type: Literal["string", "integer", "boolean", "enum", "catalog_ref"] = "string"
    catalog_entity_uri_pattern: str | None = Field(
        default=None,
        description="Ex: catalog://issue_tracker/work_item/{key} ou catalog://hr_system/employee/{id}",
    )
    default_value: str | None = None
    required: bool = True


class WorkflowContract(BaseModel):
    parameters: list[ContractParameter] = Field(default_factory=list)
    required_markdown_sections: list[str] = Field(default_factory=list)
    output_schema_uri: str | None = Field(
        default=None, description="Ex: pack://sdlc/schemas/architecture-study-v1.json"
    )


class DeterministicControlSpec(BaseModel):
    id: str
    name: str
    short_label: str
    status: ControlMaturityStatus = ControlMaturityStatus.IN_PLACE
    runner_plugin_id: str = Field(
        ..., description="ID du runner dans le Pack Registry ou Sandbox Core"
    )
    verifies_description: str
    on_ko_behavior: str
    max_self_heal_retries: int = Field(default=3, ge=0, le=5)
    config: dict[str, Any] = Field(default_factory=dict)


class NonDeterministicControlSpec(BaseModel):
    id: str
    name: str
    short_label: str
    status: ControlMaturityStatus = ControlMaturityStatus.IN_PLACE
    evaluator_type: Literal["adversarial_agent", "custom_agent_evaluator", "self_check"]
    agent_ref: str = Field(..., description="Référence d'agent dans le Pack Registry")
    model_override: str | None = Field(
        default=None, description="Recommandé : famille de modèle distincte du producteur"
    )
    risk_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    verifies_description: str
    hypothesis_note: str | None = None
    on_ko_behavior: str


class StepControlsPipeline(BaseModel):
    delegated_to_step_num: str | None = None
    delegation_note: str | None = None
    strategy: GateExecutionStrategy = GateExecutionStrategy.FAIL_FAST
    sandbox_dry_run: bool = True
    deterministic: list[DeterministicControlSpec] = Field(default_factory=list)
    non_deterministic: list[NonDeterministicControlSpec] = Field(default_factory=list)


class DeterministicSubStepSpec(BaseModel):
    """Sous-étape orchestrée par DBOS (remplace l'anti-pattern de l'Agent Orchestrateur lisant le chat)."""

    id: str
    name: str
    short_label: str
    enabled: bool = True  # False => SKIPPED par DBOS
    step_executor_type: Literal["agent_executor", "program_executor"] = "agent_executor"
    trigger_condition_label: str
    role_description: str
    instruction_prompt_or_ref: str
    toolbox_mcp_permissions: list[dict[str, str]] = Field(default_factory=list)
    skill_refs: list[str] = Field(default_factory=list)
    output_description: str
    # Verrou de transition géré par la machine à états DBOS
    requires_human_checkpoint: bool = True
    checkpoint_label: str = Field(..., description="Ex: Validation de la Qualification")
    approver_rbac_role: str = Field(default="workspace:member")
    write_preview_required: bool = Field(
        default=False,
        description="Si True, le Permission Broker bloque toute écriture MCP jusqu'à validation humaine de l'aperçu",
    )


class WorkflowDefinitionV2(BaseModel):
    """Workflow exécutable unitaire et borné sous DBOS (rattachable à une étape de la VSM)."""

    id: str
    slug: str
    title: str
    version: str = "1.0.0"
    status: WorkflowLifecycleStatus = WorkflowLifecycleStatus.DRAFT
    pack_id: str
    execution_mode: ExecutionMode = ExecutionMode.NATIVE_ORCIA
    external_tool_label: str | None = Field(
        default=None,
        description="Informationnel si EXTERNAL_DELEGATED_GATE (ex: IDE / SaaS externe)",
    )
    external_completion_event: str | None = Field(
        default=None,
        description="Événement Outbox déclenchant le sas de Gates en sortie d'outil externe",
    )
    model_override: str = "team_default"
    effort: EffortLevel = EffortLevel.DEFAULT
    global_system_prompt_or_ref: str | None = None
    guardrails: list[str] = Field(default_factory=list)
    knowledge_feedback_target_agent: str | None = None
    contract: WorkflowContract = Field(default_factory=WorkflowContract)
    sub_steps: list[DeterministicSubStepSpec] = Field(default_factory=list)
    controls: StepControlsPipeline = Field(default_factory=StepControlsPipeline)
```

---

## 2. Schéma de Chaîne de Valeur Macro-VSM (`ValueStreamMapSpec`)

Ce second schéma modélise la cartographie de bout en bout (les 4 phases, 11 étapes, 5 points de passage et boucles de retour du POC) et lie chaque étape outillée à son `workflow_definition_id` unitaire :

```python
class ReturnLoopSpec(BaseModel):
    target_step_num: str
    is_primary: bool = False
    when_condition: str
    remarks_carried: str | None = None
    behavior_actuel: str | None = None
    behavior_ia: str | None = None
    reentry_mode: str = "corrections"
    target_sub_step_id: str | None = None


class VsmStepNodeSpec(BaseModel):
    node_type: Literal["step"] = "step"
    num: str
    phase_id: str
    title: str
    badge_label: str | None = None
    opportunity_codes: list[str] = Field(default_factory=list)
    # Lien vers le Workflow exécutable borné (None si étape 100% manuelle comme 05, 07, 11)
    linked_workflow_id: str | None = None
    input_actuel: str
    input_ia: str
    output_actuel: str
    output_ia: str
    output_ia_short: str | None = None
    actor_actuel: str
    actor_ia: str
    actor_ia_short: str | None = None
    human_co_author: str | None = None
    tools_actuel: list[str] = Field(default_factory=list)
    tools_ia: list[str] = Field(default_factory=list)
    validation_actuel: str
    validation_ia: str
    validation_ia_short: str | None = None
    humans_actuel: list[dict[str, str]] = Field(default_factory=list)
    humans_ia: list[dict[str, str]] = Field(default_factory=list)
    interactions_note: str | None = None
    interactions_actuel: list[dict[str, str]] = Field(default_factory=list)
    interactions_ia: list[dict[str, str]] = Field(default_factory=list)
    detail_markdown: str = ""


class VsmPassageNodeSpec(BaseModel):
    node_type: Literal["passage"] = "passage"
    id: str
    phase_id: str
    short_title: str
    title: str
    description: str
    approver_rbac_roles: list[str] = Field(default_factory=list)
    sla_timeout_hours: int = 72
    human_mandatory_rationale: str
    ai_assistable_scope: str
    delegable_long_term: str
    note: str | None = None
    return_loops: list[ReturnLoopSpec] = Field(default_factory=list)


class ValueStreamMapSpec(BaseModel):
    id: str
    slug: str
    title: str
    subtitle: str
    source_note: str
    guiding_principle: str
    pack_id: str
    phases: list[dict[str, str]]
    opportunities: dict[str, dict[str, str]] = Field(default_factory=dict)
    nodes: list[VsmStepNodeSpec | VsmPassageNodeSpec]
```

---

## 3. Orchestration Durable DBOS avec Claim-Check S3 & Compteur d'Itération (`apps/worker`)

```python
@DBOS.workflow()
def run_bounded_workflow_v2(
    run_id: str,
    workflow_def: WorkflowDefinitionV2,
    inputs: dict[str, Any],
    initial_iteration: int = 0,
    reentry_remarks: str | None = None,
    start_sub_step_id: str | None = None,
) -> ClaimCheckPointer:
    """Exécute un workflow unitaire borné sous DBOS en respectant strictement ADR-01, ADR-02, ADR-04 et ADR-06."""
    validate_contract_inputs_step(run_id, workflow_def.contract, inputs)

    iteration = initial_iteration
    current_artifact_ptr: ClaimCheckPointer | None = None
    sub_steps = [s for s in workflow_def.sub_steps if s.enabled]

    idx = 0
    if start_sub_step_id:
        idx = next((i for i, s in enumerate(sub_steps) if s.id == start_sub_step_id), 0)

    while idx < len(sub_steps):
        sub_step = sub_steps[idx]
        # Clé d'idempotence incluant l'itération pour éviter le cache lors d'une boucle de retour
        step_execution_key = f"{run_id}:{sub_step.id}:iter-{iteration}"

        if workflow_def.execution_mode == ExecutionMode.NATIVE_ORCIA:
            current_artifact_ptr = execute_native_sub_step_with_claim_check(
                idempotency_key=step_execution_key,
                sub_step=sub_step,
                inputs=inputs,
                previous_ptr=current_artifact_ptr,
                reentry_remarks=reentry_remarks,
            )
        else:
            # Mode EXTERNAL_DELEGATED_GATE : publie le contexte MCP et attend le livrable externe (PR / Doc)
            prepare_external_context_bundle_step(
                step_execution_key, sub_step, inputs, current_artifact_ptr
            )
            ext_event = DBOS.recv(
                topic=f"external_artifact:{run_id}:{sub_step.id}", timeout_seconds=604800
            )
            current_artifact_ptr = ClaimCheckPointer.model_validate(ext_event["artifact_pointer"])

        # Jalon de validation humaine inter-sous-étapes (géré par DBOS, jamais par le prompt LLM)
        if sub_step.requires_human_checkpoint:
            signal = DBOS.recv(
                topic=f"sub_step_checkpoint:{run_id}:{sub_step.id}", timeout_seconds=259200
            )
            if signal["action"] == "AMEND_DIFF":
                # L'amendement humain a déjà été écrit dans SeaweedFS par l'API avec un nouveau SHA-256
                current_artifact_ptr = ClaimCheckPointer.model_validate(signal["amended_pointer"])
                idx += 1
            elif signal["action"] == "REJECT_RETRY_SUBSTEP":
                iteration += 1
                reentry_remarks = signal["remarks"]
                continue  # Réexécute la sous-étape courante avec une nouvelle step_execution_key
            elif signal["action"] == "APPROVE":
                reentry_remarks = None
                idx += 1
        else:
            idx += 1

    # Pipeline final de Gates sur l'artefact produit (Déterministes Auto-Heal 3x -> Non-Déterministes)
    gate_report_ptr, requires_anchor = run_gates_pipeline_with_self_heal(
        run_id=run_id,
        iteration=iteration,
        workflow_def=workflow_def,
        artifact_ptr=current_artifact_ptr,
    )

    if requires_anchor:
        anchor_decision = DBOS.recv(topic=f"anchor_card:{run_id}", timeout_seconds=259200)
        if anchor_decision["action"] == "AMEND_DIFF":
            current_artifact_ptr = ClaimCheckPointer.model_validate(
                anchor_decision["amended_pointer"]
            )
        elif anchor_decision["action"] == "REJECT_AND_LOOP":
            iteration += 1
            reentry_remarks = anchor_decision["remarks"]
            target_sub = anchor_decision.get("target_sub_step_id") or sub_steps[0].id
            return run_bounded_workflow_v2(
                run_id=run_id,
                workflow_def=workflow_def,
                inputs=inputs,
                initial_iteration=iteration,
                reentry_remarks=reentry_remarks,
                start_sub_step_id=target_sub,
            )

    return current_artifact_ptr
```

---


---
document_type: BACKEND_TECHNICAL_SPECIFICATION
epic_id: EPIC-09_AND_EPIC-10
version: "3.0.0"
target_packages:
  - "packages/orcia-core/src/orcia_core/"
  - "packages/orcia-connectors/src/orcia_connectors/"
  - "packs/sdlc/"
  - "packs/orcia-docs/"
  - "apps/api/src/orcia_api/routers/"
  - "apps/worker/src/orcia_worker/"
---

# Architecture Backend Unifiée (v3) — Core, Connecteurs & Packs Déclaratifs

Cette spécification consolide les arbitrages des **Epics 9 et 10** autour d'une architecture simplifiée à 3 piliers :
1. **`packages/orcia-core`** : Moteur d'exécution durable DBOS, stockage `ClaimCheckPointer` (SeaweedFS S3), *Permission Broker*, les **4 runners déterministes génériques de Gates** et le chargeur **`DeclarativePackLoader`**.
2. **`packages/orcia-connectors`** : Bibliothèque unique de tous les connecteurs SI et clients MCP (Jira, Confluence, Git, SQL) obéissant au contrat strict à 4 méthodes (`healthcheck`, `read`, `preview_write`, `execute_write`).
3. **`packs/<domaine>/`** : Bundles métiers **100 % déclaratifs (YAML + Markdown, zéro code Python/React)** situés à la racine du monorepo (`packs/sdlc/`, `packs/orcia-docs/`), remplaçant définitivement `packages/orcia-pack-sdlc` et `packages/orcia-pack-builder`.

---

## 1. Contrat Unique des Connecteurs (`packages/orcia-connectors/src/orcia_connectors/protocol.py`)

Tous les connecteurs d'entreprise résident dans `packages/orcia-connectors` et implémentent ce protocole unique gouverné par le *Permission Broker* :

```python
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class ConnectorHealthStatus(BaseModel):
    connector_type: str = Field(..., description="Ex: mcp:atlassian-jira, mcp:git-provider")
    ok: bool
    latency_ms: int
    error_message: str | None = None


class WritePreviewCard(BaseModel):
    """Carte de prévisualisation retournée avant toute écriture externe (Write-Preview Gate)."""
    preview_id: str
    connector_type: str
    target_resource_uri: str
    action_summary: str
    diff_or_payload_preview: dict[str, Any]
     payload_sha256: str


class SignedApprovalToken(BaseModel):
    """Jeton émis par le Permission Broker après validation humaine de la WritePreviewCard."""
    preview_id: str
    approver_user_id: str
    approved_at_utc: str
    payload_sha256: str
    broker_signature: str


@runtime_checkable
class OrciaConnectorProtocol(Protocol):
    connector_type: str

    async def healthcheck(self) -> ConnectorHealthStatus:
        """Vérifie la connectivité réseau, les certificats mTLS et la validité du token."""
        ...

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Lecture seule (ticket, page, fichier Git, requête JQL/CQL/SQL)."""
        ...

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        """Simule et prépare l'écriture sans modifier l'outil externe."""
        ...

    async def execute_write(
        self, approval_token: SignedApprovalToken, action: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Exécute l'écriture externe uniquement si la signature du Permission Broker correspond au SHA-256."""
        ...
```

---

## 2. Les 4 Runners Déterministes Génériques (`packages/orcia-core/src/orcia_core/workflows/gates/runners.py`)

Pour que les Packs restent 100 % déclaratifs (YAML + Markdown), `orcia-core` fournit **4 runners déterministes génériques** paramétrables en YAML depuis n'importe quel fichier `packs/<domaine>/gates/*.yaml` :

| ID Runner (`runner_plugin_id`) | Rôle & Vérifications effectuées en Sandbox | Paramètres YAML attendus (`config`) |
| :--- | :--- | :--- |
| **`markdown_contract_runner`** | Vérifie la présence des sections Markdown imposées, la longueur min/max par section/champ, la validité syntaxique des blocs Mermaid et l'absence de marqueurs interdits ou de PII. | `required_headings: list[str]`, `min_chars_per_section: int`, `require_mermaid_blocks: bool`, `forbid_patterns: list[str]` |
| **`json_schema_runner`** | Valide la sortie structurée d'une étape ou d'un outil contre un schéma JSON Schema / OpenAPI du Pack. | `schema_path: str`, `strict_additional_properties: bool` |
| **`cli_sandbox_runner`** | Exécute une commande déterministe isolée sans réseau dans `infra/sandbox` (`ruff`, `spectral`, `pytest`, `oas-diff`). | `command: list[str]`, `expected_exit_code: int`, `timeout_seconds: int` |
| **`catalog_invariant_runner`** | Vérifie dans PostgreSQL que toutes les URI citées par l'agent (`catalog://...`) existent réellement et respectent la classification C0–C2. | `allowed_classifications: list[str]`, `require_existing_entities: bool` |

---

## 3. Chargeur de Packs Déclaratifs (`packages/orcia-core/src/orcia_core/packs/loader.py`)

```python
from pathlib import Path
import hashlib
import yaml
from pydantic import BaseModel, Field
from orcia_core.workflows.schemas_v2 import ValueStreamMapSpec, WorkflowDefinitionV2


class RequiredConnectorSpec(BaseModel):
    connector_type: str = Field(..., description="Ex: mcp:atlassian-jira")
    required_scopes: list[str] = Field(default_factory=lambda: ["read"])
    used_for: str


class QuickActionSpec(BaseModel):
    id: str
    label: str
    target_workflow_slug: str
    icon: str = "play"


class DeclarativePackManifest(BaseModel):
    """Schéma du fichier packs/<pack_id>/pack.yaml (100 % déclaratif)."""

    id: str
    slug: str
    name: str
    version: str
    description: str
    rbac_namespace: str = Field(..., description="Ex: sdlc, hr, finance, docs")
    required_connectors: list[RequiredConnectorSpec] = Field(default_factory=list)
    quick_actions: list[QuickActionSpec] = Field(default_factory=list)


class LoadedPackBundle(BaseModel):
    manifest: DeclarativePackManifest
    bundle_sha256: str
    glossary: dict[str, Any]
    agents_markdown: dict[str, str]
    skills_markdown: dict[str, str]
    gates_specs: dict[str, Any]
    vsm_specs: list[ValueStreamMapSpec]
    workflows: list[WorkflowDefinitionV2]


class DeclarativePackLoader:
    """Charge à chaud les dossiers `packs/<domaine>/` sans aucun import Python dynamique."""

    def __init__(self, packs_root_dir: Path) -> None:
        self.packs_root_dir = packs_root_dir

    def load_all_packs(self) -> dict[str, LoadedPackBundle]:
        bundles: dict[str, LoadedPackBundle] = {}
        for pack_dir in sorted(self.packs_root_dir.iterdir()):
            manifest_path = pack_dir / "pack.yaml"
            if pack_dir.is_dir() and manifest_path.exists():
                bundle = self.load_single_pack(pack_dir)
                bundles[bundle.manifest.id] = bundle
        return bundles

    def load_single_pack(self, pack_dir: Path) -> LoadedPackBundle:
        manifest_raw = yaml.safe_load((pack_dir / "pack.yaml").read_text(encoding="utf-8"))
        manifest = DeclarativePackManifest.model_validate(manifest_raw)

        hasher = hashlib.sha256()
        for file_path in sorted(pack_dir.rglob("*")):
            if file_path.is_file():
                hasher.update(file_path.read_bytes())

        glossary = {}
        if (pack_dir / "glossary.yaml").exists():
            glossary = (
                yaml.safe_load((pack_dir / "glossary.yaml").read_text(encoding="utf-8")) or {}
            )

        agents_md = (
            {
                p.stem: p.read_text(encoding="utf-8")
                for p in sorted((pack_dir / "agents").glob("*.md"))
            }
            if (pack_dir / "agents").exists()
            else {}
        )

        skills_md = (
            {
                p.stem: p.read_text(encoding="utf-8")
                for p in sorted((pack_dir / "skills").glob("*.md"))
            }
            if (pack_dir / "skills").exists()
            else {}
        )

        gates_specs = (
            {
                p.stem: yaml.safe_load(p.read_text(encoding="utf-8"))
                if p.suffix == ".yaml"
                else p.read_text(encoding="utf-8")
                for p in sorted((pack_dir / "gates").glob("*"))
            }
            if (pack_dir / "gates").exists()
            else {}
        )

        vsm_specs: list[ValueStreamMapSpec] = []
        workflows: list[WorkflowDefinitionV2] = []
        if (pack_dir / "workflows").exists():
            for wf_file in sorted((pack_dir / "workflows").glob("*.yaml")):
                data = yaml.safe_load(wf_file.read_text(encoding="utf-8"))
                if wf_file.name.startswith("vsm-"):
                    vsm_specs.append(ValueStreamMapSpec.model_validate(data))
                else:
                    workflows.append(WorkflowDefinitionV2.model_validate(data))

        return LoadedPackBundle(
            manifest=manifest,
            bundle_sha256=hasher.hexdigest(),
            glossary=glossary,
            agents_markdown=agents_md,
            skills_markdown=skills_md,
            gates_specs=gates_specs,
            vsm_specs=vsm_specs,
            workflows=workflows,
        )
```

---

## 4. Table des Routes FastAPI (`apps/api/src/orcia_api/routers/workflows.py` & `packs.py`)

| Méthode & Route | Permission RBAC | Description |
| :--- | :--- | :--- |
| `GET /api/v1/packs` | `workspace:read` | Liste les Packs déclaratifs chargés depuis `packs/`, leur `bundle_sha256` et le statut `healthcheck()` de leurs `required_connectors` via `orcia-connectors`. |
| `POST /api/v1/packs/export/{workspace_id}` | `admin:packs:manage` | Exporte les Agents, Skills, Gates et Workflows de l'espace courant sous forme d'archive déclarative `.zip` (`pack.yaml` + dossiers). |
| `GET /api/v1/vsm` | `workflows:read` | Liste les Cartographies de Chaîne de Valeur (`ValueStreamMapSpec`) du Pack actif. |
| `GET /api/v1/workflows/v2` | `workflows:read` | Liste les Workflows unitaires exécutables (`WorkflowDefinitionV2`) avec leurs compteurs de sous-étapes et de Gates. |
| `PUT /api/v1/workflows/v2/{id}` | `workflows:write` | Sauvegarde un brouillon (ou crée automatiquement un fork `vX.Y.Z-draft` si le workflow d'origine est `PUBLISHED`). |
| `POST /api/v1/workflows/v2/{id}/what-if` | `workflows:write` | Exécute le workflow dans la Sandbox éphémère (aucun `execute_write` sur `orcia-connectors`) et retourne la matrice `ImpactAssessmentResult`. |
| `POST /api/v1/workflows/v2/{id}/runs` | `workflows:trigger` | Démarre une exécution durable DBOS (`run_bounded_workflow_v2`) avec stockage `ClaimCheckPointer` dans SeaweedFS. |
| `POST /api/v1/runs/{run_id}/hitl-signal` | Rôle de l'étape | Envoie l'un des signaux humains : réponse questionnaire, choix d'option, validation de `WritePreviewCard`, ou l'une des 4 actions souveraines d'Anchor Card (`APPROVE`, `AMEND_DIFF`, `REJECT_AND_LOOP`, `SUSPEND_SLA`). |

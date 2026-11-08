---
document_type: ANTIGRAVITY_IMPLEMENTATION_TASKS
epic_id: EPIC-09_AND_EPIC-10
version: "3.0.0"
execution_engine: "Antigravity / bmad-build"
---

# Plan d'Exécution Unifié des Tâches pour Antigravity (v3)

Ce plan fusionne la **simplification des packages (Epic 10)** et le **Process Studio v2 (Epic 9)** en **8 tâches atomiques ordonnées (`TASK-01` à `TASK-08`)** pour éviter tout travail jetable.

---

## TASK-01 : Création de `packages/orcia-connectors` & Fusion `orcia-kernel` dans `orcia-core`
* **Cible :** `packages/orcia-connectors/`, `packages/orcia-core/`
* **Actions :**
  1. Créer le package `packages/orcia-connectors` (`pyproject.toml`, `src/orcia_connectors/protocol.py`) définissant `OrciaConnectorProtocol` avec les 4 méthodes obligatoires : `healthcheck()`, `read()`, `preview_write()`, `execute_write()`.
  2. Déplacer dans `packages/orcia-connectors/src/orcia_connectors/adapters/` tous les connecteurs techniques : `atlassian_jira.py`, `atlassian_confluence.py`, `git_provider.py`, `sql_readonly.py` et `mcp_client_bridge.py`.
  3. Intégrer le contenu de `packages/orcia-kernel` dans `packages/orcia-core/src/orcia_core/kernel/` et mettre à jour les imports pour n'avoir plus que 2 packages Python dans `packages/` : `orcia-core` et `orcia-connectors`.
* **Tests obligatoires :**
  * `tests/unit/connectors/test_connector_protocol_and_write_preview.py` : Vérifie qu'aucun appel `execute_write()` ne passe sans un `SignedApprovalToken` valide du *Permission Broker*.

---

## TASK-02 : Chargeur `DeclarativePackLoader`, Stockage S3 Claim-Check & Schémas VSM/Workflow v2 dans `orcia-core`
* **Cible :** `packages/orcia-core/src/orcia_core/packs/`, `packages/orcia-core/src/orcia_core/workflows/`, `infra/migrations/`
* **Actions :**
  1. Créer `packages/orcia-core/src/orcia_core/workflows/schemas_v2.py` contenant `ClaimCheckPointer`, `ValueStreamMapSpec` et `WorkflowDefinitionV2` (100 % agnostiques du domaine SDLC).
  2. Créer `packages/orcia-core/src/orcia_core/storage/claim_check.py` pour persister tout livrable ou diff $> 4\text{ Ko}$ dans **SeaweedFS (S3)** avec empreinte `SHA-256`.
  3. Créer `packages/orcia-core/src/orcia_core/packs/loader.py` (`DeclarativePackLoader` et `PackExporter`) capable de charger à chaud les dossiers `packs/<domaine>/` et d'exporter un espace de travail en archive `.zip` de Pack.
  4. Créer la migration Alembic `20261108_0910_declarative_packs_and_workflows_v2.py`.
* **Tests obligatoires :**
  * `tests/unit/core/test_core_domain_isolation.py` : Vérifie par analyse AST/regex qu'aucun fichier de `packages/orcia-core` ne contient les mots `jira`, `confluence`, `git_branch`, `wsjf`, `rovo`, `copilot`, `safe`.

---

## TASK-03 : Création des Packs Déclaratifs `packs/sdlc/` et `packs/orcia-docs/` & Suppression des anciens packages
* **Cible :** `packs/sdlc/`, `packs/orcia-docs/`, suppression de `packages/orcia-pack-sdlc/` et `packages/orcia-pack-builder/`
* **Actions :**
  1. Créer le dossier déclaratif `packs/sdlc/` contenant :
     * `pack.yaml` (déclarant `required_connectors: ["mcp:atlassian-jira", "mcp:atlassian-confluence", "mcp:git-provider"]`).
     * `glossary.yaml` (termes métiers et entités ontologiques).
     * `agents/` (`orchestrateur-produit.md`, `crl-etude-archi.md`, `agent-us.md`, `crl-socle-generateur.md`).
     * `skills/` (`qualification-besoin.md`, `redaction-prd-wsjf.md`, `decoupe-us-invest.md`, `diagrammes-mermaid.md`).
     * `gates/` (`det-prd-fields.yaml`, `det-de-14-points.yaml`, `det-invest-dor.yaml`, `hunter-prd-challenger.md`, `hunter-archi-contradicteur.md`, `hunter-us-controller.md`).
     * `workflows/` :
       * `vsm-mon-compte-idea-to-prod.yaml` (la Chaîne de Valeur complète de 11 étapes, 4 phases, 5 points de passage humains, 8 boucles de retour et opportunités `P1`, `P2`, `P3` extraite de `Workflow agentique 2.html`).
       * `wf-01-qualification-prd.yaml` (3 sous-étapes déterministes DBOS).
       * `wf-03-etude-architecture.yaml` (4 sous-étapes déterministes DBOS).
       * `wf-06-decoupe-us.yaml` (5 sous-étapes déterministes DBOS).
       * `wf-08-dev-external-gate.yaml` (en mode `EXTERNAL_DELEGATED_GATE`).
  2. Créer le dossier déclaratif `packs/orcia-docs/` (remplaçant `orcia-pack-builder` pour la génération documentaire avec `@Redacteur-Documentation-Orcia`).
  3. Supprimer définitivement `packages/orcia-pack-sdlc/`, `packages/orcia-pack-builder/` et `packages/orcia-kernel/` et mettre à jour le `pyproject.toml` racine.
* **Tests obligatoires :**
  * `tests/unit/packs/test_declarative_packs_loading.py` : Vérifie que `DeclarativePackLoader` charge sans erreur `packs/sdlc/` et `packs/orcia-docs/` et valide 100 % des schémas Pydantic.

---

## TASK-04 : Les 4 Runners Déterministes Génériques de Gates & Pipeline Fail-Fast / Auto-Heal (3x)
* **Cible :** `packages/orcia-core/src/orcia_core/workflows/gates/`
* **Actions :**
  1. Implémenter dans `orcia-core` les 4 runners génériques (`markdown_contract_runner`, `json_schema_runner`, `cli_sandbox_runner`, `catalog_invariant_runner`).
  2. Implémenter `GatePipelineExecutor` respectant l'inviolabilité préalable (ADR-06) : exécution des contrôles déterministes en premier, boucle d'auto-remédiation bornée (`max_self_heal_retries = 3`), puis exécution des contrôles probabilistes (*Hunters*) uniquement si les contrôles déterministes sont à 100 % `NOMINAL`.
* **Tests obligatoires :** `tests/unit/core/test_generic_gate_runners_and_auto_heal.py`.

---

## TASK-05 : Worker DBOS (`run_bounded_workflow_v2`), Mode Sas Externe & Routes FastAPI
* **Cible :** `apps/worker/src/orcia_worker/workflows/`, `apps/api/src/orcia_api/routers/`
* **Actions :**
  1. Implémenter le workflow durable `run_bounded_workflow_v2` utilisant des clés d'idempotence indexées par itération `f"{run_id}:{sub_step.id}:iter-{iteration}"`.
  2. Gérer les deux modes d'exécution : `NATIVE_ORCIA` et `EXTERNAL_DELEGATED_GATE` (exposition du paquet de contexte MCP + attente de l'événement externe pour déclencher le sas de Gates).
  3. Exposer les routes REST/SSE dans `apps/api/src/orcia_api/routers/workflows.py` et `packs.py` (incluant le healthcheck des `required_connectors` et l'export d'espace en Pack `.zip`).
* **Tests obligatoires :** `tests/integration/api/test_dbos_return_loops_and_claim_check.py`.

---

## TASK-06 : Frontend — Écran `/settings/packs` Simplifié & Hub « Mes Processus » (`ProcessesHubPage`)
* **Cible :** `apps/web/src/features/settings/packs/`, `apps/web/src/features/processes/`
* **Actions :**
  1. Créer `PacksRegistryPage.tsx` (`/settings/packs`) affichant les Packs déclaratifs chargés depuis `packs/`, leurs compteurs d'objets, le statut temps réel de leurs connecteurs requis (`orcia-connectors`) et le bouton `📦 Exporter un espace en Pack`.
  2. Créer `ProcessesHubPage.tsx` (`/processes`) mettant en avant la **Chaîne de Valeur active (Macro-VSM)** en haut et la grille des **Workflows Exécutables Unitaires** en bas.

---

## TASK-07 : Frontend — Carte Interactive de Chaîne de Valeur (`ValueStreamMapView`)
* **Cible :** `apps/web/src/features/processes/vsm/`
* **Actions :**
  1. Créer `ValueStreamMapView.tsx` restituant fidèlement l'expérience du POC HTML : commutateur `Aujourd'hui | Avec les agents | Comparer`, frise des phases `01..04`, cartes d'étapes, losanges de passage humain, tracé SVG dynamique des boucles de retour en pointillés orange sans collision (`ReturnLoopsSvgOverlay.tsx`), fiche modale à 6 onglets (`StepDetailSheet.tsx`), tiroir des opportunités `P1..P3` et mode `Présenter` au clavier.

---

## TASK-08 : Frontend — Studio de Workflow 5 Blocs (Control-M), Co-pilote & Portail HITL 4 Actions
* **Cible :** `apps/web/src/features/processes/studio/`, `apps/web/src/features/processes/execution/`
* **Actions :**
  1. Créer `StudioCopilotSidebar.tsx` (chat de conception à gauche + suggestions cliquables `[+]` de `Toolboxes MCP` depuis `orcia-connectors`, et de `Skills` / `Gates` depuis le dossier `packs/<domaine>/`).
  2. Créer `WorkflowFiveBlocksCanvas.tsx` (les 5 blocs connectés façon Control-M : `1. Triggers & Contrat`, `2. Séquence de Sous-Étapes Déterministes DBOS` avec losanges de jalon et bascule `Natif ORCIA / Sas Externe`, `3. Toolbox MCP`, `4. Skills & Socle`, `5. Pipeline de Gates`).
  3. Créer `InteractiveRunDrawer.tsx` pour l'exécution interactive, la validation des `WritePreviewCard` et l'arbitrage **Anchor Card** sur Diff S3 avec les 4 actions souveraines (`Accepter`, `Amender le Diff`, `Refuser & Choisir la boucle de retour`, `Suspendre SLA`).

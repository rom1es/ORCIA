# Rapport d'Implémentation Tech Lead — Story 4.2 : Gates Agentiques avec Orthogonalité des Modèles, Pseudonymisation PII Réversible (`PiiReversibleScrubber`) & DAG de 5 Lentilles (dont `fact_verification`) + `DEC-SEC-01` / `SEC-03`

- **Clé de Story** : `4-2-gates-agentiques-avec-orthogonalité-des-modèles-pseudonymisa`
- **Actions Associées** : `DEC-SEC-01`, `SEC-03`
- **Epic** : `Epic 4` — Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution (Actions Jira, Sandbox & MCP IDE)
- **Date** : `2026-10-30`
- **Auteur** : Tech Lead / Dev Senior (`Amelia`, `Sophie` & `Karim`)
- **Statut** : `done`
- **Références Architecture & UX** : `FR-18`, `AD-6`, `AD-10`, `AD-12`, `AD-19`, `NFR-SEC-2`, `NFR-SEC-4`, `DEC-SEC-01`, `SEC-03`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique
Après le passage de la Gate Déterministe (Paliers 1 et 2, `Stories 4.1` et `4.1a`), chaque étape de workflow soumise à une validation cognitive traverse une **Gate Agentique (`AD-10`, `FR-18`)**. Trois risques majeurs menacent la fiabilité et la sécurité des évaluations par LLM :
1. **Biais d'auto-complaisance et d'ancrage cognitif** : un modèle évaluant sa propre famille ($F_{\text{eval}} = F_{\text{exec}}$) ou lisant la *Chain-of-Thought* de l'agent exécuteur valide à tort ses propres raccourcis de raisonnement.
2. **Effet « téléphone arabe » inter-étapes et hallucinations factuelles** : une étape $N$ peut dériver silencieusement des exigences fondatrices de l'étape 1 (`PRD`) ou de l'étape 2 (`Architecture`), ou inventer des faits contredisant l'*Ontologie (N1..N4)* et les *Bases de Connaissances (KBs)* épinglées.
3. **Exfiltration de PII et fuite de secrets fournisseurs (`NFR-SEC-2`, `NFR-SEC-4`, `DEC-SEC-01`, `SEC-03`)** : les données personnelles ne doivent jamais quitter la plateforme en clair vers un LLM Cloud, et aucun secret fournisseur (`api_key`) ne doit posséder de valeur par défaut en dur (`sk-orcia-local`) ni jamais apparaître dans `dbos.*`, `audit_ledger`, `domain_events_outbox`, `step_executions` ou les journaux `structlog`.

### 1.2 Analyse d'Impact GitNexus (Pré-Codage)
- **`gitnexus_impact({target: "ModelRouterService", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`3` fichiers importateurs dans `orcia_core/bootstrap/`).
- **`gitnexus_impact({target: "LiteLLMAdapter", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`1` importateur direct `bootstrap/plugin_registry.py` + `1` test `test_story_3_2b_persistence_dbos_otel.py`).
- **`gitnexus_impact({target: "configure_structlog", direction: "upstream", repo: "ORCIA"})`** :
  - `risk: UNKNOWN` dans le graphe statique, confirmé par recherche textuelle (`apps/api/src/orcia_api/main.py:L33` et `tests/unit/test_orcia_core_and_api.py:L172`).

### 1.3 Exploration & Chiffres Clés
- **Contrôle de volumétrie (`< 300-400` lignes)** :
  - `packages/orcia-kernel/src/orcia_kernel/ports.py` atteignait `487` lignes. En **Étape 0 (Pre-Story Refactoring)**, nous avons extrait les contrats de connecteurs dans `packages/orcia-kernel/src/orcia_kernel/connector_ports.py` (`177` lignes) et créé `packages/orcia-kernel/src/orcia_kernel/secret_ports.py` (`85` lignes) pour `SecretRef` et `SecretProviderPort` (tout en les ré-exportant dans `orcia_kernel.ports` pour `0` rupture d'import), ramenant `ports.py` à `377` lignes.

### 1.4 Opportunités de Factorisation (`DRY`) & Dette Technique
- Placement partagé de `ConnectorInvoker` dans `packages/orcia-core/src/orcia_core/permissions/connector_invoker.py` (Couche 4 de `AD-19 Contract 2`, ré-exporté dans `orchestration/connector_invoker.py`) afin que `bootstrap` (`LiteLLMAdapter`), `gates` (`AgenticGateService`) et `orchestration` partagent le même disjoncteur, la gestion de `Retry-After` et la taxonomie à 6 erreurs sans violer l'isolation des domaines frères (`bootstrap | orchestration`).
- Clôture conjointe de `DEC-SEC-01` et `SEC-03` via `SecretRef`, `SecretProviderPort` et l'enveloppe DEK/KEK par Workspace.

---

## 2. Plan d'Implémentation

### 2.1 Noyau Hexagonal : `SecretRef`, `SecretProviderPort` & Découpage de `orcia_kernel/ports.py` (`packages/orcia-kernel/`)
- Création de `packages/orcia-kernel/src/orcia_kernel/connector_ports.py` (extraction propre de `ConnectorPort` et du registre `orcia.connectors`).
- Création de `packages/orcia-kernel/src/orcia_kernel/secret_ports.py` :
  - `SecretRef` : référence immuable non sérialisable en clair (`__repr__` et `__str__` retournent uniquement `SecretRef(uri='secret://...')`, jamais la valeur secrète).
  - `WorkspaceEnvelopeKeyRecord` & `SecretRotationAuditEntry` (`SEC-03` : DEK par Workspace chiffrée par une KEK KMS/Vault).
  - `SecretProviderPort` (`resolve_secret(ref)`, `rotate_workspace_dek(workspace_id, actor_id)`).

### 2.2 Sécurité des Secrets, `LiteLLMAdapter` sans `sk-orcia-local` & Masquage Structlog (`DEC-SEC-01`, `SEC-03`)
- Création de `packages/orcia-core/src/orcia_core/permissions/secret_manager.py` : implémentation `EnvelopeVaultSecretProvider` (résolution de `SecretRef`, chiffrement par enveloppe AES-256-GCM DEK/KEK par Workspace, audit immuable des rotations et enregistrement des valeurs sensibles pour masquage).
- Mise à jour de `packages/orcia-core/src/orcia_core/observability/logging.py` : ajout du processeur `mask_secrets_processor` masquant automatiquement tout motif de secret (`sk-*`, `Bearer *`, clés sensibles et secrets canaris enregistrés) dans `structlog` tout en préservant les compteurs numériques (`prompt_tokens`, `completion_tokens`).
- Mise à jour de `packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py` : suppression de la valeur par défaut `sk-orcia-local`, résolution à la volée de `SecretRef` via `SecretProviderPort`, et invocation gouvernée via `ConnectorInvoker` (`AD-12`, `DEC-SEC-01`).

### 2.3 `PiiReversibleScrubber` & Moteur de Gate Agentique à 5 Lentilles (`packages/orcia-core/src/orcia_core/gates/`)
- Création de `packages/orcia-core/src/orcia_core/gates/pii_scrubber.py` (`271` lignes) :
  - `PiiReversibleScrubber` : pseudonymisation déterministe par `run_id` (adresses e-mail, téléphones, IBAN, NIR/SSN, secrets et entités personnalisées) avec stockage Redis (ou mémoire isolée par `run_id`) et ré-hydratation locale (`rehydrate_text` / `rehydrate_payload`).
  - `purge_executor_chain_of_thought` : suppression complète des blocs `<thinking>...</thinking>`, `[THOUGHT]`, `chain_of_thought`, `reasoning_content` et traces internes de l'exécuteur.
- Création de `packages/orcia-core/src/orcia_core/gates/agentic_lenses.py` (`323` lignes) et `packages/orcia-core/src/orcia_core/gates/agentic.py` (`376` lignes) :
  - Routage orthogonal (`evaluator_model_family != executor_model_family`) et routage souverain vers un modèle local (`local/ollama-*`) lorsque la classification ontologique est `SENSITIVE` ou `RESTRICTED`.
  - Exécution parallèle sans visibilité croisée des **4 Lentilles Indépendantes** (`transverse_alignment_step1`, `fact_verification`, `adversarial_edge_cases`, `domain_and_security_compliance`), suivie de la **Lentille 5 (`synthesis_and_structure`)** générant `briefing_4blocks_jsonb`, calculant `agentic_score` et publiant `GateEvaluated` (`gate_type="AGENTIC"`) dans `domain_events_outbox`.

### 2.4 Couche Backend FastAPI & Contrats OpenAPI (`apps/api/`, `packages/api-client/`)
- Exposition de `POST /api/v1/gates/agentic/evaluate` dans `apps/api/src/orcia_api/routers/gates.py` et `schemas/gates.py`.
- Régénération du SDK OpenAPI 3.1 (`0-diff`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés & Modifiés
| Fichier | Action | Lignes | Rôle |
| :--- | :--- | :---: | :--- |
| `packages/orcia-kernel/src/orcia_kernel/connector_ports.py` | Créé | `177` | Extraction de `ConnectorPort` et du registre `orcia.connectors` (`< 300-400` lignes). |
| `packages/orcia-kernel/src/orcia_kernel/secret_ports.py` | Créé | `85` | `SecretRef`, `SecretProviderPort`, `WorkspaceEnvelopeKeyRecord`, `SecretRotationAuditEntry`. |
| `packages/orcia-kernel/src/orcia_kernel/ports.py` | Modifié | `377` | Ré-export sans rupture de `connector_ports` et `secret_ports`. |
| `packages/orcia-core/src/orcia_core/permissions/secret_manager.py` | Créé | `238` | `EnvelopeVaultSecretProvider` (AES-256-GCM DEK/KEK par Workspace, rotation auditée, test du secret témoin). |
| `packages/orcia-core/src/orcia_core/permissions/connector_invoker.py` | Créé | `282` | `ConnectorInvoker` partagé en Couche 4 (`AD-19 Contract 2`). |
| `packages/orcia-core/src/orcia_core/observability/logging.py` | Modifié | `278` | Processeur `mask_secrets_processor` et liste blanche de masquage `structlog`. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py` | Modifié | `191` | Suppression de `sk-orcia-local`, résolution `SecretRef` via `SecretProviderPort` + `ConnectorInvoker`. |
| `packages/orcia-core/src/orcia_core/gates/pii_scrubber.py` | Créé | `271` | `PiiReversibleScrubber` (Redis TTL par `run_id`) & `purge_executor_chain_of_thought`. |
| `packages/orcia-core/src/orcia_core/gates/agentic_lenses.py` | Créé | `323` | Logique d'évaluation des 5 lentilles (`transverse_alignment_step1`, `fact_verification`, `adversarial_edge_cases`, `domain_and_security_compliance`, `synthesis_and_structure`). |
| `packages/orcia-core/src/orcia_core/gates/agentic.py` | Créé | `376` | `AgenticGateService` (orthogonalité, routage local `SENSITIVE`/`RESTRICTED`, DAG parallèle 4+1, Outbox `GateEvaluated`). |
| `apps/api/src/orcia_api/routers/gates.py` & `schemas/gates.py` | Modifiés | `149` / `231` | Endpoint `POST /api/v1/gates/agentic/evaluate` + garde `READ_ONLY_OBSERVER`. |
| `tests/unit/test_story_4_2_agentic_gates_and_secrets.py` | Créé | `272` | Suite de tests couvrant `Story 4.2`, `DEC-SEC-01` (secret témoin) et `SEC-03` (enveloppe DEK/KEK). |

### 3.2 Métriques & Couverture de Tests (`AD-17`)
- **Tests unitaires Python (`pytest`)** : `97 passed` en `35.84 s`, couverture globale **`91.51 %`** (`>= 90 %` requis).
- **Qualité statique & Frontières (`AD-19`)** :
  - `ruff check .` & `ruff format --check .` : `0` erreur.
  - `mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `0` erreur (`151` fichiers).
  - `lint-imports` : **`5 contracts kept, 0 broken`**.
- **Tests TypeScript & SDK OpenAPI 3.1 (`0-diff`)** : `pnpm turbo run lint typecheck test` (`9/9` tâches vertes).

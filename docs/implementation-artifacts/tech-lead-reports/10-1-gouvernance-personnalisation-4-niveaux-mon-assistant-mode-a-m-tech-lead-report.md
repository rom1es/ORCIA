# Rapport d'Analyse & Plan d'Implémentation Tech Lead — Story 10.1

- **Story Key** : `10-1-gouvernance-personnalisation-4-niveaux-mon-assistant-mode-a-m`
- **Titre** : Gouvernance & Personnalisation à 4 Niveaux de `Mon Assistant` (Bornes `🔒 AssistantHarness`, Mode A Formulaire Rapide à 3 Onglets & Mode B Studio Graphique)
- **Epic** : Epic 10 — `Mon Assistant` Tout-en-Un (Style EXEMPLE)
- **Date** : 2026-10-31
- **Auteur** : Antigravity (Tech Lead / Dev Senior ORCIA)
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte Métier & Problématique
Dans ORCIA, **`Mon Assistant`** est la résultante du workflow système à 5 nœuds orientés `orcia://system/workflows/assistant-agent` exécuté à l'intérieur des bornes de sécurité Python inaltérables **`🔒 AssistantHarness`** (`AD-15`). La **Story 10.1** permet aux utilisateurs et responsables d'équipes de personnaliser `Mon Assistant` selon leurs droits à **4 niveaux** (`USER`, `WORKSPACE`, `TEAM`, `PLATFORM`) :
- **Mode A (`Mon Assistant › ⚙ Réglages de l'assistant`)** : modale rapide à **3 onglets** (`👤 Mes préférences (Couche 5 — USER)`, `📦 Réglages de l'Espace (Couche 4 — WORKSPACE)` avec interrupteur `🔌 Exposer l'Assistant de l'Espace en MCP (/api/v1/mcp — outil assistant.ask)` soumis à la Règle de l'Entonnoir `Principe G` + bouton `📋 Copier la config MCP`, et `👁️ Assemblage complet (Lecture seule)` des 5 couches de prompt actives) ;
- **Mode B (`☍ Personnaliser dans le Studio`)** : éditeur graphique `@xyflow/react` encadré par les bornes verrouillées `🔒 AssistantHarness` (Entrée/Sortie Couche 1, rejet `HTTP 422 ERR_IMMUTABLE_HARNESS_BOUNDARY` en cas de tentative de suppression ou court-circuit), enregistrant une surcharge scopée (`TEAM` ou `WORKSPACE`) dans `workspace_customization_overrides` avec `↺ Réinitialiser à la configuration par défaut` en 1 clic.

### 1.2 Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- `impact({target: "AssistantHarness", direction: "upstream", repo: "ORCIA"})` : risque **`LOW`** (`2` dépendants directs : `orchestration/assistant_agent.py` et `orchestration/__init__.py`).
- Afin de respecter la limite de volumétrie (`<= 350` lignes par fichier) et la séparation des responsabilités, nous créons un module dédié `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py` plutôt que d'alourdir `assistant_harness.py` (`307` lignes) ou `assistant_agent.py` (`484` lignes).

### 1.3 Opportunités de Factorisation & Dette Technique
- Réutilisation de la table existante `workspace_customization_overrides` (migration `0003`) avec ajout d'un `UpsertSpec` idempotent `WORKSPACE_CUSTOMIZATION_OVERRIDES_UPSERT_SPEC` dans `packages/orcia-core/src/orcia_core/bootstrap/seeder.py`.
- Ajout des erreurs RFC 9457 `ImmutableHarnessBoundaryError` (`HTTP 422 ERR_IMMUTABLE_HARNESS_BOUNDARY`) et `FunnelRuleViolationError` (`HTTP 403 ERR_FUNNEL_RULE_VIOLATION`) dans `packages/orcia-core/src/orcia_core/orchestration/errors.py`.

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Seeder (`packages/orcia-core/bootstrap/seeder.py`)
- Ajout de `WORKSPACE_CUSTOMIZATION_OVERRIDES_UPSERT_SPEC` pour persister de manière idempotente les surcharges `TEAM`, `WORKSPACE` et `USER` sur `target_uri = 'orcia://system/workflows/assistant-agent'` dans PostgreSQL 18.

### 2.2 Noyau Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py`)
- `AssistantFourLevelGovernanceService` :
  - Gestion des 4 niveaux de personnalisation (`PLATFORM`, `TEAM`, `WORKSPACE`, `USER`) ;
  - Mode A : lecture/écriture de `UserLayerPreferences` (`Couche 5 — USER`), `WorkspaceLayerSettings` (`Couche 4 — WORKSPACE`, réservé à `TEAM_LEAD` / `PLATFORM_ADMIN`, avec vérification de la Règle de l'Entonnoir `Principe G` sur `mcp_expose_assistant` et génération du snippet `📋 Copier la config MCP`), et assemblage transparent des 5 couches (`1_CONSTITUTION`, `2_PACK_METIER`, `3_EQUIPE`, `4_ESPACE`, `5_UTILISATEUR`) ;
  - Mode B : édition Studio du graphe 5 nœuds entre les bornes `ENTRY_BOUNDARY_HARNESS` et `EXIT_BOUNDARY_HARNESS` (rejet `HTTP 422 ERR_IMMUTABLE_HARNESS_BOUNDARY` si une borne `🔒 AssistantHarness` ou un nœud socle verrouillé est supprimé, désactivé ou contourné), simulation `▷ Tester` sans écriture externe, sauvegarde dans `workspace_customization_overrides` (`TEAM` ou `WORKSPACE`) et `↺ Réinitialiser` en 1 clic.

### 2.3 Backend FastAPI & Contrats OpenAPI (`apps/api/src/orcia_api/`)
- Nouveau routeur `apps/api/src/orcia_api/routers/epic10_assistant.py` et schémas dans `apps/api/src/orcia_api/schemas/orchestration.py` :
  - `GET /api/v1/assistant/governance` (Mode A 3 onglets + Mode B graphe + 5 couches assemblées) ;
  - `PUT /api/v1/assistant/governance/mode-a/user` (Onglet 1 `👤 Mes préférences`) ;
  - `PUT /api/v1/assistant/governance/mode-a/workspace` (Onglet 2 `📦 Réglages de l'Espace` + `mcp_expose_assistant`) ;
  - `POST /api/v1/assistant/governance/mode-b/save` (Sauvegarde surcharge Studio `TEAM` / `WORKSPACE` avec garde `ERR_IMMUTABLE_HARNESS_BOUNDARY`) ;
  - `POST /api/v1/assistant/governance/mode-b/reset` (`↺ Réinitialiser à la configuration par défaut`).

### 2.4 Interface SPA `@orcia/ui` (`packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx`)
- Composant unifié supportant la modale **Mode A (`⚙ Réglages de l'assistant`, 3 onglets)** et la vue **Mode B (`☍ Personnaliser dans le Studio`, bornes `🔒 AssistantHarness` verrouillées, inspecteur `COUCHES · N`, `▷ Tester`, `Enregistrer` et `↺ Réinitialiser`)**, 100 % piloté par dictionnaire `i18n` (`fr`/`en`).

---

## 3. Bilan des Modifications & Résultats

| Fichier                                                                    | Action  | Rôle                                                                                                                                                                              |
| :------------------------------------------------------------------------- | :------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/orcia-core/src/orcia_core/orchestration/errors.py`               | Modifié | Ajout de `ERR_IMMUTABLE_HARNESS_BOUNDARY` (`422`), `ERR_FUNNEL_RULE_VIOLATION` (`403`), `ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE` (`422`), `ERR_THREAD_TURN_LOCK_HELD` (`409`). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py` | Créé    | Service `AssistantFourLevelGovernanceService` (Mode A 3 onglets, Mode B Studio, bornes `🔒 AssistantHarness`, Règle de l'Entonnoir `Principe G`, reset 1 clic).                    |
| `packages/orcia-core/src/orcia_core/bootstrap/seeder.py`                   | Modifié | Ajout de `WORKSPACE_CUSTOMIZATION_OVERRIDES_UPSERT_SPEC`.                                                                                                                         |
| `apps/api/src/orcia_api/routers/epic10_assistant.py`                       | Créé    | Endpoints REST `/api/v1/assistant/governance/*`.                                                                                                                                  |
| `packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx`         | Créé    | Primitive `@orcia/ui` Mode A (3 onglets) & Mode B (Studio Graphique avec bornes `🔒 AssistantHarness`).                                                                            |
| `tests/unit/test_epic_10_story_10_1_assistant_governance.py`               | Créé    | Tests unitaires & API Mode A / Mode B / `ERR_IMMUTABLE_HARNESS_BOUNDARY` / `ERR_FUNNEL_RULE_VIOLATION`.                                                                           |
| `tests/integration/test_story_10_1_assistant_overrides_postgres18.py`      | Créé    | Test d'intégration réel `testcontainers` PostgreSQL 18 sur `workspace_customization_overrides`.                                                                                   |

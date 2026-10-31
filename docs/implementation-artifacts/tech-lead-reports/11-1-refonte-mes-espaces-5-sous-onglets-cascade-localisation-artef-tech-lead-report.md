# Tech Lead Analysis & Implementation Report — Story 11.1 : Refonte de `Mes Espaces` en 5 Sous-Onglets, Cascade de Localisation des Artefacts à 4 Niveaux, `ExternalEditRebaser` (`Verrou V2`), `workspace_exception_waivers` Gouverné par Chaîne ADN (`Verrou V1`) & Workflow Pilote `sdlc/ticket-to-tech-spec`

- **Story Key** : `11-1-refonte-mes-espaces-5-sous-onglets-cascade-localisation-artef`
- **Epic** : Epic 11 — Gouvernance Métier de l'Espace, Exposition MCP/A2A & Atelier `orcia-pack-builder`
- **Date** : 2026-10-31
- **Auteur** : Antigravity (Tech Lead / Senior Dev)
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte & Problématique Métier (`epics.md`, `ARCHITECTURE-SPINE.md`, `DESIGN.md`)
Dans une organisation qui utilise ORCIA au quotidien, deux risques opérationnels majeurs (identifiés lors de la revue Red Team du 31 octobre) doivent être neutralisés matériellement :
1. **La saturation humaine (`Gate Fatigue`) sur les écarts documentaires récurrents (`Verrou V1`)** :
   - Lorsqu'une page Confluence présente un écart connu avec le code Git (`[STALE_WARNING]` / `ONTOLOGY_CONFLICT`) sur une norme locale d'équipe ou d'espace (`3_WORKSPACE` / `3_TEAM`), le Tech Lead doit pouvoir cocher **`[✓] Acquitter cet écart tant que la source ne change pas`** (`workspace_exception_waivers` indexé par `(workspace_id, source_uri, source_sha256, conflict_rule_id)`).
   - **Garde-fou Chaîne Causale ADN (`DIRECTIVE ➔ NORME ➔ MÉCANISME`, `AD-7`)** : si la règle en conflit remonte via `dna_chain` jusqu'à une `DIRECTIVE` de niveau `1_ENTERPRISE` marquée `inviolable: true`, un simple `TEAM_LEAD` **ne peut pas** acquitter l'écart localement (`HTTP 403 ERR_ENTERPRISE_DIRECTIVE_WAIVER_FORBIDDEN` — badge `🔒 Directive Organisationnelle`) ; seul un `PLATFORM_ADMIN` ou `SECOPS` est habilité.
2. **La friction du « Rebase de Prompt » lors d'éditions humaines externes (`Verrou V2`)** :
   - Dès qu'un artefact validé (`@vN`) est publié vers Git ou Confluence, l'outil externe redevient souverain (`Principe J`). Si un développeur modifie 20 % de la spécification dans son IDE (`@v(N+1)` externe), **`ExternalEditRebaser`** détecte la divergence `SHA-256`, exécute un diff par section, importe la version externe sans jamais l'écraser, marque les sections retouchées par l'humain en **`HUMAN_AMENDED_EXTERNAL`** (`🔒` inviolables par l'agent aval) et marque `[SUPERSEDED_BY_HUMAN_COMMIT]` les hypothèses contradictoires dans `step_memlog_jsonb`.
3. **La refonte de `Mes Espaces` en 5 sous-onglets & la Cascade de Localisation à 4 Niveaux (`Principes I & J`)** :
   - `1. Vue d'ensemble`, `2. Documents & Sources` (qualification `📚 RÉFÉRENCE` vs `🛠️ ACTIF` et `👁️ Lecture seule` vs `✍️ Lecture & Écriture (Cible d'artefacts)` + destination par défaut de l'Espace), `3. Livrables & Artefacts`, `4. Glossaire & Règles métier`, `5. Membres & Équipe`.
   - Résolution déterministe de la destination d'un livrable selon la **Cascade à 4 Niveaux** :
     1. Surcharge d'exécution (`run_destination_override_uri`),
     2. Configuration de l'étape du workflow (`step_target_destination_uri`),
     3. Destination par défaut de l'Espace (`workspace_default_destination_uri`),
     4. Repli souverain : Coffre interne ORCIA S3 CAS (`cas/<sha256>`) avec alias canonique `orcia://workspaces/<ws_slug>/artifacts/<type>/<slug>@v<N>`.
   - Confinement strict de `local://` via `os.path.realpath` (`HTTP 403 ERR_PATH_TRAVERSAL_DENIED` sur tout `../` hors racine autorisée) et acquisition de bail `ResourceLeasePort` (`AD-4`) lors d'une publication partagée.
4. **Le Workflow Pilote Semaine 1 `orcia://pack-sdlc/workflows/ticket-to-tech-spec`** :
   - Exécution complète en 3 étapes avec confinement d'orthogonalité par `SovereigntyTier` (`Verrou V3` : `C3_RESTRICTED` interdit tout modèle Cloud externe et force deux familles locales distinctes).

### 1.2 Analyse d'Impact GitNexus
- `gitnexus_impact({target: "AdaptiveHumanGateService", direction: "upstream", repo: "ORCIA"})` et `MultiProjectJiraStagedActionService` : aucune rupture des contrats existants (`risk: LOW`).
- Création d'un module dédié `packages/orcia-core/src/orcia_core/orchestration/workspace_governance_and_rebaser.py` respectant strictement `AD-19`.

---

## 2. Plan d'Implémentation

### 2.1 Migration Alembic (`0026_story_11_1_waivers_and_external_rebase.py`)
- Table `workspace_exception_waivers` (`waiver_id`, `workspace_id`, `source_uri`, `source_sha256`, `conflict_rule_id`, `dna_root_level`, `inviolable_directive`, `waived_by_user_id`, `justification`, `expires_at`, `created_at` + contrainte unique `(workspace_id, source_uri, source_sha256, conflict_rule_id)`).
- Extension de `chunk_approvals_status_check` sur `chunk_approvals` pour inclure `'HUMAN_AMENDED_EXTERNAL'` (`Verrou V2`).

### 2.2 Noyau Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/workspace_governance_and_rebaser.py`)
- `WorkspaceGovernanceAndArtifactRoutingService` :
  - Structure `Mes Espaces` à 5 sous-onglets et qualification des sources (`REFERENCE`/`ACTIVE`, `READ_ONLY`/`READ_WRITE_TARGET`).
  - `register_exception_waiver(...)` (`Verrou V1`) avec contrôle de la Chaîne Causale ADN (`1_ENTERPRISE` + `inviolable: true` $\rightarrow$ `EnterpriseDirectiveWaiverForbiddenError` pour `TEAM_LEAD`, autorisé pour `PLATFORM_ADMIN` / `SECOPS`) et invalidation automatique dès que `source_sha256` change.
  - `resolve_artifact_destination(...)` : Cascade à 4 niveaux + confinement `os.path.realpath` sur `local://` (`PathTraversalDeniedError`) + URI canonique `orcia://workspaces/<ws_slug>/artifacts/<type>/<slug>@v<N>` + empreinte `cas/<sha256>`.
  - `rebase_external_artifact_edits(...)` (`ExternalEditRebaser`, `Verrou V2`) : détection de divergence `SHA-256`, diff par section, marquage `HUMAN_AMENDED_EXTERNAL` et annotation `[SUPERSEDED_BY_HUMAN_COMMIT]` dans le `step_memlog`.
  - `run_pilot_ticket_to_tech_spec_workflow(...)` : exécution des 3 étapes de `orcia://pack-sdlc/workflows/ticket-to-tech-spec` avec `Verrou V3` (`SovereigntyTier` `C0..C3`).

### 2.3 Backend FastAPI (`apps/api/src/orcia_api/routers/epic11_workspace_governance.py`)
- Endpoints REST sous `/api/v1/workspaces/{workspace_id}/governance/*` (vue 5 sous-onglets, acquittement `waivers`, routage 4 niveaux, rebase externe `Verrou V2`, et lancement du workflow pilote `ticket-to-tech-spec`).

### 2.4 Interface SPA `@orcia/ui` (`packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`)
- Composant Direction C à 5 sous-onglets (`Vue d'ensemble`, `Documents & Sources`, `Livrables & Artefacts`, `Glossaire & Règles métier`, `Membres & Équipe`), badge `🔒 Directive Organisationnelle`, statut `🔒 HUMAN_AMENDED_EXTERNAL` et sélecteur de Cascade à 4 niveaux.

---

## 3. Bilan des Modifications & Résultats

| Fichier | Action | Rôle |
| :--- | :--- | :--- |
| `infra/migrations/versions/0026_story_11_1_waivers_and_external_rebase.py` | Créé | Table `workspace_exception_waivers` + `HUMAN_AMENDED_EXTERNAL` sur `chunk_approvals` |
| `packages/orcia-core/src/orcia_core/orchestration/workspace_governance_and_rebaser.py` | Créé | Service `Mes Espaces` 5 onglets, `Verrou V1`, Cascade 4 niveaux, `ExternalEditRebaser` (`Verrou V2`) & workflow pilote `ticket-to-tech-spec` (`Verrou V3`) |
| `apps/api/src/orcia_api/schemas/epic11_governance.py` | Créé | Schémas Pydantic v2 de l'Epic 11 (`Story 11.1`) |
| `apps/api/src/orcia_api/routers/epic11_workspace_governance.py` | Créé | Endpoints REST Story 11.1 |
| `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx` | Créé | Primitive UI Direction C `Mes Espaces` à 5 sous-onglets |
| `packages/ui/src/__tests__/epic11-governance.test.tsx` | Créé | Tests Vitest Story 11.1 |
| `tests/unit/test_epic_11_story_11_1_workspace_5tabs_waivers_rebaser.py` | Créé | Tests unitaires & API Story 11.1 |
| `tests/integration/test_story_11_1_waivers_and_external_rebase_postgres18.py` | Créé | Tests d'intégration réels PostgreSQL 18 `testcontainers` |

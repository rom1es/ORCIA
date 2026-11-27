## Epic 21: Couverture Intégrale par User Journeys (UJ-1..UJ-20), Campagne End-to-End avec Vérité PostgreSQL 18, Captures d'État Final, Audit Croisé UX/Architecture & Préparation de l'Epic 22

Garantir que **100 % des fonctionnalités métier (`kind: feature`, soit les `62` capacités fonctionnelles sur les `65` entrées de `docs/product/capabilities.yaml`)** d'ORCIA sont décrites par des User Journeys complets (`UJ-1` à `UJ-20`) dans le PRD (`prd.md`) et `EXPERIENCE.md`, contrôlées de manière bloquante en CI par `pnpm site:check`, et couvertes par des tests End-to-End Playwright vérifiant systématiquement le rendu et les interactions UI, la survie au rechargement `F5` (`page.reload()`) **ET** la persistance réelle en base PostgreSQL 18 (`orcia_e2e`, zéro validation sur état uniquement conservé en mémoire RAM Python). L'Epic organise ensuite l'exécution de la campagne intégrale avec capture PNG de l'état final de chaque test (succès comme échecs), son analyse croisée par **Sally (UX)** et **Winston (Architecture)**, la production des rapports Tech Lead pré-implémentation individuels et l'initialisation complète du plan directeur de l'**Epic 22** de remédiation.

> **Règle stricte de non-maquillage pour l'Epic 21 :** les tests E2E ne doivent ni omettre les assertions `SELECT` PostgreSQL 18, ni affaiblir les vérifications de survie au `F5`, ni neutraliser (`test.skip` / `test.fixme`) les échecs révélant une persistance encore en mémoire RAM Python, un câblage vertical incomplet ou un défaut UI ; les échecs honnêtes constatés durant la campagne constituent l'entrée officielle de l'audit Sally × Winston et de l'Epic 22.

### Story 21.1: Classification des 65 Capacités (`kind: feature | foundation`, `e2e_exempt_reason`, `uj`, `db_tables`, `read_only_surface`) & Validation de Schéma dans `capabilities_registry.py`

As a Product Manager / Tech Lead (`John` / `Amelia`),
I want classifier exhaustivement les 65 capacités recensées dans `docs/product/capabilities.yaml` en `kind: feature` (62 capacités métier) ou `kind: foundation` (3 capacités socles d'architecture/hygiène : `CAP-006`, `CAP-100`, `CAP-202`) avec les champs structurés `e2e_exempt_reason`, `uj`, `db_tables` et `read_only_surface`, et renforcer la validation de schéma dans `infra/scripts/capabilities_registry.py`,
So that le périmètre exact à couvrir par des User Journeys et des tests End-to-End avec vérité PostgreSQL 18 soit formellement tracé et contrôlé sans angle mort (`FR-1`..`FR-36`, `AD-17`, `NFR-TEST-1`).

**Dépendances :** Aucune (socle documentaire et schéma de pilotage de l'Epic 21). Précède Story 21.2, Story 21.3 et Stories 21.5..21.7.
**Références :** `docs/product/capabilities.yaml`, `infra/scripts/capabilities_registry.py`, `AD-17`, `NFR-TEST-1`, `GEMINI.md` §5.
**Fichiers impactés :** `docs/product/capabilities.yaml`, `infra/scripts/capabilities_registry.py`, `tests/unit/test_capabilities_registry.py`.

**Acceptance Criteria:**

**Given** les 65 capacités (`CAP-001` à `CAP-203`) présentes dans `docs/product/capabilities.yaml`
**When** le schéma de chaque entrée est complété et audité
**Then** chaque capacité déclare explicitement `kind: feature` (62 entrées métier) ou `kind: foundation` (3 entrées d'infrastructure/hygiène : `CAP-006`, `CAP-100`, `CAP-202`) ; toute capacité `foundation` possède un champ non vide `e2e_exempt_reason` justifiant sa couverture hors E2E, et toute capacité `feature` renseigne `uj: [UJ-...]` ainsi que soit `db_tables: [...]` (tables PostgreSQL 18 cibles pour les assertions SQL), soit `read_only_surface: true` lorsque la surface est strictement en lecture/consultation sans écriture SQL propre.

**Given** les règles de validation ajoutées dans `infra/scripts/capabilities_registry.py` (`validate_registry`)
**When** la validation du registre est exécutée
**Then** elle rejette avec un message explicite : toute capacité sans `kind` dans `{feature, foundation}`, toute capacité `foundation` sans `e2e_exempt_reason`, toute capacité `feature` sans `uj` valide (`UJ-1`..`UJ-20`), et toute capacité `feature` dépourvue à la fois de `db_tables` non vide et de `read_only_surface: true`.

**Given** la suite de tests unitaires du registre (`tests/unit/test_capabilities_registry.py`)
**When** `.venv/bin/pytest tests/unit/test_capabilities_registry.py` est exécuté
**Then** les cas nominaux sur les 65 capacités et les cas de rejet de schéma (absence de `kind`, `foundation` sans exemption, `feature` sans `db_tables` ni `read_only_surface`) passent à `100 %` et `pnpm site:check` reste vert.

---

### Story 21.2: Référentiel Complet des User Journeys (`UJ-1` à `UJ-20`) dans `prd.md` & `Key Flows` dans `EXPERIENCE.md` avec Test de Cohérence Automatique

As a Product Manager (`John`) & UX Designer (`Sally`),
I want compléter le référentiel des User Journeys (`UJ-1` à `UJ-20`) dans `prd.md` (§2.3 et §4.10) en annotant `AIOPS-INCIDENT-LOOP-01` sur `UJ-12` et en rédigeant `UJ-13` à `UJ-20`, puis enrichir les `Key Flows` dans `EXPERIENCE.md` (§9) et verrouiller l'alignement par un test de cohérence automatique,
So that chaque capacité fonctionnelle `feature` et chaque exigence `FR-1`..`FR-36` dispose d'un scénario utilisateur nommé, bout-en-bout et testable sans ambiguïté de périmètre (`FR-1`..`FR-36`, `UX-DR1`..`UX-DR17`).

**Dépendances :** Dépend de Story 21.1 (attribution cible des `UJ` dans `capabilities.yaml`). Précède Story 21.3 et Stories 21.5..21.7.
**Références :** `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md` (§2.3, §4.10), `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` (§9, §1.2), `docs/implementation-artifacts/sprint-status.yaml` (`AIOPS-INCIDENT-LOOP-01`).
**Fichiers impactés :** `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md`, `tests/unit/test_uj_prd_experience_consistency.py`.

**Acceptance Criteria:**

**Given** `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md` (§2.3 et §4.10)
**When** le référentiel des User Journeys est complété
**Then** `UJ-12` inclut l'annotation explicite `AIOPS-INCIDENT-LOOP-01` bornant la boucle d'incident sans écriture de code ni mutation Git, les 8 nouveaux parcours `UJ-13` à `UJ-20` sont rédigés au format standard du PRD (`Persona + contexte`, `Entry state`, `Path`, `Climax`, `Resolution`, `Edge case`) pour couvrir l'intégralité des capacités post-MVP (`Auth/2FA/Compte/Profil`, `Mon Organisation/IAM/SecOps/Observateur`, `Hub Modèles IA/Réindexation/Connecteurs`, `Préférences/Clés MCP`, `Citations Assistant/V5/Background Audit`, `Sources multi-nature/codegraph-mcp/ADN Starlark/Promotions Glossaire ONTOLOGY_LEAD`, `Catalogue RBAC/Packs/Process Studio v2/Wizards/Banc MCP`, `Aide contextuelle /help & /showcase`), et chaque `FR-31`..`FR-36` (§4.10) référence explicitement ses `UJ-*` (`Réalise UJ-...`).

**Given** `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` (§9)
**When** la section `Key Flows` est mise à jour
**Then** les flux comportementaux couvrent `UJ-1` à `UJ-20` en respectant les 3 invariants de microcopy utilisateur sans jargon technique interne (`EXPERIENCE.md` §1.2).

**Given** le test de cohérence automatique `tests/unit/test_uj_prd_experience_consistency.py`
**When** `.venv/bin/pytest tests/unit/test_uj_prd_experience_consistency.py` est exécuté
**Then** il vérifie automatiquement : l'existence des 20 titres `UJ-1` à `UJ-20` dans `prd.md` (§2.3), l'absence de trou de numérotation, le référencement `UJ-*` sur `FR-1`..`FR-36` (incluant `§4.10`), la couverture de `UJ-1`..`UJ-20` dans `EXPERIENCE.md` (§9), et l'absence de `UJ` référencé dans `capabilities.yaml` qui serait absent du PRD ou de `EXPERIENCE.md`.

---

### Story 21.3: Refactoring Modulaire de `sync_site_catalog.py` (`< 350` Lignes) & Verrouillage CI Bloquant `CAP ↔ UJ ↔ Spec E2E` (`pnpm site:check`)

As a Tech Lead / Ingénieur Plateforme (`Amelia` / `Karim`),
I want découper `infra/scripts/sync_site_catalog.py` sous `< 350` lignes via `_site_repo_parsers.py` et `_site_html_renderer.py`, et implémenter le contrôle CI bloquant `CAP ↔ UJ ↔ Spec E2E` dans `infra/scripts/uj_e2e_coverage.py` et `infra/scripts/capabilities_registry.py`,
So that `pnpm site:check` bloque automatiquement toute capacité `feature` sans `UJ`, toute capacité `live` `feature` sans spec E2E fonctionnelle (hors smoke `11-*`), et toute mention abusive `verification: runtime` sans E2E passant, tout en éliminant la dette de taille sur `sync_site_catalog.py` (`GEMINI.md` § Policy & §5, `AD-17`).

**Dépendances :** Dépend de Story 21.1 et Story 21.2. Précède Stories 21.4..21.8.
**Références :** `infra/scripts/sync_site_catalog.py`, `infra/scripts/capabilities_registry.py`, `GEMINI.md` (seuil 300–400 lignes & §5).
**Fichiers impactés :** `infra/scripts/sync_site_catalog.py`, `infra/scripts/_site_repo_parsers.py`, `infra/scripts/_site_html_renderer.py`, `infra/scripts/uj_e2e_coverage.py`, `infra/scripts/capabilities_registry.py`, `tests/unit/test_uj_e2e_coverage_gate.py`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`.

**Acceptance Criteria:**

**Given** le script `infra/scripts/sync_site_catalog.py` (actuellement > 880 lignes)
**When** l'extraction modulaire est réalisée
**Then** les fonctions d'introspection du dépôt sont déplacées dans `infra/scripts/_site_repo_parsers.py` et le rendu HTML statique dans `infra/scripts/_site_html_renderer.py`, ramenant `infra/scripts/sync_site_catalog.py` strictement sous `< 350` lignes, tout en conservant `parse_active_routes` et les artefacts générés par `pnpm site:sync` strictement fonctionnels et conformes à `pnpm site:check`.

**Given** le nouveau module `infra/scripts/uj_e2e_coverage.py` intégré à `infra/scripts/capabilities_registry.py` (`run_registry_check`)
**When** `pnpm site:check` s'exécute
**Then** il échoue avec un diagnostic explicite si :
- une capacité `kind: feature` ne possède pas au moins un `UJ` valide (`UJ-1`..`UJ-20`) présent dans `prd.md` ;
- une capacité `live` de type `feature` ne référence aucune spec E2E fonctionnelle sous `apps/web/e2e/` (les specs purement smoke `11-*` comme `11-screens-smoke-without-server-errors.spec.ts` sont explicitement exclues du décompte fonctionnel), sauf exemption transitoire déclarée via `e2e_backlog_story` ou `e2e_remediation_ref` ;
- une capacité déclare `verification: runtime` sans au moins une spec E2E fonctionnelle référencée et active (ou alors que son dernier statut E2E enregistré est en échec).

**Given** les tests unitaires `tests/unit/test_uj_e2e_coverage_gate.py` et les outils qualité Python
**When** `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py`, `.venv/bin/ruff check infra/scripts`, et `pnpm site:check` s'exécutent
**Then** tous les scénarios de blocage (smoke `11-*` seul, `feature` sans `UJ`, `runtime` sans spec fonctionnelle, taille de `sync_site_catalog.py < 350` lignes) et le cas nominal passent sans contournement.

---

### Story 21.4: Harnais Playwright de Vérité PostgreSQL 18 (`query_db.py` + `dbAssertions.ts`), Fixture Capture PNG Systématique (`e2eCaptureFixture.ts`) & Mise à Niveau des 16 Specs Existantes

As a Tech Lead / QA Automation (`Amelia` / `Winston`),
I want fournir un harnais Playwright interrogeant PostgreSQL 18 (`orcia_e2e`) en lecture seule stricte sans ajouter de package npm (`infra/scripts/e2e/query_db.py` + `apps/web/e2e/support/dbAssertions.ts`), une fixture capturant systématiquement le screenshot PNG final de chaque test en succès comme en échec (`apps/web/e2e/support/e2eCaptureFixture.ts`), et mettre à niveau les 16 specs existantes (`00..13` + `shell.spec.ts`) avec en-têtes `@uj`/`@cap`, vérification `F5` et assertions `SELECT` PostgreSQL 18,
So that chaque test E2E prouve la persistance réelle en base de données (zéro faux positif sur état en RAM Python) et produise une preuve visuelle exploitable par Sally et Winston (`AD-17`, `GEMINI.md` §3).

**Dépendances :** Dépend de Story 21.3. Précède Stories 21.5..21.8.
**Références :** `infra/scripts/e2e/e2e_stack.py`, `infra/scripts/e2e/e2e_stack_config.py`, `apps/web/playwright.config.ts`, `GEMINI.md` §3, règle de non-maquillage Epic 21.
**Fichiers impactés :** `infra/scripts/e2e/query_db.py`, `apps/web/e2e/support/dbAssertions.ts`, `apps/web/e2e/support/e2eCaptureFixture.ts`, `apps/web/e2e/00-stack-smoke.spec.ts` .. `apps/web/e2e/13-epic-7-autonomous-governance-and-supervision.spec.ts`, `apps/web/e2e/shell.spec.ts`, `tests/unit/test_e2e_query_db_readonly.py`.

**Acceptance Criteria:**

**Given** le script `infra/scripts/e2e/query_db.py` et les helpers `apps/web/e2e/support/dbAssertions.ts` (exécutant `.venv/bin/python infra/scripts/e2e/query_db.py` sans aucun ajout dans `apps/web/package.json`)
**When** un test Playwright invoque une assertion PostgreSQL 18 (`queryDbRows`, `expectDbRowExists`, `expectDbRowCount`)
**Then** `query_db.py` charge `.orcia-run/e2e-stack-state.json`, vérifie `is_isolated_e2e_database_url` (refus strict hors base `orcia_e2e` éphémère), rejette toute requête non strictement lecture seule (`SELECT` / `WITH ... SELECT` uniquement, rejet de `INSERT`/`UPDATE`/`DELETE`/`DDL`/multi-statements `;`, transaction PostgreSQL en mode `READ ONLY`), et retourne le résultat JSON structuré sans erreur.

**Given** la fixture `apps/web/e2e/support/e2eCaptureFixture.ts`
**When** n'importe quel test E2E se termine (statut `passed`, `failed` ou `timedOut`)
**Then** une capture PNG pleine page de l'état final est enregistrée systématiquement sous `docs/implementation-artifacts/e2e-campaign-epic-21/screenshots/<spec-slug>/<test-slug>--<status>.png` et une entrée JSONL correspondante (`spec`, `test_title`, `uj`, `cap`, `status`, `screenshot_path`, `url`, `duration_ms`, `timestamp`) est ajoutée à `docs/implementation-artifacts/e2e-campaign-epic-21/manifest.jsonl`.

**Given** les 16 specs E2E existantes (`00` à `13` incluant `12-finops-*` et `12-epic16-*`, plus `shell.spec.ts`)
**When** elles sont mises à niveau
**Then** chaque fichier déclare ses métadonnées d'en-tête `@uj` et `@cap`, utilise `e2eCaptureFixture`, vérifie la survie au rafraîchissement (`await page.reload()`) après toute mutation, et exécute des assertions `SELECT` PostgreSQL 18 réelles sur les tables cibles (`db_tables`) — sans jamais contourner, désactiver ni marquer `test.skip` / `test.fixme` les échecs révélant un défaut réel.

---

### Story 21.5: Nouvelles Specs E2E Lot A (`14` à `16`) — Auth/2FA/Compte/Profil (`UJ-13`, `UJ-16`), Mon Organisation/IAM/SecOps/Inbox & Garde `READ_ONLY_OBSERVER` `403` (`UJ-4`, `UJ-14`), Hub Modèles IA/Réindexation/Connecteurs & Permission Broker (`UJ-7`, `UJ-15`)

As a Utilisateur, Responsable BU/Équipe, Administrateur Plateforme & Développeur (`UJ-4`, `UJ-7`, `UJ-13`, `UJ-14`, `UJ-15`, `UJ-16`),
I want couvrir par trois nouvelles specs Playwright (`14`, `15`, `16`) les parcours Authentification exclusive / 2FA / Mot de passe temporaire / Mon Compte / `/profile`, Gouvernance déléguée « Mon Organisation » / IAM / SecOps / `/inbox` navigateur + garde `READ_ONLY_OBSERVER` `403`, et Hub Modèles IA / Réindexation bloquante / Connecteurs / Passthrough & Permission Broker avec `F5` et assertions `SELECT` PostgreSQL 18,
So that les fondations identitaires, organisationnelles et IA soient validées bout en bout de l'UI jusqu'à la base de données (`FR-2`, `FR-3`, `FR-21`, `FR-22`, `FR-31`, `FR-32`).

**Dépendances :** Dépend de Story 21.3 et Story 21.4.
**Références :** `UJ-4`, `UJ-7`, `UJ-13`, `UJ-14`, `UJ-15`, `UJ-16`, `CAP-001`, `CAP-003`, `CAP-040`, `CAP-041`, `CAP-043`, `CAP-050`..`CAP-054`, `CAP-058`, `CAP-063`, `CAP-067`, `CAP-069`, `CAP-190`, `CAP-203`.
**Fichiers impactés :** `apps/web/e2e/14-auth-2fa-account-and-profile.spec.ts`, `apps/web/e2e/15-organization-iam-secops-inbox-and-observer.spec.ts`, `apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts`, `docs/product/capabilities.yaml`.

**Acceptance Criteria:**

**Given** `apps/web/e2e/14-auth-2fa-account-and-profile.spec.ts` (`@uj UJ-13 UJ-16`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste la politique d'authentification exclusive (`LOCAL` / `OIDC`), le double facteur (`TOTP` / `EMAIL_OTP`), la connexion par mot de passe temporaire et changement obligatoire, le popup « Mon Compte » + modale Paramètres 5 onglets (préférences, clés IDE/MCP) et la page `/profile` (identité, 4 KPIs tokens/séries, éléments populaires), contrôle la survie après `page.reload()` (`F5`), et vérifie via `SELECT` PG18 (`iam_accounts`, `platform_auth_settings`, `user_preferences`, `user_mcp_tokens`, `audit_ledger`).

**Given** `apps/web/e2e/15-organization-iam-secops-inbox-and-observer.spec.ts` (`@uj UJ-4 UJ-14`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste `/organization` avec `BU_LEAD` et `TEAM_LEAD` (création de sous-BU/équipe, invitation scopée sans escalade, interdiction `403` de suppression de la BU racine), `/settings` IAM (matrice des rôles, exceptions SecOps), `/inbox` navigateur (filtres personnel/équipe/autonome) et la garde `READ_ONLY_OBSERVER` rejetant toute mutation (`403`), contrôle la survie au `page.reload()` (`F5`), et vérifie via `SELECT` PG18 (`org_units`, `iam_accounts`, `iam_secops_exceptions`, `audit_ledger` avec `org_unit_id`, `inbox_notifications`).

**Given** `apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts` (`@uj UJ-7 UJ-15`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste `/settings/ai-models` (champs vides initiaux, découverte `0` token, test de connexion chat/embedding dim 1024, modèle d'embedding unique GLOBAL, blocage Assistant/RAG sans embedding `ERR_NO_ACTIVE_EMBEDDING_MODEL` et réindexation bloquante `503 ERR_RAG_REINDEX_IN_PROGRESS`), les connecteurs socle et Passthrough utilisateur, et le `PermissionBroker` affichant la procédure + lien Jira + `Replay Step N`, vérifie la survie au `page.reload()` (`F5`) et exécute des `SELECT` PG18 (`workspace_llm_tier_mappings`, `enterprise_connectors`, `user_passthrough_credentials`, `rag_reindexing_jobs`), sans masquer un éventuel échec via `test.skip`.

---

### Story 21.6: Nouvelles Specs E2E Lot B (`17` & `18`) — Sources d'Espace Multi-Nature / Fraîcheur `SHA-256` / `codegraph-mcp` / Chaîne ADN Starlark / Promotions Glossaire `L4 → L1` (`UJ-5`, `UJ-18`) & Catalogue Fédéré RBAC / Packs / Wizards / Banc de Test MCP-A2A (`UJ-9`, `UJ-19`)

As a Tech Lead, Référent Glossaire (`ONTOLOGY_LEAD`), Administrateur Plateforme & Concepteur de Packs (`UJ-5`, `UJ-9`, `UJ-18`, `UJ-19`),
I want couvrir par deux nouvelles specs Playwright (`17` & `18`) les sources d'espace multi-nature, la fraîcheur `SHA-256`, `codegraph-mcp`, la chaîne ADN Starlark & waivers, les promotions Glossaire `ONTOLOGY_LEAD` (`L4 → L1`), le Catalogue Fédéré RBAC, les packs déclaratifs, les wizards durables et le banc de test MCP/A2A avec `F5` et assertions `SELECT` PostgreSQL 18,
So that la gouvernance documentaire, sémantique et catalogue soit validée jusqu'en base PostgreSQL (`FR-8`, `FR-9`, `FR-10`, `FR-20`, `FR-23`, `FR-28`, `FR-34`, `FR-35`).

**Dépendances :** Dépend de Story 21.3 et Story 21.4.
**Références :** `UJ-5`, `UJ-9`, `UJ-18`, `UJ-19`, `CAP-002`, `CAP-010`, `CAP-011`, `CAP-055`..`CAP-057`, `CAP-080`..`CAP-084`, `CAP-150`, `CAP-180`.
**Fichiers impactés :** `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts`, `apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts`, `docs/product/capabilities.yaml`.

**Acceptance Criteria:**

**Given** `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts` (`@uj UJ-5 UJ-18`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle valide l'ajout et la gestion de sources multi-nature dans `/workspaces/$wsId/sources`, la sonde de fraîcheur `SHA-256` et `[STALE_WARNING]`, l'invocation lecture seule `codegraph-mcp`, la compilation `Text-to-Starlark` de la chaîne ADN (`Directive → Norme → Mécanisme`) + acquittement `workspace_exception_waivers`, et le workflow complet de promotion Glossaire `ONTOLOGY_LEAD` (`L4 → L3 → L2 → L1`) dans `/ontology` avec détection de collision, contrôle la survie au `page.reload()` (`F5`), et vérifie par `SELECT` PG18 (`workspace_datasources`, `datasource_webhook_deliveries`, `workspace_exception_waivers`, `ontology_concepts`, `ontology_promotion_proposals`).

**Given** `apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts` (`@uj UJ-9 UJ-19`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle valide le Catalogue Fédéré (`/catalog`) avec ses permissions RBAC (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) et cycle de publication, l'écran `/settings/packs` (packs déclaratifs `packs/sdlc`, `packs/orcia-docs`, activation et prérequis connecteurs), les wizards d'initialisation durables (`/wizards`) et le banc de test MCP/A2A (`🔌`), contrôle la survie au `page.reload()` (`F5`), et vérifie par `SELECT` PG18 (`catalog_items`, `workflow_definitions`, `declarative_packs`, `workspace_pack_activations`, `wizard_runs`, `audit_ledger`).

---

### Story 21.7: Nouvelles Specs E2E Lot C (`19` à `21`) — Orchestration `What-If`/Replay/Gates Orthogonales (`UJ-1`..`UJ-3`, `UJ-6`), Process Studio v2/FinOps/Autonomie/`LOG_SINK_ALERT` (`UJ-8`, `UJ-11`, `UJ-12`, `UJ-19`), Citations Assistant `[S1]/[G1]/[O1]`/Verrou V5/Background Audit/`/help`/`/showcase` (`UJ-10`, `UJ-17`, `UJ-20`) — Couverture `100 %` des `62` Capacités `feature`

As a PM, Architecte, Tech Lead, SecOps, Directrice BU & Utilisateur (`UJ-1`..`UJ-3`, `UJ-6`, `UJ-8`, `UJ-10`..`UJ-12`, `UJ-17`, `UJ-19`, `UJ-20`),
I want couvrir par trois nouvelles specs Playwright (`19`, `20`, `21`) l'orchestration `What-If` / `[STALE_WARNING]` / Replay Step N / Gates orthogonales, Process Studio v2 (Macro-VSM 11 étapes, Studio 5 blocs, HITL 4 actions), FinOps cognitif, autonomie & déclencheur `LOG_SINK_ALERT`, ainsi que les citations Assistant `[S1]/[G1]/[O1]` & Verrou V5, audit en tâche de fond, `/help` (`ⓘ`) & `/showcase` avec `F5` et assertions `SELECT` PostgreSQL 18,
So that **100 % des `62` capacités `feature` soient couvertes avec `0` `e2e_backlog_story` résiduel** et vérifiées par `pnpm site:check` (`FR-1`..`FR-36`, `AD-17`).

**Dépendances :** Dépend de Story 21.3, Story 21.4, Story 21.5 et Story 21.6. Précède Story 21.8.
**Références :** `UJ-1`..`UJ-3`, `UJ-6`, `UJ-8`, `UJ-10`..`UJ-12`, `UJ-17`, `UJ-19`, `UJ-20`, `CAP-020`..`CAP-024`, `CAP-030`..`CAP-033`, `CAP-064`, `CAP-065`, `CAP-066`, `CAP-068`, `CAP-070`..`CAP-076`, `CAP-090`..`CAP-092`, `CAP-140`, `CAP-160`, `CAP-200`, `CAP-201`.
**Fichiers impactés :** `apps/web/e2e/19-orchestration-whatif-replay-and-gates.spec.ts`, `apps/web/e2e/20-process-studio-v2-finops-and-log-sink.spec.ts`, `apps/web/e2e/21-assistant-citations-v5-audit-help-showcase.spec.ts`, `docs/product/capabilities.yaml`.

**Acceptance Criteria:**

**Given** `apps/web/e2e/19-orchestration-whatif-replay-and-gates.spec.ts` (`@uj UJ-1 UJ-2 UJ-3 UJ-6`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste `Workflow-as-Code`, Challenge Amont avec simulation `What-If`, signalement `[STALE_WARNING]` + Replay Step N, Gate Déterministe Sandbox et Gate Agentique Orthogonale (`evaluator_model_family != executor_model_family`) + Gate Humaine, vérifie la survie au `page.reload()` (`F5`), et valide via `SELECT` PG18 (`workflow_runs`, `step_executions`, `blackboard_snapshots`, `gate_evaluations`, `run_locks`).

**Given** `apps/web/e2e/20-process-studio-v2-finops-and-log-sink.spec.ts` (`@uj UJ-8 UJ-11 UJ-12 UJ-19`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste la Macro-VSM 11 étapes (`/processes/vsm/$vsmId`), le Studio 5 blocs (`/processes/studio/$workflowId`), la revue HITL 4 actions, le tableau FinOps cognitif + quotas connecteurs (`/finops`), et le déclenchement idempotent `LOG_SINK_ALERT` (`AIOPS-INCIDENT-LOOP-01`) avec contrat d'autonomie et `Kill-Switch`/`Rollback`, vérifie la survie au `page.reload()` (`F5`), et valide via `SELECT` PG18 (`workflows_v2`, `autonomy_contracts`, `workflow_triggers`, `finops_cost_entries`, `audit_ledger`).

**Given** `apps/web/e2e/21-assistant-citations-v5-audit-help-showcase.spec.ts` (`@uj UJ-10 UJ-17 UJ-20`)
**When** la spec s'exécute et que `docs/product/capabilities.yaml` est mis à jour
**Then** elle teste les citations déterministes `[S1]/[G1]/[O1]`, le Verrou V5 d'officialisation via Gate, l'audit en tâche de fond (`BACKGROUND_AUDIT`), le renvoi ciblé `/help` (`ⓘ`) et le site vitrine `/showcase` avec `F5` et assertions `SELECT` PG18 (`assistant_threads`, `assistant_messages`, `catalog_items`), et **100 % des `62` capacités `feature` possèdent une couverture E2E fonctionnelle (`0` `e2e_backlog_story` résiduel dans `capabilities.yaml`, `pnpm site:check` passant à `0` erreur)**.

---

### Story 21.8: Campagne E2E Intégrale (`00..21` + `shell.spec.ts`, `--retries=0 --max-failures=0`), Archivage Screenshots PNG & `playwright-results.json`, Bilan d'Exécution, Audit Croisé Sally × Winston & Vérité dans `capabilities.yaml`

As a UX Designer (`Sally`), Architecte (`Winston`) & Tech Lead (`Amelia`),
I want exécuter l'intégralité des specs E2E (`00..21` + `shell.spec.ts`) sans aucun retry ni arrêt anticipé (`--retries=0 --max-failures=0`), archiver toutes les captures PNG d'état final (succès et échecs) et `playwright-results.json`, produire le bilan factuel d'exécution, mener l'inspection croisée Sally × Winston dans `synthese-remediation-sally-winston-epic-21.md`, et mettre à jour honnêtement `docs/product/capabilities.yaml`,
So that chaque écart UI, UX, de persistance ou d'architecture soit objectivé par des preuves visuelles et SQL irréfutables avant planification de la remédiation (`AD-17`, `GEMINI.md` §5).

**Dépendances :** Dépend de Story 21.7 (100 % des specs écrites). Précède Story 21.9.
**Références :** `apps/web/playwright.config.ts`, `docs/product/capabilities.yaml`, `EXPERIENCE.md`, `DESIGN.md`, `ARCHITECTURE-SPINE.md`.
**Fichiers impactés :** `docs/implementation-artifacts/e2e-campaign-epic-21/playwright-results.json`, `docs/implementation-artifacts/e2e-campaign-epic-21/manifest.jsonl`, `docs/implementation-artifacts/e2e-campaign-epic-21/screenshots/**/*.png`, `docs/implementation-artifacts/e2e-campaign-epic-21/bilan-execution-tests-e2e-epic-21.md`, `docs/implementation-artifacts/e2e-campaign-epic-21/synthese-remediation-sally-winston-epic-21.md`, `docs/product/capabilities.yaml`.

**Acceptance Criteria:**

**Given** l'ensemble des suites Playwright (`00..21` incluant `12-finops-*` et `12-epic16-*`, plus `shell.spec.ts`) sur `desktop-cockpit` (`1440x900`) et `mobile-companion` (`390x844`)
**When** la campagne intégrale est lancée avec `--retries=0 --max-failures=0` et le reporter JSON activé
**Then** la totalité des tests s'exécute sans aucun `test.skip` / `test.fixme` masquant un échec, et les artefacts complets (`playwright-results.json`, `manifest.jsonl`, et l'intégralité des captures PNG d'état final en succès comme en échec sous `screenshots/`) sont archivés dans `docs/implementation-artifacts/e2e-campaign-epic-21/`.

**Given** les résultats et captures archivés
**When** `docs/implementation-artifacts/e2e-campaign-epic-21/bilan-execution-tests-e2e-epic-21.md` est rédigé
**Then** il dresse l'inventaire chiffré exact (total tests, verts, rouges, 0 skippé), la matrice de couverture `CAP ↔ UJ ↔ Spec ↔ Vérification UI/F5/SQL`, la cause racine observée de chaque échec et les liens vers toutes les captures PNG correspondantes.

**Given** la revue croisée de toutes les captures PNG et traces d'échecs par **Sally (UX)** et **Winston (Architecture)**
**When** ils produisent `docs/implementation-artifacts/e2e-campaign-epic-21/synthese-remediation-sally-winston-epic-21.md`
**Then** chaque défaillance E2E et chaque anomalie visuelle/ergonomique/architecturale détectée sur capture (surcharge, jargon, défaut de feedback, état RAM non persisté en PG18, violation `AD-*`) est formalisée avec sévérité (`P0`..`P3`), capacité `CAP-*` / parcours `UJ-*` touché et recommandation de correction ciblée.

**Given** l'état réel constaté à l'issue de la campagne
**When** `docs/product/capabilities.yaml` est mis à jour et contrôlé par `pnpm site:check`
**Then** seules les capacités dont 100 % des assertions E2E (UI + `F5` + `SELECT` PG18) ont réussi conservent ou reçoivent `verification: runtime` (avec date `verified_at`), tandis que toute capacité touchée par au moins un échec passe honnêtement à `verification: failed_e2e`.

---

### Story 21.9: Analyse Tech Lead & Impact GitNexus (`repo: "ORCIA"`), Rapports Tech Lead Pré-Implémentation (`22-1-...` à `22-N-...`), Plan Directeur & Initialisation Complète de l'Epic 22

As a Tech Lead (`Amelia`) & Architecte (`Winston`),
I want conduire l'analyse Tech Lead et d'impact GitNexus (`repo: "ORCIA"`) pour chaque échec E2E et chaque point de la synthèse Sally × Winston, rédiger les Rapports Tech Lead pré-implémentation individuels (`22-1-...` à `22-N-...`), publier le plan directeur `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`, et initialiser complètement l'**Epic 22** dans `epics.md` et `sprint-status.yaml` avec un test automatique garantissant `100 %` de traçabilité,
So that chaque correction de l'Epic 22 démarre avec une architecture validée, zéro angle mort et une traçabilité intégrale jusqu'au retour au vert de toutes les capacités (`GEMINI.md` § Policy, `AD-17`).

**Dépendances :** Dépend de Story 21.8. Clôture l'Epic 21.
**Références :** `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md`, `docs/implementation-artifacts/e2e-campaign-epic-21/bilan-execution-tests-e2e-epic-21.md`, `docs/implementation-artifacts/e2e-campaign-epic-21/synthese-remediation-sally-winston-epic-21.md`, `GEMINI.md` (§ Protocole Tech Lead).
**Fichiers impactés :** `docs/implementation-artifacts/tech-lead-reports/22-1-*.md` .. `22-N-*.md`, `docs/implementation-artifacts/tech-lead-reports/README.md`, `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`, `docs/planning-artifacts/epics.md` (ajout Epic 22), `docs/implementation-artifacts/sprint-status.yaml` (ajout `epic-22` et `22-1-...`..`22-N-...`), `tests/unit/test_epic21_to_epic22_traceability.py`.

**Acceptance Criteria:**

**Given** l'ensemble des échecs E2E de `bilan-execution-tests-e2e-epic-21.md` et des points de remédiation de `synthese-remediation-sally-winston-epic-21.md`
**When** le Tech Lead exécute l'analyse d'impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` avec `repo: "ORCIA"`) sur les modules concernés
**Then** tous les défauts sont regroupés en `N` Stories cohérentes `Story 22.1` à `Story 22.N`, et chaque Story dispose d'un Rapport Tech Lead pré-implémentation individuel (`docs/implementation-artifacts/tech-lead-reports/22-1-...-tech-lead-report.md` .. `22-N-...`) conforme à `TECH-LEAD-REPORT-TEMPLATE.md` (Sections 1 & 2 rédigées, Section 3 préparée) et enregistré dans `docs/implementation-artifacts/tech-lead-reports/README.md`.

**Given** le plan directeur `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`
**When** il consolide la feuille de route de remédiation
**Then** il contient la matrice complète reliant chaque échec E2E, chaque constat Sally × Winston (`P0`..`P3`) et chaque `CAP-*` en `failed_e2e` à une Story `22.k`, l'ordonnancement topologique d'exécution, les migrations/refactorings requis et la condition de sortie de l'Epic 22 (`100 %` des capacités `feature` repassées à `verification: runtime`).

**Given** l'ajout de l'**Epic 22** et de ses Stories `22.1` à `22.N` dans `docs/planning-artifacts/epics.md` et `docs/implementation-artifacts/sprint-status.yaml`, ainsi que `tests/unit/test_epic21_to_epic22_traceability.py`
**When** `.venv/bin/pytest tests/unit/test_epic21_to_epic22_traceability.py` et `pnpm site:sync` + `pnpm site:check` s'exécutent
**Then** le test automatique prouve `100 %` de traçabilité bidirectionnelle (aucun échec E2E, aucun constat Sally × Winston et aucune capacité `failed_e2e` orpheline), et `epics.md`, `sprint-status.yaml` et les rapports Tech Lead sont prêts pour le démarrage de l'Epic 22.

---

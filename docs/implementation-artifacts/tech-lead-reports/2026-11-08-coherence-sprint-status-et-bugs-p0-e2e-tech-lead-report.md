# 2026-11-08 — Cohérence de `sprint-status.yaml` et correction des bugs P0 révélés par les E2E

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-coherence-sprint-status-et-bugs-p0-e2e` (`Epic 13`, tickets `BUG-E2E-01..04`)
- **Capacité(s)** : `CAP-073` (dossiers Assistant), `CAP-023` (ancrages humains / arbitrage), `CAP-040` (notifications / claim temps réel), `CAP-001` (authentification) — classification `feature` (bugfix) + `doc`
- **Branche dédiée** : `fix/p0-e2e-bugs`
- **Statut** : `in-progress`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Incohérences du suivi de sprint (constat du 2026-11-08)
1. `CAP-ACT-5` marqué `done` alors que seules 3 / 57 capacités sont en `verification: runtime`.
2. `TEST-07` marqué `done` alors que la refonte HTTP des fichiers d'intégration historiques (`test_story_9_*`, `10_*`, `11_*`) n'est pas faite.
3. `CAP-ACT-1` et `UX-DS-RADIX-01` rattachés à `epic-12` (terminé) au lieu de `epic-13`.
4. Stories `3.4`, `4.3`, `5.1` en `done` alors que leur surface UI / temps réel n'est pas utilisable (`BUG-E2E-02/03/05`) : à annoter.
5. `last_updated` obsolète.

### 1.2 Bugs P0 (à investiguer dans le code avant plan détaillé)
| Bug | Symptôme | Garde-fou violé |
| :--- | :--- | :--- |
| `BUG-E2E-04` | `resolve_user()` retombe sur la persona `marc` sans jeton ; notifications fictives semées en mémoire | Sécurité (usurpation), zéro donnée fictive |
| `BUG-E2E-01` | Dossiers Assistant non réhydratés depuis PostgreSQL après `F5` | Garde-fou n°3 (survie au F5 via `GET`) |
| `BUG-E2E-02` | `HumanLedAnchorCard` / `ArbitrationTieBreakCard` non montés dans `apps/web` | Garde-fou n°5 / câblage vertical |
| `BUG-E2E-03` | `/api/v1/events/stream` rejoue puis se ferme (pas de SSE persistant) | Règle 2 (zéro faux streaming), FR-2 |

L'étude d'impact détaillée (GitNexus) de chaque bug est consignée en Section 2 au fur et à mesure, avant chaque modification de code.

### 1.3 Résultats de l'investigation (causes racines)
| Bug | Cause racine constatée | Impact GitNexus |
| :--- | :--- | :--- |
| `BUG-E2E-04` | L'identité repose sur des **personas en mémoire** (`karim`, `claire`, `marc`, `nadia`) : `AuthAndOrganizationService.resolve_user` retombe sur `marc` sans jeton, et **tout appelant peut passer `?persona_key=karim`** (admin). Le 1er administrateur créé au Jour 0 dans PostgreSQL (`users`) n'est pas connu de `AuthAndOrganizationService`, et `apps/web` n'envoie jamais de `Bearer`. `initialize_app_services` sème 4 notifications fictives. | `resolve_user` : **CRITICAL** (90 appelants, 86 processus) ; `seed_default_notifications` : **CRITICAL** (87 dépendants) |
| `BUG-E2E-01` | `AssistantFoldersAndSharingService` est **100 % en mémoire** (`self._folders: dict`) alors que la migration `0025` crée `assistant_folders`, `assistant_threads`, `assistant_folder_shares` : adaptateur SQL manquant (garde-fou n°1). Côté web, création locale avec identifiant client puis `POST` vers un `workspace_id` de repli fictif (`…000301`), et aucun `GET` au démarrage. | Service + routeur + `apps/web/src/features/inbox/index.tsx` |
| `BUG-E2E-03` | `GET /api/v1/events/stream` lit `list_recent_events()` puis termine le générateur ; `workspace_id` par défaut fictif (`…000301`) ; aucun `EventSource` dans `apps/web`. | Routeur `inbox_and_leases.py` + broker SSE + web |
| `BUG-E2E-02` | Composants `@orcia/ui` existants mais jamais montés ; nécessite un écran de run porteur d'une ancre / d'un arbitrage (aucun run au Jour 0). | `apps/web` (nouvel écran ou panneau du cockpit) |

Chaque bug P0 relève d'une story à part entière, et non d'un correctif ponctuel. `BUG-E2E-04` en particulier impose une décision d'architecture (modèle d'authentification de bout en bout).

## 2. Plan d'Implémentation

### 2.0 Étape 0 — Cohérence documentaire
- Corriger `sprint-status.yaml` (statuts, rattachements, annotations, `last_updated`) et la ligne `CAP-ACT-5` / `TEST-07` du rapport `2026-11-08-test-07-a-10-...`.

### 2.1 BUG-E2E-04 — Correctif de sécurité borné (décision utilisateur du 2026-11-08)
- Core (`permissions`) : `AuthenticationRequiredError` (`401 ERR_AUTH_REQUIRED`, catalogue FR/EN), fonction pure `persona_impersonation_allowed(orcia_env)` (vrai seulement pour `local` / `test`), paramètre `allow_persona_impersonation` de `AuthAndOrganizationService` (défaut `False`, sûr) : sans Bearer et sans autorisation, `resolve_user` lève `AuthenticationRequiredError` et ignore tout `persona_key`.
- Composition Root : `allow_persona_impersonation=persona_impersonation_allowed(ORCIA_ENV)` ; notifications d'amorce semées uniquement si `ORCIA_E2E_SEED_FIXTURES=1` (posé par `infra/scripts/e2e/e2e_stack_config.py`).
- Hors périmètre (ticket `AUTH-01`) : authentification sur la table `users`, jeton envoyé par `apps/web`, lecture d'`ORCIA_ENV` / `ORCIA_BOOTSTRAP_TOKEN` dans `get_accostage_service`, persistance des notifications.
- Pyramide : Couche Sécurité (`tests/security/test_authentication_enforcement.py`, 12 tests) ; Couche 1 (`test_story_5_1_*` arrange explicite des notifications) ; Couche 5 : la pile E2E reste en `local` et sème ses fixtures, spec `04` inchangée.

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.0 Étape 0 — Cohérence documentaire (faite)
| Élément | Avant | Après |
| :--- | :--- | :--- |
| `CAP-ACT-5` | `done` | `in-progress` (54/54 capacités live testées, mais 3/57 en `runtime`) |
| `TEST-07` | `done` | `review` (reste : refonte HTTP des fichiers historiques `test_story_9_*`, `10_*`, `11_*`) |
| `CAP-ACT-1`, `UX-DS-RADIX-01` | `epic-12` | `epic-13` |
| Stories `3.4`, `4.3`, `5.1` | `done` sans réserve | `done` + annotation renvoyant vers `BUG-E2E-02/05/03` |
| Story `13.1` | `review` | `review` justifié (attend CAP-ACT-1 / CAP-ACT-5) |
| `last_updated` | 09:30 | 14:40 |

### 3.1 BUG-E2E-04 (fait — correctif borné)
| Fichier | Modification |
| :--- | :--- |
| `packages/orcia-core/src/orcia_core/permissions/errors.py` | `AuthenticationRequiredError` + entrée de catalogue `ERR_AUTH_REQUIRED` (FR/EN) |
| `packages/orcia-core/src/orcia_core/permissions/service.py` | `persona_impersonation_allowed`, paramètre `allow_persona_impersonation`, refus sans Bearer |
| `packages/orcia-core/src/orcia_core/permissions/__init__.py` | Export + paramètre du constructeur de topologie de référence |
| `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` | Lecture d'`ORCIA_ENV`, suppression des notifications fictives hors pile E2E |
| `infra/scripts/e2e/e2e_stack_config.py` | `ORCIA_E2E_SEED_FIXTURES=1` |
| `tests/security/test_authentication_enforcement.py` | Nouveau (12 tests : 401 sans Bearer, 401 malgré `persona_key=karim`, Bearer valide accepté, persona en local, zéro notification au démarrage) |
| `tests/security/test_api_security_baseline.py`, `tests/unit/test_story_5_1_*` | Sonde inversée / arrange explicite |

- Vérifications : `pytest tests/security` 33 passés ; `pytest tests/unit tests/contract tests/conformance tests/evals` (hors conteneurs) vert sauf 2 échecs **préexistants sur `main`** (`test_ac_e2_*`, `test_ac_f2_*`) → ticket `TEST-HYG-01` ; `ruff`, `mypy --strict`, `lint-imports` (5/5) verts.
- Impact GitNexus pré-édition : `resolve_user` et `seed_default_notifications` **CRITICAL** ; comportement inchangé en `local` / `test` (défaut de la pile E2E et des tests), seul le mode non local change.

### 3.2 BUG-E2E-01 (fait côté portail ; persistance SQL → BUG-E2E-01b)
Constat complémentaire : l'adaptateur SQL ne peut pas être livré sans `AUTH-01` (clé étrangère `assistant_folders.owner_user_id → users(id)` alors que l'identité API est une persona en mémoire).

| Fichier | Modification |
| :--- | :--- |
| `apps/web/src/features/inbox/useServerAssistantFolders.ts` | Nouveau hook : réhydratation `GET …/overview`, création / notes / visibilité via l'API, identifiants serveur, refus explicite sans espace, erreurs remontées |
| `apps/web/src/features/inbox/index.tsx` | Branchement du hook ; suppression de l'identifiant client fabriqué et de l'espace de repli fictif `…000301` |
| `packages/api-client/src/domains/bootstrapAndOntology.ts` | Méthode typée `configureAssistantFolderSharing` |
| `apps/web/src/i18n/locales/assistant_labels.ts` | Messages FR/EN `assistantFoldersSync` |
| `apps/web/src/__tests__/vitest.setup.ts` | Backend simulé à état pour les dossiers (POST / share / overview) + `seedVitestPlatformSetupState` |
| `apps/web/src/__tests__/assistant-folders-server-rehydration.test.tsx` | Nouveau (4 tests : survie au F5 via GET, refus sans espace, notes + visibilité persistées, erreur affichée) |
| `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` | Espace réel pré-rempli, attente de l'aller-retour serveur |
| `apps/web/e2e/02-assistant-streaming-and-folders.spec.ts` | Création d'un espace réel, attente du `GET overview` après F5, `test.fail` retiré ; `test.fixme` « survit au redémarrage de l'API » (BUG-E2E-01b) |

- Vérifications : `pnpm turbo run lint typecheck test` (web 47, ui 68, api-client 8) vert ; **E2E 02 sur pile isolée : 2 passés, 1 `fixme`**.
- Correction annexe : la documentation `docs/testing-strategy.md` (et ses reprises dans `README.md`, `architecture.md`, `AGENTS.md`) citait des ports, scripts et fichiers E2E inexistants (`:55433`, `pnpm test:e2e:up`, `refuse_if_not_e2e_target`, `test_rag_hybrid_rrf_eval.py`…) ; remplacés par les mécanismes réels (`testcontainers`, API `:8100`, web `:3101`, `is_isolated_e2e_database_url`, `pnpm e2e`) et chaque lien de fichier vérifié.

### 3.3 BUG-E2E-03, 02
_En cours._

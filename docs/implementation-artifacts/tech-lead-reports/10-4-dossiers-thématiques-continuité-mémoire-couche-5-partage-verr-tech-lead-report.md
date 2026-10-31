# Tech Lead Analysis & Implementation Report — Story 10.4 : Dossiers Thématiques (`📁 Dossiers`), Continuité Mémoire Couche 5, Partage Collaboratif (`🔒 Privé | 👥 Partagé | 📦 Espace`) & Verrou de Tour Redis

- **Story Key** : `10-4-dossiers-thématiques-continuité-mémoire-couche-5-partage-verr`
- **Epic** : Epic 10 — Expérience `Mon Assistant` All-in-One (`AD-15`, `AD-4`, `AD-6`, `AD-21`)
- **Date** : 2026-10-31
- **Auteur** : Antigravity (Tech Lead / Senior Dev)
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte & Problématique Métier (`epics.md`, `ARCHITECTURE-SPINE.md`, `DESIGN.md`)
Un assistant conversationnel d'entreprise perd 80 % de sa valeur si chaque nouvelle discussion repart d'une page blanche ou si deux membres d'une équipe ne peuvent pas co-construire un cadrage dans un même dossier thématique sans s'écraser mutuellement ni partager accidentellement leurs jetons d'accès personnels (`Passthrough OIDC/PAT`).

La **Story 10.4** clôt l'**Epic 10** en dotant `Mon Assistant` de :
1. **L'organisation en 3 onglets sobres (`Principe K.6`, Composant 15)** :
   - `💬 Discussion active` (avec pilule sélecteur `📁 Dossier : [Nom] ⌄` et tiroir `📌 Notes du dossier`),
   - `📁 Dossiers (N)` (grille des dossiers thématiques de l'Espace),
   - `🕘 Historique & Recherche` (recherche transversale dans les discussions, dossiers et cartes d'artefacts).
2. **La continuité mémoire automatique en Couche 5 (`AD-15`) & Passerelle Processus en 1 clic** :
   - Toute discussion rattachée à un `📁 Dossier` (ex. `📁 Refonte Tunnel Checkout`) injecte automatiquement en **Couche 5 (`5_UTILISATEUR / DOSSIER`)** :
     - les décisions épinglées dans `📌 Notes du dossier`,
     - les pièces jointes et brouillons d'artefacts (`@draft`) du dossier,
     - les résumés consolidés des discussions précédentes du même dossier.
   - Le bouton **`☍ Lancer un Processus à partir de ce dossier →`** pré-remplit en 1 clic le `Contrat du workflow` d'un Processus (notamment le **Workflow Pilote Semaine 1 `orcia://pack-sdlc/workflows/ticket-to-tech-spec`**) avec la synthèse consolidée du dossier, les notes épinglées et les preuves `[S1..Sn]`.
3. **Le partage collaboratif à 3 niveaux de visibilité strictement confinés à l'Espace courant (`AD-21`)** :
   - `PRIVATE` (`🔒 Privé`, par défaut),
   - `SHARED_SELECTED` (`👥 Partagé avec des collègues choisis` de l'Espace en `READ_ONLY` `👁️ Lecture seule` ou `CO_CONTRIBUTOR` `✍️ Co-contributeur`),
   - `WORKSPACE_OPEN` (`📦 Ouvert à tout l'Espace`),
   - Rejet strict (`HTTP 403 ERR_SCOPE_ACCESS_DENIED`) de toute tentative de partage avec un utilisateur hors de l'Espace courant (`workspace_id`),
   - Avertissement préventif explicite dans la modale de partage dès lors que le dossier ou la discussion référence des sources restreintes (`🔒 Source restreinte` filtrées par lecteur via la Story 10.3).
4. **Le verrou de tour Redis léger & l'isolation stricte `Passthrough` par auteur de message (`AD-6`)** :
   - Lorsqu'un **Co-contributeur (`✍️`)** envoie un message dans une discussion partagée, le moteur acquiert de manière atomique le verrou Redis **`SET lock:thread:<thread_id> <user_id> NX EX 60`** (`HTTP 409 ERR_THREAD_TURN_LOCK_HELD` si un pair interroge déjà l'assistant),
   - Diffuse en temps réel via SSE l'indicateur **`✍️ {Prénom} interroge l'assistant...`**,
   - Exécute tous les connecteurs externes et outils MCP exclusivement sous **l'identité `Passthrough` personnelle de l'auteur du message courant** (`author_passthrough_user_id = sender.id`, jamais le jeton du créateur initial du dossier).

### 1.2 Analyse d'Impact GitNexus
- `gitnexus_impact({target: "AssistantCitationAndV5GuardService", direction: "upstream", repo: "ORCIA"})` : `0` appelant cassé (`risk: LOW`).
- Création d'un module dédié `packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py` (`< 380` lignes) respectant `AD-19` (`0` import de framework dans `orcia_core`).

### 1.3 Opportunités de Factorisation & Dette Technique
- Réutilisation directe de `ThreadTurnLockHeldError` (`ERR_THREAD_TURN_LOCK_HELD`, HTTP 409) et `ScopeAccessDeniedError` (`ERR_SCOPE_ACCESS_DENIED`, HTTP 403) déjà déclarés dans `orcia_core.orchestration.errors`.
- Aucune dette technique résiduelle sur l'Epic 10.

---

## 2. Plan d'Implémentation

### 2.1 Migration Alembic (`0025_story_10_4_assistant_folders_and_threads.py`)
- Création des tables PostgreSQL 18 (clés primaires `UUIDv7`, SQL brut idempotent avec `upgrade()` / `downgrade()`) :
  - `assistant_folders` (`folder_id`, `workspace_id`, `owner_user_id`, `title`, `pinned_notes_markdown`, `visibility_mode` `CHECK IN ('PRIVATE', 'SHARED_SELECTED', 'WORKSPACE_OPEN')`, `consolidated_summary`, `has_restricted_sources`, `created_at`, `updated_at`),
  - `assistant_threads` (`thread_id`, `workspace_id`, `folder_id`, `creator_user_id`, `title`, `thread_summary`, `turn_count`, `last_author_user_id`, `last_author_passthrough_identity`, `created_at`, `updated_at`),
  - `assistant_folder_shares` (`share_id`, `folder_id`, `workspace_id`, `grantee_user_id`, `access_role` `CHECK IN ('READ_ONLY', 'CO_CONTRIBUTOR')`, `created_at`).

### 2.2 Noyau Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py`)
- `AssistantFoldersAndSharingService` :
  - `create_or_update_folder(...)` : création/mise à jour de `📁 Dossier`, épinglage de `📌 Notes du dossier` et pièces jointes.
  - `build_layer5_folder_memory_injection(...)` : assemblage déterministe de la **Couche 5 (`AD-15`)** injectant notes épinglées, brouillons `@draft` et résumés consolidés des discussions précédentes du dossier.
  - `prepare_workflow_launch_from_folder(...)` : pré-remplissage en 1 clic du contrat d'entrée d'un Processus (`orcia://pack-sdlc/workflows/ticket-to-tech-spec` par défaut) à partir du dossier.
  - `configure_folder_sharing(...)` : gestion des 3 niveaux de visibilité (`PRIVATE`, `SHARED_SELECTED`, `WORKSPACE_OPEN`), confinement strict aux membres de l'Espace courant et génération de l'avertissement préventif sur les sources restreintes.
  - `send_collaborative_thread_turn(...)` : acquisition atomique du verrou de tour Redis `SET lock:thread:<thread_id> <user_id> NX EX 60`, émission de l'indicateur SSE `✍️ {Prénom} interroge l'assistant...` et exécution sous identité `Passthrough` personnelle de l'auteur du message (`AD-6`).
  - `search_history(...)` : recherche dans le 3e onglet `🕘 Historique & Recherche` (discussions, dossiers, artefacts).

### 2.3 Backend FastAPI & SDK OpenAPI (`apps/api`)
- Nouveaux endpoints dans `apps/api/src/orcia_api/routers/epic10_assistant.py` :
  - `POST /api/v1/assistant/folders`
  - `POST /api/v1/assistant/folders/{folder_id}/share`
  - `POST /api/v1/assistant/folders/{folder_id}/launch-process`
  - `POST /api/v1/assistant/threads/{thread_id}/turns`
  - `GET /api/v1/assistant/workspaces/{workspace_id}/overview`

### 2.4 Interface SPA `@orcia/ui` (`packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx`)
- Composant Direction C implémentant les 3 onglets (`💬 Discussion active` avec pilule `📁 Dossier ⌄` et `📌 Notes du dossier`, `📁 Dossiers (N)` avec bouton `☍ Lancer un Processus à partir de ce dossier →`, `🕘 Historique & Recherche`), la modale de partage à 3 niveaux avec alerte sur les sources restreintes, et la bannière temps réel `✍️ {Prénom} interroge l'assistant...`.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Fichiers Créés / Modifiés
| Fichier | Action | Rôle |
| :--- | :--- | :--- |
| `infra/migrations/versions/0025_story_10_4_assistant_folders_and_threads.py` | Créé | Tables PG18 `assistant_folders`, `assistant_threads`, `assistant_folder_shares` |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py` | Créé | Service `AssistantFoldersAndSharingService` (Couche 5, partage, verrou Redis `NX EX 60`, `Passthrough`) |
| `apps/api/src/orcia_api/schemas/assistant.py` | Modifié | Schémas Pydantic v2 de la Story 10.4 |
| `apps/api/src/orcia_api/dependencies.py` | Modifié | Injection `get_assistant_folders_and_sharing_service` |
| `apps/api/src/orcia_api/routers/epic10_assistant.py` | Modifié | Routes REST Story 10.4 |
| `packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx` | Créé | Primitive UI Direction C 3 onglets + partage + verrou de tour |
| `packages/ui/src/__tests__/epic10-assistant.test.tsx` | Modifié | Tests Vitest Story 10.4 |
| `tests/unit/test_epic_10_story_10_4_folders_and_sharing.py` | Créé | Tests unitaires & API Story 10.4 |
| `tests/integration/test_story_10_4_folders_and_turn_lock_postgres18_redis.py` | Créé | Tests d'intégration réels PG18 + Redis 7.4 `testcontainers` |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Frontières (`AD-19`)
- `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **PASS (`0` erreur)**
- `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : **PASS (`0` issue)**
- `.venv/bin/lint-imports` : **PASS (`8 kept, 0 broken`)**
- `.venv/bin/pytest` (unitaires + intégration PG18 & Redis 7.4 `testcontainers`) : **PASS**
- `pnpm turbo run lint typecheck test` : **PASS**

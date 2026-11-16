# 2026-11-16 — Cadrage Architectural & Produit : Délégation Hiérarchique de l'Organigramme (BU_LEAD / TEAM_LEAD), Invitation Scopée de Comptes & Garde Anti-Auto-Éviction

- **Date** : `2026-11-16`
- **Story / Clé Sprint** : `2026-11-16-cadrage-delegation-hierarchique-bu-equipe-et-invitation-comptes` (`Cadrage Architectural & Planification Backlog — IAM-ORG-DELEGATION-01 & UX-AUTH-DOUBLE-ICON-01`)
- **Capacité(s)** : `CAP-050`, `CAP-051`, `CAP-058`, `CAP-067` (cibles à mettre à jour lors de l'implémentation de `IAM-ORG-DELEGATION-01`) — classification : `doc` (préparant une évolution `feature | ux | sécurité`)
- **Auteur / Contexte** : Analyse de bout en bout suite au constat utilisateur et à la capture de référence `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/screenshots/2026-11-16-bu-lead-settings-readonly-et-doubles-icones.png` (`Rouge Gorge · Responsable de Direction (BU)` bloquée en lecture seule sur `/settings`). Couvre `FR-21`, `FR-22`, `FR-31`, `AD-6`, `AD-17`, `AD-19`, `AD-21`, `UX-DR1`.
- **Commits associés** : *(phase de cadrage et planification documentaire — aucune modification de code applicatif à ce stade)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte, Preuve Terrain & Diagnostic des 3 Verrous (UI, Domaine, API)

Lors de la connexion avec le compte `Rouge Gorge` (`rouge.gorge@orcia.ia`), pourtant titulaire du rôle **Responsable de Direction (`BU_LEAD`)**, l'utilisateur constate qu'il lui est impossible de gérer l'organisation de sa BU (créer des sous-BUs, créer des équipes, ajouter/gérer des responsables sur sa BU ou sur les unités en dessous), tout comme un responsable d'équipe (`TEAM_LEAD`) ne peut pas gérer son équipe.

La capture d'écran archivée (`docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/screenshots/2026-11-16-bu-lead-settings-readonly-et-doubles-icones.png`) démontre le blocage sur `/settings` : l'écran affiche exclusivement la bannière **« Accès en lecture seule sur la configuration de la plateforme »** avec un unique bouton `Ouvrir Mon Compte`.

L'exploration du codebase confirme **3 verrous structurels superposés** :

1. **Frontend (`apps/web`) — Blocage total de la navigation et de `/settings`** :
   - **Menu latéral masqué** : `apps/web/src/components/shellPresets.ts:L33-L52` (`evaluateScopeModuleVisibility`) conditionne l'entrée `Configuration` (`/settings`) à `bootstrap: role === "PLATFORM_ADMIN"`, masquant l'entrée pour `BU_LEAD` et `TEAM_LEAD`.
   - **Onglets vidés et écran bloqué en lecture seule** : lors du chantier `2026-11-15-politique-authentification-exclusive-2fa-et-isolation-locale` (qui a remplacé l'ouverture adaptative initialement prévue par `Story 17.1`), `apps/web/src/stores/settingsRbacResolver.ts:L34, L70-L101` a figé `SCOPED_LEAD_SETTINGS_TABS: readonly SettingsTabKey[] = [] as const` et imposé `isPlatformAdministratorSession` (`session.roles.includes("PLATFORM_ADMIN") && session.activeHat === "PLATFORM_ADMIN"`). Pour tout `BU_LEAD` ou `TEAM_LEAD`, `resolveSettingsAccess` retourne désormais `visibleTabs: []`, `canMutate: false` et `isReadOnlyRestricted: true`.
   - **Écran `/settings` verrouillé** : `apps/web/src/routes/settings.tsx:L158-L200` bascule immédiatement sur `settings-readonly-access-banner` dès que `isReadOnlyRestricted || effectiveTab === null`, et encapsule en plus l'arbre organisationnel dans `<PermissionGuard scopePath="GLOBAL" verb="read">`.
   - **Absence d'écran alternatif et de filtrage contextuel** : `/workspaces` (`apps/web/src/features/workspaces/CreateWorkspaceCard.tsx`) ne permet de créer que des *Espaces*, jamais des sous-BUs ni des équipes. Les composants `SettingsOrganizationUnitsBlock.tsx`, `CreateOrgUnitModal.tsx`, `EditOrgUnitModal.tsx`, `ManageOrgUnitMembersModal.tsx` et `ConfirmDeleteOrgUnitModal.tsx` ne disposent d'aucun filtrage de parenté ni d'édition borné au sous-arbre du responsable connecté.

2. **Domaine (`packages/orcia-core/src/orcia_core/permissions/`) — Absence de gouvernance descendante sur les mutations d'unités et d'invitations** :
   - **Acquis existants** : le socle SQL/domaine supporte déjà la hiérarchie multi-niveaux sans plafond (`ENTERPRISE -> BU -> Sous-BU -> TEAM` dans `0002`, `20261111_1702`, `20261115_1902`, et `org_hierarchy.py:L148-L150` qui interdit seulement une `BU` sous une `TEAM`), les co-responsables multiples (`lead_user_ids_jsonb`), l'interdiction des membres directs sur une BU (`chk_org_units_bu_no_members`) et la synchronisation bidirectionnelle transactionnelle B1 `lead_user_ids ↔ BU_LEAD / TEAM_LEAD` (`sql_org_iam_role_sync.py:L108-L150`).
   - **Manque constaté** : bien que la matrice native (`packages/orcia-core/src/orcia_core/permissions/role_matrix.py:L159-L184`) accorde à `BU_LEAD` les verbes `("create", "read", "update", "delete")` au scope `BU` et à `TEAM_LEAD` les verbes `("read", "update")` au scope `TEAM` sur `org_units`, `MatrixPermissionEvaluator` (`packages/orcia-core/src/orcia_core/permissions/evaluator.py:L121-L209`) n'exploite `is_ancestor_of` / `get_descendant_org_unit_ids` **que** pour `resolve_workspace_access` et le roll-up FinOps. Aucune règle métier n'encadre la délégation descendante de gestion des unités ou d'invitation de nouveaux comptes.

3. **Backend API (`apps/api`) — Garde RBAC globale plate & absence de garde d'invitation déléguée** :
   - **Isolation latérale et écart à la matrice sur `/api/v1/org-units`** : dans `apps/api/src/orcia_api/routers/_org_units_helpers.py:L83-L102`, `enforce_org_unit_mutation_access` se contente de vérifier que `active_hat` / `platform_role` appartient à `ADMIN_MODULE_ALLOWED_ROLES` (`PLATFORM_ADMIN`, `BU_DIRECTOR`/`BU_LEAD`, `TEAM_LEAD` — `evaluator.py:L26-L28`) sur `org_units.py:L134-L310`, **sans jamais vérifier** que `org_unit_id` ou `parent_id` appartient au sous-arbre dirigé par l'acteur :
     - par appel HTTP direct, une `BU_LEAD` d'une BU `A` pourrait muter une BU `B` ou créer une BU racine (`parent_id = None`) ;
     - un `TEAM_LEAD` passe aujourd'hui le garde sur `POST /api/v1/org-units` et `DELETE /api/v1/org-units/{id}`, en contradiction directe avec `role_matrix.py:L175-L182`.
   - **Absence d'invitation / création déléguée de comptes IAM** : `apps/api/src/orcia_api/routers/iam_accounts.py:L114-L148` et `_iam_accounts_passwords.py:L43-L66` appliquent une garde globale sans politique de périmètre délégué permettant à un `BU_LEAD` ou `TEAM_LEAD` de créer de nouveaux comptes humains bornés à leur sous-arbre tout en bloquant toute escalade vers `PLATFORM_ADMIN`, `SECOPS` ou `SERVICE_PRINCIPAL`.

4. **Anomalie visuelle connexe relevée sur la capture (`UX-AUTH-DOUBLE-ICON-01`)** :
   - Coexistence d'une icône SVG `<OrciaIcon />` et d'un emoji/glyphe en dur créant une double icône visible (`⚠️ ⚠️` sur `TemporaryPasswordWarningBanner`, et `⚙️ ⚙️` / `🔗 🔗` dans le menu `UserAccountDropdownMenu`).

---

### 1.2 Arbitrages Produit & Sécurité Validés (Décisions D1, D2, D3)

Trois arbitrages explicites ont été validés avec le commanditaire le `2026-11-16` pour cadrer l'implémentation cible :

#### Décision D1 — Délégation effective de l'invitation / création de nouveaux comptes humains par les Leads sur leur périmètre
`PLATFORM_ADMIN` n'est **pas** le seul rôle autorisé à créer de nouveaux comptes dans ORCIA. Un `BU_LEAD` ou un `TEAM_LEAD` doit pouvoir à la fois rattacher des comptes existants (`GET /api/v1/org-units/known-users`) **et** inviter/créer de nouveaux comptes humains (`account_kind = "HUMAN"`, avec modale de mot de passe temporaire 12 car. `TemporaryPasswordInvitationModal` en mode `LOCAL` ou compte `OIDC_FEDERATED` pré-habilité en mode `SSO`) dès lors que l'opération reste strictement confinée à son périmètre dirigé :

| Rôle de l'acteur | Périmètre cible autorisé | Rôles attribuables lors de la création / invitation | Restrictions anti-escalade strictes (`HTTP 403`) |
| :--- | :--- | :--- | :--- |
| **`BU_LEAD`** | Sa/ses BU(s) `B` et tout le sous-arbre descendant `B*` (sous-BUs et équipes rattachées sous `B`) | `CONTRIBUTOR` / `OBSERVER` (membre d'au moins une équipe de `B*`), `TEAM_LEAD` (co-responsable d'au moins une équipe de `B*`), `BU_LEAD` (co-responsable de `B` ou d'une sous-BU de `B*`) | Interdiction de créer un `SERVICE_PRINCIPAL`, d'attribuer `PLATFORM_ADMIN` ou `SECOPS`, de modifier un compte détenant `PLATFORM_ADMIN`/`SECOPS`, ou d'inviter sans rattachement à `B*` / hors de `B*` (`ERR_IAM_DELEGATION_SCOPE_EXCEEDED` / `ERR_GRANT_ESCALATION_FORBIDDEN`) |
| **`TEAM_LEAD`** | Exclusivement l'équipe ou les équipes `T` dont il est lui-même `TEAM_LEAD` | `CONTRIBUTOR` / `OBSERVER` (membre de `T`), `TEAM_LEAD` (co-responsable de `T`) | Interdiction de créer un `SERVICE_PRINCIPAL`, d'attribuer `PLATFORM_ADMIN`, `SECOPS` ou `BU_LEAD`, de modifier un compte hors de `T` ou détenant des privilèges supérieurs, ou d'inviter sans rattachement à `T` |

#### Décision D2 — Matrice de gestion de l'organigramme par sous-arbre & Garde-fou anti-auto-éviction
La gestion hiérarchique de l'organigramme applique la matrice suivante, doublée d'un garde-fou explicite empêchant de laisser une unité orpheline de responsable :

| Action sur `org_units` | `PLATFORM_ADMIN` | `BU_LEAD` (sur BU `B` dirigée et sous-arbre descendant `B*`) | `TEAM_LEAD` (sur équipe `T` dirigée) |
| :--- | :--- | :--- | :--- |
| **Consulter l'organigramme** | Entreprise entière | Sous-arbre(s) `B*` éditable(s) + chaîne d'ancêtres affichée en lecture seule pour contexte | Équipe(s) `T` éditable(s) + chaîne d'ancêtres BU affichée en lecture seule |
| **Créer une BU racine (`parent_id = None`)** | Oui | **Non** (`HTTP 403 ERR_ORG_UNIT_OUTSIDE_DELEGATED_SCOPE`) | **Non** (`403`) |
| **Créer une Sous-BU (`kind="BU"`, `parent_id ∈ B*`)** | Oui | **Oui** (sous `B` ou toute sous-BU de `B*`) | **Non** (`403`) |
| **Créer une Équipe (`kind="TEAM"`, `parent_id ∈ B*`)** | Oui | **Oui** (sous `B` ou toute sous-BU de `B*`) | **Non** (`403`) |
| **Modifier sa propre unité racine déléguée (`B` ou `T`)** | Oui | **Oui** : nom, `billing_enabled`, co-responsables `lead_user_ids` — sans déplacer `parent_id` vers un parent hors de ses BUs dirigées | **Oui** : nom, membres `member_user_ids`, co-responsables `lead_user_ids` — **sans changer `parent_id` ni `billing_enabled`** |
| **Modifier une sous-BU ou équipe descendante (`⊂ B*`)** | Oui | **Oui** : nom, `parent_id` (confiné dans `B*`), co-responsables `lead_user_ids`, membres d'équipe `member_user_ids`, `billing_enabled` | N/A (pas de sous-unité sous `TEAM`) |
| **Supprimer une unité (`DELETE`)** | Oui (si vide `409`) | **Oui uniquement sur les sous-BUs et équipes strictement descendantes de `B`** (interdiction de supprimer sa propre BU racine `B`) | **Non** (`403`) |

- **Garde-fou anti-auto-éviction / anti-unité orpheline (`HTTP 422 ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN`)** : un `BU_LEAD` ou `TEAM_LEAD` agissant par délégation (hors `PLATFORM_ADMIN` et hors `BU_LEAD` intervenant depuis une BU ancêtre strictement supérieure sur une sous-BU/équipe enfant) ne peut pas vider `lead_user_ids` (`0` responsable restant) ni se retirer lui-même lorsqu'il est le seul responsable de l'unité.

#### Décision D3 — Ticket UX dédié pour les doubles icônes (`UX-AUTH-DOUBLE-ICON-01`)
Les doubles icônes observées sur la capture (`⚠️ ⚠️` dans le bandeau mot de passe temporaire et `⚙️ ⚙️` / `🔗 🔗` dans le menu Mon Compte) sont isolées dans un ticket distinct `UX-AUTH-DOUBLE-ICON-01` (`P3`) afin de garder `IAM-ORG-DELEGATION-01` strictement concentré sur le périmètre RBAC/IAM/Organisation.

---

### 1.3 Exploration, Analyse Volumétrique & Factorisation Prévue (`<= 350` lignes)

- **Audit volumétrique des modules concernés** :
  - `packages/orcia-core/src/orcia_core/permissions/hierarchical_rbac.py` : `485` lignes (`DEBT-RBAC-SPLIT-01` déjà ouvert).
  - `packages/orcia-core/src/orcia_core/permissions/evaluator.py` : `354` lignes.
  - `packages/orcia-core/src/orcia_core/permissions/iam_accounts.py` : `369` lignes.
  - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` : `383` lignes.
  - `apps/api/src/orcia_api/routers/_org_units_helpers.py` : `378` lignes.
  - `apps/api/src/orcia_api/routers/iam_accounts.py` : `360` lignes.
- **Découpage & factorisation imposés lors de l'implémentation de `IAM-ORG-DELEGATION-01`** :
  1. Isoler la logique pure de portée descendante et de garde anti-auto-éviction dans un module dédié `< 250` lignes : `packages/orcia-core/src/orcia_core/permissions/org_delegation.py` (zéro import SQL/framework).
  2. Isoler les règles pures d'invitation/création déléguée de comptes humains et les vérifications anti-escalade dans `packages/orcia-core/src/orcia_core/permissions/iam_delegated_invitation.py` (`< 220` lignes).
  3. Découper `_org_units_helpers.py` (`378` L) et `routers/iam_accounts.py` (`360` L) avant d'y raccorder les contrôles de délégation pour maintenir chaque fichier sous `300–350` lignes.
- **Alignement `capabilities.yaml` & `sprint-status.yaml`** :
  - Aucun chevauchement avec les stories `backlog` des Epics 6 et 7.
  - Lors de l'implémentation de `IAM-ORG-DELEGATION-01`, mettre à jour les surfaces/notes/tests de **`CAP-050`**, **`CAP-051`**, **`CAP-058`** (coquille `/settings` adaptative par rôle) et **`CAP-067`**.

---

## 2. Plan d'Implémentation Cible (Pour Exécution Ultérieure de `IAM-ORG-DELEGATION-01`)

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/`)
- **Aucune migration DDL requise** : le schéma PostgreSQL 18 existant (`org_units` avec `parent_id`, `lead_user_ids_jsonb`, `member_user_ids_jsonb`, `chk_org_units_bu_no_members` et `iam_accounts` avec `roles_jsonb`, `account_kind`, `auth_source`) couvre déjà intégralement l'arbre multi-niveaux, les co-responsables multiples et les comptes humains créés par délégation.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/src/orcia_core/permissions/`)
- **`org_delegation.py`** (module pur `AD-19`, zéro import SQL/FastAPI) :
  - `resolve_delegated_org_scope(actor, units)` : calcule l'ensemble des BU dirigées (`led_bu_ids`), leur fermeture transitive descendante (`managed_bu_subtree_ids`, `managed_team_ids`) et les équipes dirigées directement (`led_team_ids`).
  - `compute_org_unit_actor_capabilities(actor, unit, scope)` : calcule les droits effectifs par nœud (`can_edit`, `can_manage_members`, `can_create_child`, `can_delete`, `can_move_parent`, `can_toggle_billing`).
  - `assert_can_create_org_unit(...)`, `assert_can_update_org_unit(...)`, `assert_can_delete_org_unit(...)` : application stricte de la matrice D2 et du garde-fou anti-auto-éviction (`LastOrgUnitLeadRemovalForbiddenError`, HTTP `422 ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN`).
- **`iam_delegated_invitation.py`** (module pur `AD-19`) :
  - `assert_can_delegate_invite_account(actor, request, units)` : valide que l'acteur est `PLATFORM_ADMIN` ou un `BU_LEAD`/`TEAM_LEAD` agissant exclusivement sur un compte `HUMAN`, sans rôle privilégié (`PLATFORM_ADMIN`, `SECOPS`, ni `BU_LEAD` pour un `TEAM_LEAD`), et avec au moins un rattachement (`led_bu_ids`, `led_team_ids`, `team_ids`) intégralement inclus dans le périmètre dirigé de l'acteur.
- **`errors.py` & `_error_catalog.py`** : ajout des erreurs bilingues FR/EN RFC 9457 `OrgUnitOutsideDelegatedScopeError` (`403 ERR_ORG_UNIT_OUTSIDE_DELEGATED_SCOPE`), `LastOrgUnitLeadRemovalForbiddenError` (`422 ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN`) et `IamDelegationScopeExceededError` (`403 ERR_IAM_DELEGATION_SCOPE_EXCEEDED`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **`schemas/org_unit_models.py` & `schemas/iam_accounts.py`** :
  - Ajouter les droits calculés par nœud dans `OrgUnitResponse` (`can_edit`, `can_manage_members`, `can_create_child`, `can_delete`, `can_move_parent`, `can_toggle_billing`) et exposer les métadonnées d'invitation déléguée si nécessaire.
- **`routers/org_units.py` & `_org_units_helpers.py` (découpé)** :
  - Sur `GET /api/v1/org-units` : renvoyer l'arbre visible contextualisé (ancêtres en lecture seule + sous-arbre/équipes gérées avec leurs booléens `can_*`).
  - Sur `POST /api/v1/org-units`, `PATCH /api/v1/org-units/{id}`, `DELETE /api/v1/org-units/{id}` : remplacer la garde plate actuelle par `assert_can_create_org_unit`, `assert_can_update_org_unit`, `assert_can_delete_org_unit` et rejeter `READ_ONLY_OBSERVER` (`403 ERR_OBSERVER_MODE_READ_ONLY`).
- **`routers/iam_accounts.py` & `_iam_accounts_passwords.py`** :
  - Autoriser `POST /api/v1/settings/iam/accounts` (ou route dédiée scopée `/api/v1/org-units/invite-member` + garde unifiée) pour `BU_LEAD` et `TEAM_LEAD` sous contrôle strict de `assert_can_delegate_invite_account`, en réutilisant la génération de mot de passe temporaire 12 car. (en mode `LOCAL`) et la synchronisation transactionnelle B1 (`sql_org_iam_role_sync.py`), tout en maintenant `GET/PATCH/DELETE` globaux d'annuaire strictement verrouillés hors `PLATFORM_ADMIN` / `SECOPS`.
- **`packages/api-client/`** : régénérer le SDK OpenAPI 3.1 (`scripts/export_openapi.py`, porte `0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `packages/ui/`)
- **Navigation & Résolveur RBAC (`shellPresets.ts`, `settingsRbacResolver.ts`, `routes/settings.tsx`)** :
  - Rétablir la visibilité de `Configuration` pour `BU_LEAD` et `TEAM_LEAD` (`evaluateScopeModuleVisibility`).
  - Fixer `SCOPED_LEAD_SETTINGS_TABS = ["organization"] as const` : `BU_LEAD` et `TEAM_LEAD` accèdent uniquement à l'onglet **`Organisation`** (`/settings?tab=organization`), tandis que `iam` (Annuaire global & Exceptions SecOps), `authentication`, `models`, `connectors` et `packs` restent strictement invisibles et bloqués hors `PLATFORM_ADMIN` / `SECOPS`.
  - Remplacer `<PermissionGuard scopePath="GLOBAL" verb="read">` sur l'onglet `organization` par un contrôle scopé cohérent avec `resolveSettingsAccess`.
- **Composants Organisation & Modale `+ Nouveau membre` (`apps/web/src/features/admin/organization/` & `SettingsOrganizationUnitsBlock.tsx`)** :
  - Piloter les boutons d'action ligne par ligne (`Modifier`, `Membres`, `+ Nouvelle unité`, `Supprimer`) via les booléens `can_*` renvoyés par l'API.
  - Filtrer les sélecteurs d'unité parente dans `CreateOrgUnitModal` et `EditOrgUnitModal` pour ne proposer que les BUs/sous-BUs du sous-arbre dirigé (sans option *Racine* pour un `BU_LEAD`).
  - Activer le bouton chaîné `+ Nouveau membre` dans les modales d'unité pour les `BU_LEAD` et `TEAM_LEAD`, en pré-remplissant et bornant les rôles et unités assignables à leur périmètre (zéro case `PLATFORM_ADMIN` / `SECOPS`, zéro `SERVICE_PRINCIPAL`), et en affichant la `TemporaryPasswordInvitationModal` après création en mode `LOCAL`.
  - Afficher un retour explicite si l'utilisateur tente de retirer le dernier responsable (`422`) et ajouter un accès rapide vers la gestion d'organisation depuis `/workspaces` (optionnel ergonomique).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a & 1b (`pytest` $\ge 90\%$ & `Vitest`)** : tests unitaires exhaustifs de `org_delegation.py` et `iam_delegated_invitation.py` (`BU_LEAD` sur BU/sous-BU/équipe, `TEAM_LEAD` sur équipe, garde anti-auto-éviction, anti-escalade) + tests Vitest sur `settingsRbacResolver.ts`, `SettingsOrganizationUnitsBlock`, les modales et la survie au `F5` (`unmount()` + `render()`).
- **Couche 2 (`HTTP FastAPI ➔ PostgreSQL 18 SELECT` via `testcontainers`)** : création de sous-BU/équipe et invitation d'un compte `HUMAN` par `BU_LEAD` et `TEAM_LEAD` vérifiées par `SELECT` sur `org_units`, `iam_accounts` et `users`, plus rejets `403` inter-BU / escalade et `422` dernier responsable.
- **Couche 3 (`OpenAPI 0-diff`, `Schemathesis`, `lint-imports`, `ruff`, `mypy --strict`, `pnpm turbo run lint typecheck test`)**.
- **Couche Sécurité (`tests/security/`)** : tests Red-Team d'isolation latérale inter-BU (`BU_LEAD A` ne peut pas muter `BU B`), d'interdiction d'élévation (`PLATFORM_ADMIN`, `SECOPS`, `SERVICE_PRINCIPAL`), et de rejet `403 ERR_OBSERVER_MODE_READ_ONLY`.
- **Couche 5 (`Playwright E2E`)** : scénario navigateur complet avec un compte `BU_LEAD` (`Rouge Gorge`) créant une sous-BU, une équipe et invitant un contributeur, puis vérification après `F5`.

---

## 3. Bilan des Modifications & Résultats (Phase de Cadrage & Backlog)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/screenshots/2026-11-16-bu-lead-settings-readonly-et-doubles-icones.png` | Archivage | Capture d'écran de référence démontrant le blocage `Rouge Gorge` (`BU_LEAD`) en lecture seule sur `/settings` ainsi que les doubles icônes. |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-16-cadrage-delegation-hierarchique-bu-equipe-et-invitation-comptes-tech-lead-report.md` | Création | Rapport technique pérenne de diagnostic (UI, Domaine, API), arbitrages D1/D2/D3 et plan d'implémentation complet `IAM-ORG-DELEGATION-01`. |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Indexation du nouveau rapport de cadrage dans le registre des rapports Tech Lead. |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Enregistrement des `action_items` `IAM-ORG-DELEGATION-01` (`P1`) et `UX-AUTH-DOUBLE-ICON-01` (`P3`) avec liens vers le rapport et la capture. |

### 3.2 & 3.3 Contrôles & Validation de Cadrage
- **Isolation du code applicatif** : `0` ligne de code applicatif modifiée à ce stade (travail borné au cadrage, à l'archivage de preuve et au backlog `sprint-status.yaml`).
- **Validation syntaxique & registre** : YAML de `sprint-status.yaml` contrôlé par `.venv/bin/python`, synchronisation du site catalogue validée (`pnpm site:sync && pnpm site:check`) et contrôle Spine (`lint_spine.py`) sans erreur.

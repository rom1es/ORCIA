## Epic 20: Gouvernance Déléguée (« Mon Organisation » & Audit Scopé), Glossaire PG18 & Rôle `ONTOLOGY_LEAD`, Consolidation « Mon Compte » (Style ChatGPT) et Page « Profil »

Corriger les blocages de délégation hiérarchique et les fractures de navigation constatés en exploitation : offrir un menu dédié **« Mon Organisation »** (`/organization`, placé sous `Mes Espaces`) aux `PLATFORM_ADMIN`, `BU_LEAD` (ex. Martin Pecheur) et `TEAM_LEAD` (ex. Pascal Lacdap) avec confinement strict de sous-arbre et invitation IAM scopée (`+ Inviter un utilisateur` sans escalade vers `PLATFORM_ADMIN`/`SECOPS`), filtrer le **Journal d'Activité** (`/activity` & `audit_ledger`) selon le périmètre réel de chaque rôle (incluant `org_unit_id` et suppression de `Plateforme entière` hors `PLATFORM_ADMIN`/`SECOPS`), renommer l'entrée gauche `Aide` en **« Glossaire »** (`/ontology`) adossée à PostgreSQL 18 avec le nouveau 7e rôle officiel **`ONTOLOGY_LEAD`** (désigné par BU) et un circuit de promotion palier par palier (`L4 → L3 → L2 → L1`) doté d'un onglet `Propositions à valider`, supprimer le contrôle de login redondant en haut à droite ainsi que le faux sélecteur `Rôle` au profit d'un popup **« Mon Compte »** consolidé en bas à gauche (style ChatGPT) et d'une modale unifiée **Paramètres** persistée en PostgreSQL 18, et livrer la page dédiée **« Mon Profil »** (`/profile`) affichant identité, rattachements, 4 KPIs de jetons/séries et les agents/processus/outils les plus utilisés alimentés par les tours `Mon Assistant` (`CAP-010`, `CAP-050`, `CAP-051`, `CAP-058`, `CAP-060`, `CAP-063`, `CAP-064`, `CAP-065`, `CAP-067`, `CAP-069`, `FR-8`, `FR-9`, `FR-21`, `FR-25`, `FR-31`, `FR-32`).

### Story 20.1: Menu « Mon Organisation » (`/organization`), Délégation `BU_LEAD` / `TEAM_LEAD`, Invitation IAM Scopée & Journal d'Activité Filtré par Périmètre

As a Responsable de Direction (`BU_LEAD`), Responsable d'Équipe (`TEAM_LEAD`) ou Administrateur Plateforme (`PLATFORM_ADMIN`),
I want gérer directement l'organigramme, les sous-BUs, les équipes, les co-responsables, les référents glossaire et l'invitation d'utilisateurs depuis un menu dédié « Mon Organisation » sous « Mes Espaces », et consulter un Journal d'Activité strictement filtré sur mon périmètre autorisé,
So that chaque responsable administre son périmètre en autonomie sans être bloqué sur `/settings` ni voir d'événements hors de ses droits (`FR-21`, `FR-25`, `FR-31`, `FR-32`, `IAM-ORG-DELEGATION-01`).

**Acceptance Criteria:**

**Given** un utilisateur connecté avec rôle `PLATFORM_ADMIN`, `BU_LEAD` (ex. Martin Pecheur) ou `TEAM_LEAD` (ex. Pascal Lacdap)
**When** il observe la barre latérale gauche et navigue vers `/organization`
**Then** l'entrée **« Mon Organisation »** apparaît juste sous « Mes Espaces » (tandis que l'onglet `organisation` est retiré de `/settings`, qui conserve 5 onglets : `iam`, `authentication`, `models`, `connectors`, `packs`) ; le `BU_LEAD` peut créer des sous-BUs et équipes dans son sous-arbre, modifier ses unités dirigées (co-responsables `lead_user_ids`, référents glossaire `ontology_lead_user_ids`), supprimer uniquement ses unités enfants (rejet `403 ERR_ORG_UNIT_ROOT_DELETE_FORBIDDEN` sur sa BU racine dirigée) et inviter un compte humain dans son sous-arbre via `POST /api/v1/org-units/invite-user` (rejet `403` sur `PLATFORM_ADMIN` / `SECOPS` / hors sous-arbre) ; le `TEAM_LEAD` peut modifier le nom, les co-responsables et les membres de ses seules équipes (sans créer ni supprimer d'unité).

**Given** les mutations d'organisation et d'accounts IAM (`ORG_UNIT_*`, `IAM_ACCOUNT_*`) ainsi que la consultation de `/activity`
**When** un utilisateur liste le Journal d'Activité via `GET /api/v1/audit/ledger` ou ouvre `/activity`
**Then** les mutations sont journalisées dans `audit_ledger` avec `org_unit_id`, `PLATFORM_ADMIN`/`SECOPS` conservent l'accès global (`Plateforme entière`), `BU_LEAD` accède aux événements de ses BUs/sous-BUs/équipes/espaces (y compris `workspace_id IS NULL AND org_unit_id IN (...)`), `TEAM_LEAD` accède à ses équipes et espaces, et `CONTRIBUTOR`/`OBSERVER` uniquement aux espaces dont ils sont membres — sans jamais proposer ni sélectionner `Plateforme entière` côté UI pour les non-admins/non-SecOps.

---

### Story 20.2: Menu « Glossaire » (`/ontology`), Persistance PostgreSQL 18 de l'Ontologie L1–L4, Rôle `ONTOLOGY_LEAD` & Promotions Palier par Palier (`L4 → L3 → L2 → L1`)

As a Membre d'Espace, Référent Glossaire (`ONTOLOGY_LEAD`), Responsable d'Équipe / BU ou Administrateur Plateforme,
I want accéder au Glossaire & Ontologie depuis le menu gauche renommé « Glossaire » (`/ontology`) persistant réellement en PostgreSQL 18, avec délégation de la validation L2 BU au rôle officiel `ONTOLOGY_LEAD` et promotion palier par palier (`L4 → L3 → L2 → L1`),
So that le vocabulaire métier et les règles de l'organisation soient gouvernés durablement sans confusion avec le Centre d'Aide (`/help`) ni perte au rafraîchissement (`F5`) (`FR-8`, `FR-9`, `FR-31`, `FR-34`).

**Acceptance Criteria:**

**Given** la navigation principale de la barre latérale gauche et les routes `/ontology` et `/help`
**When** l'utilisateur clique sur « Glossaire » dans la barre latérale gauche
**Then** la route `/ontology` s'ouvre avec l'explorateur d'ontologie/glossaire L1–L4 et l'onglet **`Propositions à valider (N)`** sans bannière `/showcase` ni centre d'aide statique (ceux-ci étant réservés à `/help`), tandis que le 7e rôle officiel `ONTOLOGY_LEAD` (« Référent Glossaire ») est synchronisé de façon bidirectionnelle entre `org_units.ontology_lead_user_ids_jsonb` (BU) et `iam_accounts.roles_jsonb`.

**Given** un terme ou une règle persisté en PostgreSQL 18 (`ontology_concepts`, `ontology_promotion_proposals`)
**When** un membre propose une promotion (`POST /api/v1/ontology-rag/ontology/promotions`) ou qu'un valideur habilité tranche (`POST /api/v1/ontology-rag/ontology/promotions/{id}/decide`)
**Then** l'auteur ne peut proposer que vers le palier immédiatement supérieur (`4_WORKSPACE` $\rightarrow$ `3_TEAM`, `3_TEAM` $\rightarrow$ `2_DOMAIN`, `2_DOMAIN` $\rightarrow$ `1_ENTERPRISE`) avec détection de collision, et seule la validation autorisée (`TEAM_LEAD`/`ONTOLOGY_LEAD`/`BU_LEAD` pour `3_TEAM`, `ONTOLOGY_LEAD` de la BU / `BU_LEAD` pour `2_DOMAIN`, `PLATFORM_ADMIN` pour `1_ENTERPRISE`) approuve ou rejette avec survie complète au `F5`.

---

### Story 20.3: Suppression du Login Top-Right, Popup « Mon Compte » en Bas à Gauche (Style ChatGPT) & Modale Unifiée « Paramètres » Persistée en PG18

As a Utilisateur authentifié ORCIA,
I want un en-tête épuré sans bouton login redondant ni faux sélecteur de rôle RBAC, un popup « Mon Compte » en bas à gauche inspiré de ChatGPT, et une modale unifiée « Paramètres » à 5 onglets persistée en PostgreSQL 18,
So that mes préférences (thème, langue, casquette IA, instructions, connexions outils, clés MCP) survivent au rechargement sans jamais altérer mes droits RBAC réels (`FR-32`, `CAP-060`, `CAP-063`, `UX-AUTH-DOUBLE-ICON-01`).

**Acceptance Criteria:**

**Given** la coquille 4 zones (`FourZoneDirectionCShell`)
**When** l'utilisateur observe le haut-droite et clique sur son bloc compte en bas à gauche
**Then** la zone haut-droite ne contient plus le contrôle Login/Compte (seulement `[❓ Aide]` et `[🔔 Notifications]`), le faux sélecteur `Rôle` (`dropdown-hat-selector`) est supprimé (`settingsRbacResolver` évalue l'union complète `session.roles`), et le clic sur le pied du rail gauche ouvre un popup style ChatGPT proposant : en-tête cliquable vers `/profile`, `Personnalisation`, `Profil`, `Paramètres`, `Aide ›` (`/help`, `/showcase`) et `Se déconnecter` (zéro double icône/emoji).

**Given** la modale unifiée « Paramètres » à 5 onglets (`Général`, `Personnalisation`, `Compte & Sécurité`, `Connexions aux outils`, `Clés IDE & MCP`)
**When** l'utilisateur modifie son thème, sa langue, sa casquette IA ou génère/révoque une clé MCP
**Then** les réglages sont persistés en PostgreSQL 18 (`user_preferences`, `user_mcp_tokens` hachés SHA-256 sans aucune clé codée en dur) via `/api/v1/users/me/preferences` et `/api/v1/users/me/mcp-tokens`, survivent au `F5` (`unmount()` + `render()`) et sont remis à zéro proprement par `pnpm db:reset`.

---

### Story 20.4: Page Dédiée « Mon Profil » (`/profile`, Style ChatGPT : Identité, 4 KPIs Tokens/Séries & Éléments Populaires) & Télémétrie Tokens de `Mon Assistant`

As a Utilisateur authentifié ORCIA,
I want consulter ma page personnelle `/profile` présentant mon identité, mes rattachements BU/Équipes/Rôles, mes 4 indicateurs de consommation de tokens et séries d'activité ainsi que mes agents/processus/outils les plus utilisés,
So that je dispose d'une vue synthétique claire de mon activité réelle sur la plateforme, alimentée aussi bien par `Mon Assistant` que par les workflows (`FR-25`, `FR-32`, `CAP-069`).

**Acceptance Criteria:**

**Given** un tour complété dans `Mon Assistant` (`assistant_workspace.py` / `assistant_background_turns.py`)
**When** l'exécution se termine (streaming SSE ou non-streaming)
**Then** les tokens (`input_tokens`, `output_tokens`, réels via `usage` ou estimation déterministe tracée) sont enregistrés dans `audit_ledger` avec `event_type = "ASSISTANT_TURN_COMPLETED"`, `actor_id`, `actor_email`, `model_id` et `workspace_id`.

**Given** l'utilisateur authentifié ouvrant `/profile` (via l'entrée `Profil` ou l'en-tête du popup `Mon Compte`)
**When** `GET /api/v1/users/me/profile-summary` s'exécute
**Then** l'agrégation SQL strictement confinée à l'utilisateur retourne son identité, ses BU/équipes/rôles, ses 4 KPIs (`total_tokens`, `peak_daily_tokens`, `longest_streak_days`, `current_streak_days`) et ses `popular_items` (Top 5 agents/processus/compétences/outils utilisés, vide `[]` au Jour 0), rendus dans `UserProfileOverviewPage` avec un bouton `Modifier` ouvrant la modale Paramètres (`Compte & Sécurité`), tandis que la Heatmap 12 mois et le tableau Statistiques détaillées restent différés dans `ACTION_ITEM-20.1`.

---

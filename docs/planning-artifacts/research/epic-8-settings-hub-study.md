# Étude de cadrage — Epic 8 : Settings Hub, Gouvernance d'Entreprise & Routage Cognitif

- **Statut** : `in-design` — **Date** : 2026-10-30 — **Auteur** : Lead Architect (BMAD)
- **Références** : AD-19 (frontières modulaires), AD-20 (Core / packs), Story 3.2f (typologie des étapes), Story 3.5 (Gates), Epic 7 (Service Principals)

## 0. Contexte et objectifs

ORCIA (DBOS / PostgreSQL 18, Outbox, Core agnostique + packs métier, SPA Vite 6 / TanStack Router / Tailwind / Radix) doit centraliser :
1. l'administration d'entreprise (`/settings/*`) ;
2. la gouvernance fine des habilitations (verbes × hiérarchie) ;
3. l'abstraction cognitive des LLMs (tiers + routage autonome) ;
4. des assistants d'initialisation durables (Zéro écran blanc).

Principes : frontières `AD-19` respectées (`orcia_core.permissions`, `orcia_core.catalog`, nouveau domaine d'inférence dans `orcia_core`), schémas HTTP uniquement dans `apps/api/.../schemas/`, SDK OpenAPI régénéré (0-diff), UI dans `@orcia/ui`, libellés en français via i18n typé.

---

## 1. Modèle d'habilitations granulaire & hiérarchique (RBAC / ABAC)

### 1.1 Verbes standardisés

| Verbe | Sémantique |
|---|---|
| `create` | Créer une ressource dans le scope |
| `read` | Lire l'existence et la configuration |
| `update` | Modifier la configuration |
| `delete` | Supprimer / archiver |
| `execute` | Exécuter / utiliser **sans** lire la configuration (ex. lancer un workflow, utiliser un connecteur sans voir ses secrets) |
| `grant` | Déléguer localement des habilitations (délégation contrôlée) |

### 1.2 Hiérarchie et scoping

```
Organisation -> Workspace / Domaine -> Pack -> Ressource -> Action
```

Une habilitation = `(sujet, scope_path, resource_type, verbe, effect=ALLOW)` où `scope_path` est un chemin matérialisé (ou `ltree` PostgreSQL) permettant la résolution par ancêtres en **une requête** (CTE récursive bornée, pas de N+1).

Sujets : utilisateur, groupe, rôle, Service Principal IA (Epic 7).

### 1.3 Règles MVP

- **Héritage purement additif** : l'ensemble effectif = union des ALLOW des ancêtres et du nœud.
- **Confinement de `grant`** : `grant(S, P, v)` autorisé ssi l'émetteur détient `v` sur `P` (ou ancêtre) **et** `grant` sur `P`; `P` ⊆ périmètre de l'émetteur. Pas d'escalade : droits délégués ≤ droits propres. Chaque délégation est écrite dans `audit_ledger` (append-only).
- Les mutations restent soumises à `RunAccessGuard` / `ScopeAccessGuard`; `READ_ONLY_OBSERVER` ⇒ `403 ERR_OBSERVER_MODE_READ_ONLY`.
- Erreurs métier dans `orcia_core/permissions/errors.py` (hérite `OrciaDomainError`), réponse RFC 9457 avec `trace_id`.

### 1.4 UX pour entités non autorisées

Nominal : **découverte passive** — entité visible grisée, cadenas + badge « Non habilité », action « Demander l'accès » (événement Outbox `AccessRequested`).

### 1.5 Trajectoire d'évolution (Action Items)

| ID | Extension | Impact modèle |
|---|---|---|
| `ACTION_ITEM-8.1` | `DENY` prioritaire + `INHERITANCE_BLOCK` sur sous-entités sensibles | colonne `effect ∈ {ALLOW, DENY}`, flag `inheritance_block` sur le nœud; algorithme : DENY > ALLOW, coupure d'héritage au nœud bloqué |
| `ACTION_ITEM-8.2` | `execute` contextuel (`env == 'staging'`, plafond tokens/run) | colonne `conditions_jsonb` évaluée par le broker (mini-DSL borné, sans `eval`) |
| `ACTION_ITEM-8.3` | `hidden_when_unauthorized: true` par type d'objet | attribut sur le type de ressource; l'API renvoie `404` indistinguable, jamais de cadenas |

Le schéma MVP **réserve** ces colonnes (nullables / défaut neutre) pour éviter une migration cassante (Expand → Contract).

### 1.6 Données & migrations

Migration Alembic incrémentale (SQL brut, `upgrade`/`downgrade` testés), PK UUIDv7 : `permission_grants`, `resource_scopes` (arbre), index GIN/ltree sur `scope_path`. Seed des rôles par défaut via `bootstrap/seeder.py` (upserts idempotents).

---

## 2. Abstraction cognitive & routage intelligent des modèles

### 2.1 Tiers logiques

| Tier | Usage | Coût |
|---|---|---|
| `simple` | Extraction JSON, classification, faible latence | € |
| `medium` | Synthèse, rédaction de specs | €€ |
| `complex` | Raisonnement lourd, architecture, agents contradictoires (Blind Hunter, Edge Case Hunter) | €€€ |

Les workflows référencent **un tier**, jamais un modèle physique. Le mapping `tier → (provider, model, params)` est administrable par workspace (`/settings/ai-models`), avec fallback chain par tier.

### 2.2 Option `auto` (Semantic Router)

- Résolution **au runtime** à partir de la typologie d'étape (Story 3.2f) et de la nature de la Gate (Story 3.5).
- **Cascading Fallback** : exécution en `simple`; si une gate **déterministe** échoue ⇒ escalade `medium` puis `complex` (plafond configurable, nombre d'escalades borné).
- Idempotence DBOS : la décision de routage est un `step` DBOS enregistré (rejeu sans re-décision); chaque tentative est auditée (tier, modèle, coût, raison d'escalade) et alimente FinOps.
- Appels via LiteLLM derrière un port `InferenceRouterPort` (hors `orcia_kernel`); en CI `DeterministicCassetteLLM` (0 $).

### 2.3 Schéma & contrat

```python
class InferenceTier(StrEnum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    AUTO = "auto"
```

Workflow-as-Code :
```yaml
steps:
  - id: summarize_spec
    inference_tier: medium      # simple | medium | complex | auto
```

Tables : `ai_providers`, `ai_tier_mappings(workspace_id, tier, provider_id, model, fallback_order, token_budget)`, `inference_attempts` (append-only logique). Défaut du champ : `auto` ou `medium` (à trancher, cf. §6). Budgets de tokens appliqués par run et par période.

---

## 3. Architecture frontend (TanStack Router)

Layout racine `/settings` ; `beforeLoad` vérifie `read` (consultation) vs `update`/`write` (édition) via le contexte de permissions chargé une fois (`/api/v1/shell`). Refus ⇒ redirection vers vue d'info « Non habilité » (pas d'écran blanc).

| Route | Contenu |
|---|---|
| `/settings/iam` | Utilisateurs, groupes, rôles, Service Principals IA, matrice de délégation |
| `/settings/connectors` | Catalogue fédéré (Git, Jira, Confluence, DBs), secrets `••••••••`, healthchecks |
| `/settings/ai-models` | Fournisseurs, mapping des tiers, auto-routing, budgets |
| `/settings/packs` | Registre, découverte, activation dynamique (cf. ARCH-M10) |
| `/settings/workflows` | Gabarits YAML, taxonomie des étapes, chaînage des Gates |
| `/settings/audit` | Audit trail append-only, rejeu Outbox |

Composants génériques (`@orcia/ui`, sans import router / api-client) :
- `<PermissionGuard mode="read|write|execute|grant">` : reçoit un booléen/état résolu en props; `fallback` = cadenas + « Non habilité ».
- `<SecretField>` : masquage systématique, jamais de valeur renvoyée par l'API (seulement `has_value` + empreinte), écrasement explicite (« Remplacer »), jamais de log.

Règles UX/UI : Direction C, tokens uniquement, 2 typographies max, WCAG AA, Mobile-First, `Escape` pour fermer les tiroirs, feedback immédiat, libellés i18n FR.

---

## 4. Parcours d'initialisation (Wizards durables, Zero Empty-State)

| Wizard | Étapes clés |
|---|---|
| Tech Lead / SDLC | Git + Jira, détection `specs/`, calibration de sévérité des agents de revue |
| Responsable Métier (RH / Achats) | Gabarit, connecteurs SI, seuils What-If, arbitres des Anchor Cards |
| Admin Plateforme / Sécurité | SSO OIDC bi-mode, clés de chiffrement, rétention DBOS |

Exigences :
- **Projet démo** injecté (seed idempotent) pour qu'aucun écran ne soit vide.
- **Tests de connectivité fail-fast** : workflows DBOS déterministes, timeout court, erreur RFC 9457 localisée.
- **Persistance de progression** : table `wizard_sessions(state_jsonb, step, version)` pilotée par un workflow DBOS; reprise sans perte, écritures idempotentes; secrets saisis stockés chiffrés (vault), jamais dans `state_jsonb`.

---

## 5. Découpage en stories

| Story | Périmètre | Dépendances |
|---|---|---|
| 8.1 | Moteur 6 verbes + scoping hiérarchique, migration, API, tests de confinement `grant` | Epic 7.1 |
| 8.2 | Tiers + routeur `auto` + cascading fallback + budgets | 3.2f, 3.5 |
| 8.3 | Coquille `/settings/*`, `PermissionGuard`, i18n | 8.1 |
| 8.4 | Hub connecteurs + `SecretField` + healthchecks | 8.3, `ConnectorPort` (3.2e) |
| 8.5 | Studio workflows + registre des packs | 8.2, 8.3 |
| 8.6 | Wizards durables + projet démo | 8.1, 8.4 |

Ordre conseillé : 8.1 → (8.2 ∥ 8.3) → 8.4 → 8.5 → 8.6. Les rapports Tech Lead (`tech-lead-reports/{story-key}-tech-lead-report.md`) sont produits story par story, avec analyse GitNexus (`repo: "ORCIA"`) préalable.

## 6. Risques & questions ouvertes

1. Performance de résolution des permissions sur arbres profonds ⇒ `ltree` + cache de session invalidé via Outbox.
2. Risque d'escalade par délégation `grant` ⇒ tests de propriété (hypothesis) sur l'invariant « délégué ≤ détenu ».
3. Coût des cascades `auto` ⇒ plafond d'escalades et alerte FinOps.
4. Tier par défaut des workflows : `auto` vs `medium` — décision produit requise.
5. Fuite de secrets via wizard / audit ⇒ redaction centralisée dans `orcia_kernel`.
6. Ajout éventuel de dépendances (`ltree` natif PostgreSQL : aucune nouvelle dépendance) — mise à jour de l'ARCHITECTURE-SPINE + `lint_spine.py` si l'une est ajoutée.

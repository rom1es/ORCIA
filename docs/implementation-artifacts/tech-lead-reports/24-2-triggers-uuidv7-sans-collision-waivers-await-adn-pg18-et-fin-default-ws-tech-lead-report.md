# Rapport Tech Lead — Story 24.2 : Déclencheurs UUIDv7 sans Collision, Waivers `await`, ADN Starlark PG18 & Purge `default-ws`

- **Story :** `24-2-triggers-uuidv7-sans-collision-waivers-await-adn-pg18-et-fin-default-ws` (Epic 24 — Vague 0 `P0/P1`)
- **Date :** 2026-11-20
- **Statut :** `En attente d'implémentation` (initialisé par `Story 23.8`)
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-03`, `REM24-04` | Échecs E2E `20#2 #49`, `17#3 #40` | Constat `UX23-06` (`P1`) | Diagnostics `ARCH24-03`, `ARCH24-04`
- **Capacité(s) (`capabilities.yaml`) :** `CAP-010`, `CAP-011`, `CAP-081`, `CAP-084`, `CAP-180`, `CAP-201` (`6` capacités Desktop `failed_e2e`)
- **Classification :** `feature` (intégrité UUIDv7, persistance PG18 & hygiène Jour 0)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Critères d'Acceptation
Deux échecs structurants bloquent la création séquentielle d'automatisations et la gouvernance d'espace :
1. **Collision UUIDv7 sur triggers séquentiels (`20#2 #49` / `ARCH24-03`)** : dans `packages/orcia-core/src/orcia_core/orchestration/_triggers_lifecycle_ops.py:46-47`, la clé auto-générée vaut `f"trg-{tid[:8]}"`. Or les `8` premiers caractères hexadécimaux d'un `UUIDv7` encodent les `32` bits MSB de l'horodatage (`65,5 s` de granularité), provoquant une collision immédiate lors de deux créations séquentielles dans la même fenêtre temporelle. Par ailleurs, `WorkflowTriggersModal` ne permet pas la saisie optionnelle d'un `trigger_key`.
2. **Waivers non attendus, ADN Starlark volatil & résidus `"default-ws"` (`17#3 #40` / `ARCH24-04` / `UX23-06`)** :
   - Dans `WorkspaceDnaAndWaiversSection.tsx` (`277` L), les appels `registerWorkspaceExceptionWaiver` et `compileDnaStarlark` ne sont pas `await` correctement avec état `submitting` et rafraîchissement depuis PG18 ; lorsque `0` espace existe, la section ne doit jamais être montée avec des identifiants factices.
   - `DnaStarlarkAndGlossaryLifecycleService` garde en RAM les mécanismes Starlark signés sans les persister durablement en PG18 (`dependencies/workspace_and_packs.py`).
   - Des fallbacks factices `"default-ws"`, `"ws-claims-alpha"`, `"ws-mon-compte"` subsistent dans le code applicatif/UI en contradiction avec la vérité terrain Jour 0.

**Critères d'acceptation :** zéro collision `trigger_key` sur créations en rafale (`< 1 s`), `await` + `submitting` + rechargement PG18 sur waivers et ADN Starlark, persistance PG18 des mécanismes signés, `0` occurrence runtime de `"default-ws"` / `"ws-claims-alpha"` / `"ws-mon-compte"`, et succès E2E `20#2 #49` + `17#3 #40`.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `TriggerDispatcherService` (`packages/orcia-core/src/orcia_core/orchestration/triggers_dispatcher.py`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`). Inspection directe `_triggers_lifecycle_ops.py:36-67` (`261` L) confirmant `tid[:8]` aux lignes `46-47`.
- `DnaStarlarkAndGlossaryLifecycleService` (`packages/orcia-core/src/orcia_core/orchestration/dna_starlark_and_glossary_lifecycle.py:89-447`) : `impactedCount: 400`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 376`, `d=2: 22`, `d=3: 2`, `processes_affected: 83`, `modules_affected: 20`).
- Impact API (`gitnexus api_impact`) :
  - `apps/api/src/orcia_api/routers/workflow_triggers.py` (`8` routes HTTP).
  - `apps/api/src/orcia_api/routers/workspace_governance.py` (`7` routes HTTP) + `apps/api/src/orcia_api/dependencies/workspace_and_packs.py` (`189` L).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` L)
- **Découpage obligatoire `dna_starlark_and_glossary_lifecycle.py` (`447` L > seuil `400` L)** : séparer le cycle de vie glossaire/ontologie de la compilation/persistance Starlark ADN en deux modules cohésifs `< 250` L (avec adaptateur SQL dédié sous `_internal/`).
- **Primitive commune `uuid_utils` suffixe entropique** : utiliser la partie aléatoire/finale d'UUIDv7 (`tid` complet ou `tid.replace("-", "")[-12:]`) ou un générateur d'identifiant court dans `orcia_kernel` afin d'éliminer tout tronquage sur MSB temporels dans le codebase.

---

## 2. Plan d'Implémentation

### 2.1 Couche Données & Migrations Alembic / PostgreSQL 18
1. Vérifier les colonnes actuelles de `ontology_relations` (`mechanism_payload_jsonb` ou table dédiée aux mécanismes Starlark signés) et des tables de waivers d'espace ; ajouter au besoin une révision Alembic `Expand` en SQL brut garantissant la persistance du payload Starlark compilé et signé par workspace en PG18.
2. Vérifier la contrainte d'unicité de `trigger_key` en base pour supporter soit la clé fournie par l'utilisateur (`409` RFC 9457 explicite si déjà prise), soit la clé auto-générée sans collision temporelle.
3. Mettre à jour `_first_boot_reset_guards.py` si une nouvelle table mutable est introduite.

### 2.2 Noyau Hexagonal (`orcia-kernel` / `orcia-core`) & Workers
1. Corriger `_triggers_lifecycle_ops.py:46-47` (`execute_create_trigger`) : générer `f"trg-{tid}"` ou `f"trg-{tid.replace('-', '')[-12:]}"` (jamais `tid[:8]`).
2. Découper `dna_starlark_and_glossary_lifecycle.py` (`447` L $\rightarrow$ `< 300` L par module) et persister les mécanismes Starlark compilés/signés en PG18 via port + adaptateur SQL injecté dans `dependencies/workspace_and_packs.py` (`189` L).
3. Purger toute référence ou fallback `"default-ws"`, `"ws-claims-alpha"` et `"ws-mon-compte"` du noyau et vérifier la gestion stricte des erreurs RFC 9457 (`ERR_WORKSPACE_REQUIRED` / `404` / `409`).

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
1. Exposer le champ optionnel `trigger_key` sur le schéma de requête de création de trigger dans `apps/api/src/orcia_api/schemas/` (`workflow_triggers.py` `8` routes) et régénérer `@orcia/api-client` (`0-diff`).
2. Vérifier les endpoints `workspace_governance.py` (`7` routes) pour retourner la liste des waivers et l'état Starlark directement relus depuis PG18 (`Depends(...)` injecté depuis `dependencies/workspace_and_packs.py`).

### 2.4 Interface SPA Vite + TanStack Router & Design System (`@orcia/ui` / `apps/web`)
1. Exposer le champ optionnel `trigger_key` dans `WorkflowTriggersModal` avec validation et gestion d'erreur visible (`[role="alert"]`, `UX23-06`).
2. Dans `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` (`277` L) et `workspaces/index.tsx` (`224` L) :
   - Ajouter `await` + état `submitting` + rechargement PG18 immédiat sur `registerWorkspaceExceptionWaiver` et `compileDnaStarlark`.
   - Supprimer tout fallback `"default-ws"` / `"ws-claims-alpha"` / `"ws-mon-compte"` ; ne pas monter `WorkspaceDnaAndWaiversSection` lorsqu'aucun espace n'existe (afficher un état vide explicite guidant vers la création d'espace).

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire >= 90 %)** : test de non-collision sur `1 000` créations de triggers dans la même milliseconde ; tests unitaires split `dna_starlark_and_glossary_lifecycle` et interdiction AST/grep `"default-ws"` en prod.
- **Couche 2 (Intégration `testcontainers` PG18 réel)** : création séquentielle de triggers et enregistrement waivers + ADN Starlark via `create_app()` réel $\rightarrow$ `SELECT` PG18 $\rightarrow$ relecture à froid.
- **Couche 3 (Composants React)** : test Vitest `WorkspaceDnaAndWaiversSection` (vérifiant l'attente `await`, l'état `submitting`, le non-montage si `0` workspace et l'affichage `[role="alert"]` sans catch silencieux).
- **Couche 4 (E2E Playwright ciblé)** : `20-process-studio-and-triggers.spec.ts` (`20#2 #49`) et `17-workspace-waivers-and-dna-starlark.spec.ts` (`17#3 #40`) avec rechargement `F5`.
- **Couche 5 (Statique & Sécurité)** : `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck test`, `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats

> **Statut :** `En attente d'implémentation` — Cette section sera complétée après implémentation, passage des 5 couches `AD-17`, ré-indexation GitNexus (`npx gitnexus analyze` + `gitnexus_detect_changes()`) et exécution de `pnpm site:sync`.

| Fichier / Composant | Action Prévue | Statut |
|---|---|---|
| `packages/orcia-core/.../orchestration/_triggers_lifecycle_ops.py` | Fix collision `tid[:8]` (`L46-47`) | `En attente d'implémentation` |
| `packages/orcia-core/.../orchestration/dna_starlark_and_glossary_lifecycle.py` | Split `< 350` L + persistance ADN PG18 | `En attente d'implémentation` |
| `infra/migrations/versions/*` + `dependencies/workspace_and_packs.py` | Schéma/DI ADN Starlark PG18 | `En attente d'implémentation` |
| `apps/api/src/orcia_api/{schemas,routers}/workflow_triggers.py` & `@orcia/api-client` | `trigger_key` optionnel + OpenAPI sync | `En attente d'implémentation` |
| `apps/web/src/features/workspaces/{WorkspaceDnaAndWaiversSection.tsx,index.tsx}` | `await`, état vide `0` espace, fin `"default-ws"` | `En attente d'implémentation` |
| Composant modal triggers (`WorkflowTriggersModal`) | Champ optionnel `trigger_key` & erreur RFC 9457 | `En attente d'implémentation` |

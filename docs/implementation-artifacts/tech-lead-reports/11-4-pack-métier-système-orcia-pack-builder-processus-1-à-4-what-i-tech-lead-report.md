# Rapport d'Analyse & d'Implémentation Tech Lead — Story 11.4 : Pack Métier Système `packages/orcia-pack-builder` (Processus 1 à 4, Simulation *What-If*, Certification `Starlark` Palier 1b `< 2 ms` & Promotion depuis un Espace)

> **Statut** : `DONE`
> **Date** : `2026-10-31`
> **Auteur** : Tech Lead / Senior Dev Agent
> **Références** : [`epics.md` (Story 11.4)](../../planning-artifacts/epics.md#L1333-L1349) · [`ARCHITECTURE-SPINE.md`](../../planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md) · [`DESIGN.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md) · [`EXPERIENCE.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte Fonctionnel & Problématique
Pour permettre à ORCIA de s'étendre à de nouveaux métiers (Finance, Juridique, RH, Retail, Ops, Cyber) sans polluer `orcia-kernel` ni `orcia-core` (`AD-20`) et sans jamais compiler d'outils tiers en WASI (`AD-9`), la **Story 11.4** livre le Pack Métier Système **`packages/orcia-pack-builder`** embarquant **4 agents spécialisés** (`@Architecte-Métier-Pack`, `@Ingénieur-Prompt-et-Workflow`, `@Certificateur-Sécurité-et-Sandbox`, `@Rédacteur-Documentation-Orcia`) et les **4 premiers processus gouvernés** :
1. **Processus 1 (`create-business-pack`)** :
   - Exige un **`✍️ Ancrage Humain Violet`** d'intention métier (`human_authored_required: true`, $\ge 30$ caractères, sinon rejet `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED` `AD-3`) ;
   - Structure la chaîne causale **`DIRECTIVE ➔ NORME ➔ MÉCANISME`** du glossaire socle (`AD-7`), les profils humains, les agents et les processus ;
   - Valide le manifeste `pack.yaml` en Sandbox Palier 1a (`< 5 s`) et toutes les règles métiers `.star` en Palier 1b (`StarlarkMechanismSandbox` `< 2 ms`) ;
   - Génère l'arborescence complète d'un Pack Métier cible (`packages/orcia-pack-{pack_slug}/`) avec `0` écriture dans `packages/orcia-kernel` ou `packages/orcia-core` (`AD-20`).
2. **Processus 2 (`evolve-business-pack`)** :
   - Exécute la simulation d'impact ***What-If*** (`ImpactSimulator`, `AD-7`) pour identifier tous les Espaces et Processus impactés par la nouvelle version `@vX.Y.Z` sans jamais altérer les `run-lock.json` des runs en cours.
3. **Processus 3 (`certify-pack-tool`)** :
   - Certifie en priorité les règles métiers déterministes via **`StarlarkMechanismSandbox`** (**Palier 1b `starlark-pyo3` + anti-ReDoS linéaire $O(n)$ `< 2 ms`** sur vecteurs `passing_test_payload` / `failing_test_payload`) ;
   - Ou exécute les tests TDD et l'audit de sécurité d'un outil lourd dans **`sandbox-runner` Palier 2** (`TIER_2_CONTAINER`, `gVisor/Podman rootless --network=none < 60 s`, `AD-9`).
4. **Processus 4 (`export-from-workspace-to-pack`)** :
   - Nettoie automatiquement toute référence locale (`workspace_id`, `local://`, `SecretRef`, emails/URLs internes) avant de promouvoir un agent, un processus, une norme ou un mécanisme Starlark éprouvé d'un Espace vers une nouvelle révision du Pack Métier.

### 1.2 Analyse d'Impact GitNexus
- **Requête `gitnexus_query({query: "pack-builder ImpactSimulator StarlarkMechanismSandbox pack.yaml create-business-pack", repo: "ORCIA"})`** :
  - Identifie `StarlarkMechanismSandbox` (`packages/orcia-core/src/orcia_core/gates/_internal/starlark_sandbox.py`), `DnaStarlarkAndGlossaryLifecycleService` (`Story 11.2`), et `orcia_pack_sdlc` (`packages/orcia-pack-sdlc/src/orcia_pack_sdlc/__init__.py`).
- **Analyse `gitnexus_impact({target: "StarlarkMechanismSandbox", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`2` appelants amont : `gates/__init__.py` et `dna_starlark_and_glossary_lifecycle.py`).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie
- Création du package Python isolé `packages/orcia-pack-builder/` (`src/orcia_pack_builder/__init__.py`, `pack.yaml`, `pyproject.toml`) enregistré dans `pyproject.toml` et vérifié par `import-linter` (`AD-20 Contract 4` étendu pour interdire tout import de `orcia_pack_builder` depuis `orcia_kernel` ou `orcia_core`).
- Création du service d'orchestration `packages/orcia-core/src/orcia_core/orchestration/pack_builder_processes.py` (< 390 lignes) réutilisant directement `StarlarkMechanismSandbox`.

---

## 2. Plan d'Implémentation

### 2.1 Package Système `packages/orcia-pack-builder` (`AD-20`)
- Manifeste déclaratif `packages/orcia-pack-builder/pack.yaml` et package Python `packages/orcia-pack-builder/src/orcia_pack_builder/__init__.py` déclarant les 4 agents spécialisés et les 5 processus gouvernés (`create-business-pack`, `evolve-business-pack`, `certify-pack-tool`, `export-from-workspace-to-pack`, `generate-and-attach-help`).

### 2.2 Noyau Hexagonal (`packages/orcia-core`)
- Module [`pack_builder_processes.py`](../../../../packages/orcia-core/src/orcia_core/orchestration/pack_builder_processes.py) :
  - `PackBuilderSystemService` implémentant :
    - `create_business_pack(...)` (Processus 1 : ancrage humain violet obligatoire, chaîne ADN `DIRECTIVE ➔ NORME ➔ MÉCANISME`, validation manifeste Palier 1a `< 5 s` + règles `.star` Palier 1b `< 2 ms`, génération de l'arborescence `packages/orcia-pack-{slug}/` sans toucher `orcia-kernel`/`orcia-core`) ;
    - `evolve_business_pack_what_if(...)` (Processus 2 : rapport d'impact *What-If* par Espace/Processus et préservation stricte des `run-lock.json` actifs) ;
    - `certify_pack_tool(...)` (Processus 3 : certification `TIER_1B_STARLARK` `< 2 ms` sur vecteurs `PASS`/`FAIL` ou `TIER_2_CONTAINER` `--network=none < 60 s`) ;
    - `export_from_workspace_to_pack(...)` (Processus 4 : scrubbing déterministe des identifiants d'espace, `SecretRef` et chemins `local://` avant promotion).

### 2.3 Backend FastAPI (`apps/api`)
- Schémas Pydantic v2 [`epic11_pack_builder.py`](../../../../apps/api/src/orcia_api/schemas/epic11_pack_builder.py) et routeur [`epic11_pack_builder.py`](../../../../apps/api/src/orcia_api/routers/epic11_pack_builder.py) exposant `/api/v1/pack-builder/manifest`, `/api/v1/pack-builder/processes/create-pack`, `/api/v1/pack-builder/processes/evolve-what-if`, `/api/v1/pack-builder/processes/certify-tool`, `/api/v1/pack-builder/processes/export-from-workspace`.

### 2.4 Interface SPA Direction C (`@orcia/ui`)
- Primitive [`PackBuilderProcessesStudioView.tsx`](../../../../packages/ui/src/primitives/PackBuilderProcessesStudioView.tsx) affichant les 4 agents spécialisés, l'Ancrage Humain Violet (`#6D28D9`), les 4 processus d'atelier, le rapport *What-If* et le certificat de test Palier 1b / Palier 2.

---

## 3. Bilan des Modifications & Résultats (Après Implémentation)

### 3.1 Fichiers Créés / Modifiés
| Fichier | Nature | Rôle |
| :--- | :--- | :--- |
| `packages/orcia-pack-builder/pack.yaml` | Créé | Manifeste déclaratif du pack système `orcia-pack-builder` |
| `packages/orcia-pack-builder/pyproject.toml` | Créé | Métadonnées et `entry_points` (`orcia.packs`) du pack système |
| `packages/orcia-pack-builder/src/orcia_pack_builder/__init__.py` | Créé | Définition des 4 agents et 5 processus gouvernés (`AD-20`) |
| `packages/orcia-core/src/orcia_core/orchestration/pack_builder_processes.py` | Créé | `PackBuilderSystemService` (Processus 1 à 4) |
| `apps/api/src/orcia_api/schemas/epic11_pack_builder.py` | Créé | Schémas HTTP/OpenAPI Pydantic v2 Story 11.4 |
| `apps/api/src/orcia_api/routers/epic11_pack_builder.py` | Créé | Endpoints FastAPI `/api/v1/pack-builder/*` |
| `packages/ui/src/primitives/PackBuilderProcessesStudioView.tsx` | Créé | Primitive Direction C pour l'Atelier `orcia-pack-builder` |
| `tests/unit/test_epic_11_story_11_4_pack_builder_processes.py` | Créé | Tests unitaires Processus 1 à 4 + isolation `AD-20` |
| `tests/integration/test_story_11_4_pack_builder_postgres18_s3.py` | Créé | Tests d'intégration PostgreSQL 18 + SeaweedFS S3 (`testcontainers`) |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Frontières (`AD-19` / `AD-20`)
- `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `0` erreur.
- `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core packages/orcia-pack-sdlc packages/orcia-pack-builder apps/api apps/worker` : `0` erreur.
- `.venv/bin/lint-imports` : `5 contracts kept, 0 broken` (`orcia_pack_builder` inclus dans les contrats d'isolation `AD-19` et `AD-20`).
- `.venv/bin/pytest tests/unit/test_epic_11_story_11_4_pack_builder_processes.py tests/integration/test_story_11_4_pack_builder_postgres18_s3.py` : 100 % verts.
- `pnpm turbo run lint typecheck test` : 100 % verts.

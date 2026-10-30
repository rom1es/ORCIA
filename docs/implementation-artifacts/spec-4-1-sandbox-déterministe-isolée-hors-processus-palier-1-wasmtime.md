# Spécification d'Implémentation — Story 4.1 : Sandbox Déterministe Isolée Hors Processus Palier 1 (`wasmtime-py < 5 s`, sans réseau), Détection de Pattern Drift & Workflows Système `init-existing-project` / `init-skill`

- **Clé de Story** : `4-1-sandbox-déterministe-isolée-hors-processus-palier-1-wasmtime`
- **Epic** : `Epic 4` — Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution
- **Statut** : `done`
- **Références** : `FR-17`, `FR-28`, `AD-9`, `AD-12`, `AD-16`, `AD-19`, `M8`, `Q3: 3A`, `Q5`, `NFR-SEC-1`

---

## 1. Objectif & Périmètre

1. **Table `gate_evaluations` (Migration Alembic `0017_story_4_1`)** :
   - Stocke les évaluations des Gates (`DETERMINISTIC`, `AGENTIC`, `HUMAN`), le palier de sandbox (`TIER_1_WASM`, `TIER_2_CONTAINER`, `NONE`), le verdict (`PASS`, `FAIL`, `ERROR`, `PENDING_HUMAN_REVIEW`), le score (`0.0..1.0`), les indicateurs de validation (`schema_validation_passed`, `ontology_axioms_passed`, `pattern_drift_passed`), les constats JSONB (`pattern_drift_findings_jsonb`, `lens_findings_jsonb`, `briefing_4blocks_jsonb`) et la durée d'exécution (`duration_ms`).
2. **Sandbox Hors Processus Palier 1 (`infra/sandbox/tier1_runner.py` & `SubprocessTier1SandboxAdapter` derrière `SandboxPort`)** :
   - Exécution isolée hors processus sans privilèges root, sans aucun accès réseau (`socket` verrouillé -> `exit_code = 126`), système de fichiers en lecture seule hors `/tmp` éphémère limité à `64 MB`, plafond mémoire `256 MB` (`RLIMIT_DATA` / contrôle d'allocation -> `exit_code = 137`) et timeout matériel strict de `5 000 ms` (`exit_code = 124`).
   - Supporte l'exécution de modules WebAssembly (`wasmtime` si présent) et l'évaluateur déterministe pur en sous-processus isolé.
3. **Évaluateur de Gate Déterministe & Détection de Pattern Drift (`packages/orcia-core/src/orcia_core/gates/deterministic.py`)** :
   - Vérifie dans la Sandbox Palier 1 :
     1. Le schéma JSON/YAML du *Gabarit d'Artefact* (sections requises, types de champs).
     2. Les axiomes formels de l'*Ontologie* (`immutable: true`, expressions d'invariants).
     3. Les règles d'analyse statique de **Pattern Drift (`FR-17`)** vis-à-vis de `ARCHITECTURE-SPINE.md` (rejetant toute bibliothèque ou motif banni ou absent de la Spine de référence).
   - Publie `GateEvaluated` dans `domain_events_outbox`.
   - S'intègre comme exécuteur `SKILL` dans `orcia.step_executors` et classe les erreurs dans la taxonomie `orcia_kernel.errors` (timeout $\rightarrow$ `UpstreamTimeoutError` relançable ; évasion réseau/FS/mémoire $\rightarrow$ `PolicyDeniedError` non relançable).
4. **Workflows Système `init-existing-project` & `init-skill` (`FR-28`, `AD-16`)** :
   - `orcia://system/bootstrap/init-existing-project` : scanne un projet existant (*Brownfield*) pour générer et faire signer un `ARCHITECTURE-SPINE.md` initial (`[ADOPTED]`) servant de baseline anti-*Pattern Drift*.
   - `orcia://system/bootstrap/init-skill` : certifie un *Skill* candidat dans la Sandbox Palier 1 (`< 5 000 ms`, `0` appel réseau, `<= 256 MB` RAM) avant de l'enregistrer dans le Catalogue Fédéré, et rejette tout *Skill* violant les contraintes d'isolation.

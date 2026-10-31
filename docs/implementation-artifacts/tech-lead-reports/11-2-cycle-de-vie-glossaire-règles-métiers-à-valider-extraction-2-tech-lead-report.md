# Rapport Tech Lead — Story 11.2 : Chaîne Causale ADN (`DIRECTIVE ➔ NORME ➔ MÉCANISME`), Compilateur `Text-to-Starlark` Palier 1b (`< 2 ms`), Cycle de Vie du Glossaire (`✨ À valider <= 15 FIFO`) & Promotion *In-Flow* (`Verrou V4`)

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Problématique
La **Story 11.2** concrétise les emprunts architecturaux ciblés à Poesis (`sie-operator` et `gsm-ontology`) sans introduire de dette JVM ni Neo4j, ainsi que le **Verrou V4** sur le cycle de vie du Glossaire :
1. **Chaîne Causale ADN (`🛡️ DIRECTIVE ➔ 📏 NORME ➔ ⚙️ MÉCANISME`, `AD-7`)** : Enrichir `ontology_concepts`, `ontology_axioms` et `ontology_relations` avec `dna_stereotype` (`CONCEPT | DIRECTIVE | NORM | MECHANISM`), `mechanism_payload_jsonb` et les prédicats `OPERATIONALIZES_DIRECTIVE` / `IMPLEMENTS_NORM`, affichant sur 1 ligne dans le `CognitiveReviewBriefing` le fil d'Ariane causal complet.
2. **Compilateur Design-Time `Text-to-Starlark` & `StarlarkMechanismSandbox` Palier 1b (`AD-9`)** : Permettre de compiler une Norme exprimée en français en un mécanisme de Gate déterministe `Starlark` auto-testé (`PASS` sur `passing_test_payload`, `FAIL` sur `failing_test_payload` en `< 5 ms` au Design-Time avec validation JSON Schema préalable et 1 boucle de *Self-Correction*), puis exécuté en **`< 2 ms` et `0 token` LLM** au Run-Time (avec regex en temps linéaire $O(n)$ anti-ReDoS et `orcia_sys.emit_effect` confiné aux Actions Staged).
3. **Extraction en 2 Passes & Promotion *In-Flow* (`Verrou V4`, `AD-8`, `AD-11`)** :
   - **Passe 1 déterministe (`0 $` LLM)** : seule autorisée sur un simple `git push`, dédupliquant contre `ontology_concepts` et filtrant les empreintes rejetées (`REJECTED_CANDIDATE`) ;
   - **Passe 2 de consolidation LLM bornée (`Top-15`)** : déclenchée uniquement sur MR/PR, synchronisation manuelle ou passage de Gate, plafonnant la file `✨ À valider (N)` à **maximum `15` candidats actifs par Espace** (FIFO + purge TTL 30j) et exposant les **`Top-3` termes L4 ($\ge 0.85$)** sous forme de cases pré-cochées dans le Briefing 4 blocs (`Verrou V4`), avec simulation d'impact *What-If* et invalidation immédiate du cache Redis du prompt de `Mon Assistant`.

### 1.2 Analyse d'Impact GitNexus
- `gitnexus_impact({target: "OntologyGovernanceService", direction: "upstream", repo: "ORCIA"})` : `risk: LOW`, `impactedCount: 6`.
- Respect strict d'`AD-19` : `StarlarkMechanismSandbox` est isolé dans `packages/orcia-core/src/orcia_core/gates/_internal/starlark_sandbox.py`, et le service d'extraction/DNA/compilation est exposé sans violation `lint-imports`.

---

## 2. Plan d'Implémentation

### 2.1 Migrations Alembic (`0027_story_11_2_dna_chain_and_glossary_lifecycle.py`)
- Ajout des colonnes `dna_stereotype VARCHAR(32) NOT NULL DEFAULT 'CONCEPT'` et `mechanism_payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb` sur `ontology_concepts` et `ontology_axioms` (`Expand -> Backfill -> Contract`), ainsi que de la table `ontology_rejected_candidates` pour mémoriser les empreintes `REJECTED_CANDIDATE`.

### 2.2 Noyau Hexagonal (`packages/orcia-core`)
- `packages/orcia-core/src/orcia_core/gates/_internal/starlark_sandbox.py` : `StarlarkMechanismSandbox` déterministe (`max_steps = 100_000`, regex temps linéaire $O(n)$ anti-ReDoS, `orcia_sys.emit_effect` confiné aux Actions Staged, exécution `< 2 ms`).
- `packages/orcia-core/src/orcia_core/orchestration/dna_starlark_and_glossary_lifecycle.py` : `DnaStarlarkAndGlossaryLifecycleService` réunissant la chaîne causale ADN (`DIRECTIVE ➔ NORME ➔ MÉCANISME`), `TextToStarlarkCompilerService` (avec validation JSON Schema des payloads de test, auto-test `< 5 ms` et 1 retry de *Self-Correction*), et l'extracteur 2 passes + file FIFO `<= 15` + promotion *In-Flow* `Top-3` (`Verrou V4`).

### 2.3 Backend FastAPI & SDK OpenAPI (`apps/api`)
- Schémas dans `apps/api/src/orcia_api/schemas/epic11_governance.py` et endpoints dans `apps/api/src/orcia_api/routers/epic11_workspace_governance.py` (`/dna-mechanisms/compile`, `/dna-mechanisms/evaluate`, `/glossary/extract`, `/glossary/promote-in-flow`).

### 2.4 Interface SPA Direction C (`packages/ui`)
- Primitive `@orcia/ui` `DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` affichant le fil d'Ariane causal `🛡️ DIRECTIVE ➔ 📏 NORME ➔ ⚙️ MÉCANISME`, le badge `✓ Vérifié sur cas de test (PASS/FAIL en < 5 ms)`, la file `✨ À valider (N <= 15)` et les `Top-3` cases pré-cochées du Briefing 4 blocs (`Verrou V4`).

---

## 3. Bilan des Modifications & Résultats

| Fichier | Action | Rôle |
|---|---|---|
| `infra/migrations/versions/0027_story_11_2_dna_chain_and_glossary_lifecycle.py` | Créé | Migration PG18 `dna_stereotype`, `mechanism_payload_jsonb` & `ontology_rejected_candidates` |
| `packages/orcia-core/src/orcia_core/gates/_internal/starlark_sandbox.py` | Créé | `StarlarkMechanismSandbox` Palier 1b (`< 2 ms`, anti-ReDoS $O(n)$, Staged effects) |
| `packages/orcia-core/src/orcia_core/orchestration/dna_starlark_and_glossary_lifecycle.py` | Créé | Chaîne ADN, Compilateur `Text-to-Starlark` & Cycle de vie Glossaire 2 passes (`Verrou V4`) |
| `packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` | Créé | Primitive Direction C `@orcia/ui` pour Story 11.2 |
| `tests/unit/test_epic_11_story_11_2_dna_starlark_and_glossary.py` | Créé | Tests unitaires & contrat API FastAPI |
| `tests/integration/test_story_11_2_dna_and_glossary_postgres18_redis.py` | Créé | Tests d'intégration réels PG18 + Redis 7.4 `testcontainers` |

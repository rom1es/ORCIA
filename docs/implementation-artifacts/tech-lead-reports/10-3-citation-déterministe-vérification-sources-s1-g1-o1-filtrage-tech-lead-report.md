# Rapport Tech Lead — Story 10.3 : Citation Déterministe & Vérification des Sources (`[S1]`, `[G1]`, `[O1]`), Filtrage Dynamique par Lecteur & Verrou V5 (`AD-15`)

- **Story Key** : `10-3-citation-déterministe-vérification-sources-s1-g1-o1-filtrage`
- **Epic** : `Epic 10 — Mon Assistant All-in-One (Compagnon Gouverné, 3 Vitesses, Citations & Dossiers)`
- **Date** : `2026-10-31`
- **Statut** : `done`
- **Auteur** : Tech Lead / Senior Dev Agent (`AD-15`, `AD-19`, `AD-21`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Problématique
Dans `Mon Assistant`, chaque affirmation doit être reliée à une preuve vérifiable sans jamais exposer le contenu d'une source restreinte à un co-lecteur non habilité dans un fil partagé, et sans permettre de contourner les Gates d'un Processus pour modifier directement le SI (`git://`, `confluence://`, `jira://`) ou officialiser un artefact `@v1`. **Story 10.3** implémente :
1. **Table des Preuves numérotée (`EvidenceTable`)** construite par le Nœud 3 (`parallel_context_fan_out`) et injectée au Nœud 4 (`prompt_layer_assembly`) :
   - `[S1..Sn]` : Sources documentaires triées avec priorité absolue des sources **`REFERENCE`** sur les sources **`ACTIVE`**, accompagnées de leur statut de fraîcheur (`FRESH` ou `STALE_WARNING`).
   - `[G1..Gn]` : Termes du Glossaire et Axiomes `N1–N3` de l'Ontologie.
   - `[O1..On]` : Résultats d'outils MCP / Connecteurs.
2. **Événement SSE `citation_map` (`t = 80 ms`) & Filtrage RBAC Dynamique par Lecteur (`READ_SOURCE`)** :
   - Si un lecteur d'un fil partagé ne possède pas `READ_SOURCE` sur `[S1]`, le backend purge `snippet = None` côté serveur et renvoie la pilule dégradée **`[S1 · 🔒 Source restreinte — Demander l'accès]`**.
3. **Vérificateur déterministe post-stream (`< 5 ms`) contre les citations fantômes** :
   - Toute balise hors bornes inventée par le LLM (`[S99]`, `[G42]`, `[O9]`) est remplacée par **`[Citation non vérifiée]`** et journalisée dans l'`audit_ledger` (`PHANTOM_CITATION_STRIPPED`).
4. **Carte d'Artefact Structurée & Verrou V5 (`AD-15`)** :
   - Actions autorisées : `📋 Copier`, `⬇ Exporter (.md / .json)`, `💾 Enregistrer en brouillon (@draft)`, **`☍ Continuer dans un Processus →`**.
   - **Verrou V5** : Toute tentative d'écriture directe vers le SI (`git://`, `confluence://`, `jira://`) ou d'officialisation `@v1` depuis `Mon Assistant` lève **`HTTP 422 ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE`** (`DirectSiWriteRequiresProcessGateError`).

### 1.2 Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- `gitnexus_impact({target: "DirectSiWriteRequiresProcessGateError", direction: "upstream", repo: "ORCIA"})` : erreur domaine créée en `Story 10.1` dans `packages/orcia-core/src/orcia_core/orchestration/errors.py`.
- Création d'un module dédié `packages/orcia-core/src/orcia_core/orchestration/assistant_citations_and_v5_guard.py` (`< 380` lignes, `0` import de framework).

---

## 2. Plan d'Implémentation

### 2.1 Base de Données (`audit_ledger`)
- Les citations fantômes remplacées par `[Citation non vérifiée]` sont persistées en mode strictement append-only dans `audit_ledger` (`action = 'PHANTOM_CITATION_STRIPPED'`).

### 2.2 Noyau Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/assistant_citations_and_v5_guard.py`)
- `EvidenceSourceCitation` (`tag: [S1]`, `authority_tier: REFERENCE | ACTIVE`, `freshness: FRESH | STALE_WARNING`, `snippet`, `restricted_access`).
- `EvidenceGlossaryCitation` (`tag: [G1]`), `EvidenceToolCitation` (`tag: [O1]`).
- `AssistantCitationAndV5GuardService` :
  - `build_evidence_table(...)` (tri `REFERENCE` > `ACTIVE` et numérotation `[S1..Sn]`, `[G1..Gn]`, `[O1..On]`).
  - `filter_citation_map_for_reader(user, evidence_table, allowed_source_uris)` (purge `snippet = None` et libellé `[S1 · 🔒 Source restreinte — Demander l'accès]`).
  - `verify_and_sanitize_citations(response_text, evidence_table)` (`< 5 ms`, remplace `[S99]` par `[Citation non vérifiée]` + entrée d'audit).
  - `execute_artifact_card_action(...)` (autorise `SAVE_DRAFT` `@draft` et `CONTINUE_IN_PROCESS`, bloque `DIRECT_SI_WRITE` / `PUBLISH_V1_VAULT` avec `DirectSiWriteRequiresProcessGateError` `422 ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE`).

### 2.3 Backend FastAPI (`apps/api/src/orcia_api/routers/epic10_assistant.py`)
- `POST /api/v1/assistant/citations/verify-turn`
- `POST /api/v1/assistant/citations/filter-for-reader`
- `POST /api/v1/assistant/artifacts/action` (application du Verrou V5 `AD-15`)

### 2.4 Interface SPA (`packages/ui/src/primitives/AssistantCitationPillsAndArtifactCard.tsx`)
- Pilules interactives `[S1]`, `[G1]`, `[O1]` avec carte d'aperçu au survol, pilule `[S1 · 🔒 Source restreinte — Demander l'accès]`, pied replié `📚 X sources consultées ([S1]..[SX]) · Y termes du Glossaire ([G1]..[GY]) ▾`, et Carte d'Artefact Structurée avec Verrou V5.

---

## 3. Bilan des Modifications & Résultats

| Fichier | Action | Rôle |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_citations_and_v5_guard.py` | Créé | Table des Preuves `[S1]/[G1]/[O1]`, filtrage `READ_SOURCE`, anti-citation fantôme `< 5 ms` & Verrou V5 (`AD-15`) |
| `apps/api/src/orcia_api/schemas/assistant.py` | Modifié | Schémas `CitationMapResponse`, `VerifyCitationsRequest/Response`, `ArtifactCardActionRequest/Response` |
| `apps/api/src/orcia_api/routers/epic10_assistant.py` | Modifié | Endpoints `/citations/verify-turn`, `/citations/filter-for-reader`, `/artifacts/action` |
| `packages/ui/src/primitives/AssistantCitationPillsAndArtifactCard.tsx` | Créé | Primitive UI `@orcia/ui` Direction C pour les pilules `[S1]/[G1]/[O1]` et la Carte d'Artefact V5 |
| `tests/unit/test_epic_10_story_10_3_citations_and_v5_guard.py` | Créé | Tests unitaires & API du tri `REFERENCE > ACTIVE`, filtrage `READ_SOURCE`, `[Citation non vérifiée]` et `422 ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE` |
| `tests/integration/test_story_10_3_phantom_citation_audit_postgres18.py` | Créé | Test d'intégration réel PostgreSQL 18 (`testcontainers`) d'inscription append-only dans `audit_ledger` |
| `packages/ui/src/__tests__/epic10-assistant.test.tsx` | Modifié | Test Vitest de `AssistantCitationPillsAndArtifactCard` |

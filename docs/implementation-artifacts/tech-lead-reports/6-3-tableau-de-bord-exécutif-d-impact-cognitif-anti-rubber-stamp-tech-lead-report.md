# Story 6.3 — Tableau de Bord Exécutif d'Impact Cognitif, Anti-Rubber-Stamping & Indice de Réversibilité Humaine

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code applicatif)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/6-3-tableau-de-bord-exécutif-d-impact-cognitif-anti-rubber-stamp-tech-lead-report.md`

- **Date** : 2026-11-16
- **Story / Clé Sprint** : `6-3-tableau-de-bord-exécutif-d-impact-cognitif-anti-rubber-stamp` (`Epic 6`)
- **Capacité(s)** : `CAP-200` (Gouvernance cognitive & réversibilité humaine dans FinOps) — classification : `feature` (voir `AGENTS.md` §5 et `capabilities.yaml`)
- **Auteur / Contexte** : Winston (`bmad-agent-architect` 🏗️) & Sally (`bmad-agent-ux-designer` 🎨). Mesure des 3 contre-métriques d'impact cognitif et de maîtrise humaine (`Ratio Cadrage Actif >= 40%`, `Taux de Validations Expéditives < 5%`, `Indice de Conformité d'Architecture & Réversibilité 0%`), moteur de recommandation d'allègement ou de renforcement des Gates, agrégation SQL pure dans `orcia_core/audit_finops/_internal/sql_cognitive_impact.py` (respectant `AD-19 Contract 2` avec zéro import de `orcia_core.gates`), composant `@orcia/ui` `FinopsHumanMasteryTab.tsx` monté sur `/finops` avec vocabulaire strictement exempt de jargon (`fr.ts`/`en.ts`) et protection par `enforce_scope_mutation_guard`. Couvre `FR-27`, `AD-17`, `AD-19`, `AD-20`, `SM-C1`, `SM-C2`, `SM-C3`, `UX-DR2` et `UX-DR5`.
- **Commits associés** : `pending-implementation`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
Dans les flux de travail accélérés par l'IA, la présence humaine peut devenir une illusion de sécurité (*Rubber-Stamping*) :
1. **Validation aveugle et fatigue de revue (*Gate Fatigue*)** : Face à des artefacts verbeux générés en quelques secondes, les experts humains risquent d'approuver machinalement sans lecture approfondie (approbation d'un document de 1 500 mots en moins de 15 secondes sans ouvrir le briefing de revue).
2. **Déséquilibre de la posture intellectuelle** : Les experts sont souvent cantonnés à une relecture passive en bout de chaîne plutôt qu'au cadrage initial des intentions du problème (ancres humaines, arbitrages, formulation des contraintes).
3. **Dérive architecturale insidieuse (*Pattern Drift*)** : L'injection de code ou de schémas générés peut violer les règles fixées dans l'Architecture Spine ou l'ontologie d'entreprise sans dérogation explicite.
4. **Nécessité de recommandations actionnables** : Si un workflow présente un taux de succès de $100\%$ sur 30 jours avec des revues expéditives et zéro commentaire, le système doit recommander au Tech Lead d'alléger la Gate (passage en politique par échantillonnage `sampling` à 20% ou ciblée sur le risque `risk_based`) ou de renforcer les ancrages humains obligatoires en amont.
5. **Impératif ergonomique Direction C** : Tout vocabulaire anxiogène ou interne (« Rubber-Stamping », « Pattern Drift », « < 15 s ») est strictement prohibé dans l'UI et les fichiers de traduction (`i18n-and-shell.test.tsx`). L'interface doit employer une sémantique constructive et valorisante (« Maîtrise humaine et qualité », « Cadrage actif d'intention », « Validation expéditive »).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `AdaptiveHumanGateService` (`packages/orcia-core/src/orcia_core/gates/human.py`) : fournit déjà `review_duration_ms` et `fast_approval_warning`.
  - `gate_evaluations`, `human_anchor_signatures`, `human_arbitration_requests` : tables sources en base.
  - **Frontière stricte `AD-19 Contract 2`** : `audit_finops` réside dans la Couche 2 au même titre que `gates`. **Interdiction formelle pour `audit_finops` d'importer `orcia_core.gates`**. La solution consiste à effectuer l'agrégation directement en SQL asynchrone (`sa.text`) sur les tables sans coupler les modules Python.
  - `enforce_scope_mutation_guard` : doit sécuriser l'application de toute recommandation de politique de Gate (`POST /api/v1/finops/gates/policy-recommendation/{id}/apply`).
- **Exploration & Données Chiffrées** :
  - Les 3 métriques sont calculées sur fenêtres glissantes (`7D`, `30D`, `90D`) avec agrégation par Workflow, Équipe et Direction (BU).
  - Le ratio de cadrage actif mesure le temps passé sur les ancrages obligatoires et arbitrages rapporté au temps humain total.
- **Opportunités de Factorisation & Dette Technique** :
  - Réutilisation de la structure des cartes de score Direction C (`packages/ui/src/primitives/finops/CognitiveMetricCard.tsx`) avec jauges visuelles colorées (vert, ambre, cobalt).
  - Évitement de toute duplication de logique grâce au service centralisé `cognitive_impact_service.py`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune modification de schéma relationnel n'est requise pour cette Story : les tables nécessaires (`gate_evaluations`, `human_anchor_signatures`, `human_arbitration_requests`, `audit_ledger`, `workspace_exception_waivers`) existent déjà en base de données PostgreSQL 18.
- Utilisation exclusive d'index existants sur `gate_evaluations(created_at, reviewer_user_id)` et `human_anchor_signatures(created_at)`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers
- **Requêtes d'Agrégation SQL Directes (`packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_cognitive_impact.py`)** :
  - Requêtes SQL pures calculant :
    1. Le temps cumulé sur `human_anchor_signatures` et `human_arbitration_requests` vs le temps total passé sur `gate_evaluations` (Ratio Cadrage Actif).
    2. La proportion d'approbations ayant `fast_approval_warning = TRUE` ou durée $< 15 000$ ms (Taux de Validation Expéditive).
    3. Les dérogations et écarts enregistrés dans `workspace_exception_waivers` et `audit_ledger` (Indice de Dérive d'Architecture).
  - Isolation totale : zéro import de `orcia_core.gates`.
- **Moteur de Recommandations (`packages/orcia-core/src/orcia_core/audit_finops/cognitive_impact_service.py`)** :
  - Calcul des métriques avec seuils :
    - Ratio Cadrage Actif : vert si $\ge 40\%$, ambre si $< 40\%$.
    - Taux Validation Expéditive : vert si $< 5\%$, rouge si $\ge 5\%$.
    - Dérive Architecture : vert si $0\%$, rouge si $> 0\%$.
  - Moteur d'évaluation périodique : si un workflow affiche sur 30 jours $> 98\%$ d'approbations rapides sans commentaire, génération d'une recommandation actionnable d'allègement (`sampling` 20% ou `risk_based`) ou de renforcement des ancrages amont.

### 2.3 Couche Backend API, Sécurité & Contrats
- **Schémas RFC 9457 (`apps/api/src/orcia_api/schemas/finops.py`)** :
  - `CognitiveImpactDashboardResponse`, `CognitiveMetricItemSchema`, `GatePolicyRecommendationSchema`, `ApplyRecommendationRequest`, `ApplyRecommendationResponse`.
- **Endpoints FastAPI (`apps/api/src/orcia_api/routers/finops.py`)** :
  - `GET /api/v1/finops/cognitive-impact` : restitution des métriques agrégées, filtres temporels et recommandations actives.
  - `POST /api/v1/finops/gates/policy-recommendation/{recommendation_id}/apply` : application de la recommandation sous la garde `enforce_scope_mutation_guard` (`HTTP 403` si observateur).
- **Client TypeScript & OpenAPI SDK (`packages/api-client/`)** :
  - Régénération du SDK via `scripts/export_openapi.py` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/` & `@orcia/ui`)
- **Composants `@orcia/ui` (`packages/ui/src/primitives/finops/`)** :
  - `FinopsHumanMasteryTab.tsx` : affichage des 3 cartes d'indicateurs de maîtrise humaine, des bannières de recommandations et de l'historique d'arbitrage.
  - `CognitiveMetricCard.tsx` : carte individuelle avec jauge visuelle de santé, valeur cible et statut contextuel.
- **Vocabulaire i18n Strictement Sans Jargon (`apps/web/src/i18n/locales/{fr,en}.ts`)** :
  - Respect strict de l'interdiction de termes bruts.
  - Formulations retenues : « Maîtrise humaine et qualité », « Cadrage actif d'intention », « Validation expéditive », « Conformité architecturale ».
  - Validation automatique par `apps/web/src/__tests__/i18n-and-shell.test.tsx`.
- **Montage dans `apps/web/src/features/finops/index.tsx`** :
  - Ajout de l'onglet `Maîtrise humaine & Qualité` dans le `FinopsGovernanceDashboardView`.
  - Câblage des actions d'application de recommandations sans bouton muet (`zero-dead-buttons-and-silent-catches-audit.test.tsx`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python)** :
  - `test_story_6_3_cognitive_impact_service.py` : calcul déterministe des ratios, respect des seuils d'alerte et logique de génération des recommandations.
- **Couche 1b (Composants TS `Vitest`)** :
  - Rendu de l'onglet `FinopsHumanMasteryTab`, interaction avec la recommandation et survie au rechargement de page (`F5`).
- **Couche 2 (Intégration `testcontainers` PostgreSQL 18)** :
  - `test_story_6_3_cognitive_impact_postgres18.py` : insertion d'évaluations de Gates réelles et vérification de l'agrégation SQL asynchrone sans chargement mémoire.
- **Couche 3 (Contrats OpenAPI & `lint-imports`)** :
  - Vérification du respect strict du contrat `Contract 2` (zéro import de `gates` dans `audit_finops`).
- **Couche 4 (Evals Déterministes `0 $`)** :
  - `tests/evals/test_story_6_3_cognitive_governance_evals.py` : test de bout en bout de l'évaluation d'impact cognitif sur jeu doré.
- **Couche 5 (E2E Playwright)** :
  - `apps/web/e2e/12-finops-and-audit-provenance.spec.ts` : scénario complet de consultation de l'onglet de maîtrise humaine et application d'une recommandation.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *Section réservée à l'implémentation par le dev worker (`bmad-dev-worker` ⚡).*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/audit_finops/cognitive_impact_service.py` | Création | Moteur de calcul des contre-métriques et des recommandations d'ajustement |
| `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_cognitive_impact.py` | Création | Requêtes SQL pures d'agrégation d'impact cognitif sans import de `gates` |
| `packages/ui/src/primitives/finops/FinopsHumanMasteryTab.tsx` | Création | Onglet Maîtrise humaine & Qualité |
| `packages/ui/src/primitives/finops/CognitiveMetricCard.tsx` | Création | Carte individuelle de métrique cognitive avec jauge |
| `apps/api/src/orcia_api/schemas/finops.py` | Modification | Schémas RFC 9457 pour l'impact cognitif et les recommandations |
| `apps/api/src/orcia_api/routers/finops.py` | Modification | Endpoints `/api/v1/finops/cognitive-impact` et application |
| `apps/web/src/features/finops/index.tsx` | Modification | Intégration de l'onglet de maîtrise humaine |
| `apps/web/src/i18n/locales/fr.ts` | Modification | Traductions françaises soignées sans aucun jargon |
| `apps/web/src/i18n/locales/en.ts` | Modification | Traductions anglaises soignées sans aucun jargon |
| `tests/unit/test_story_6_3_cognitive_impact_service.py` | Création | Tests unitaires des algorithmes de calcul et règles d'alerte |
| `tests/integration/test_story_6_3_cognitive_impact_postgres18.py` | Création | Tests d'intégration testcontainers PostgreSQL 18 |
| `tests/evals/test_story_6_3_cognitive_governance_evals.py` | Création | Évaluation déterministe à 0 $ sur jeu doré |
| `apps/web/e2e/12-finops-and-audit-provenance.spec.ts` | Création | Test Playwright E2E de consultation et d'arbitrage |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : Requis $\ge 90\%$.
- **Performances mesurées** : Agrégation SQL de maîtrise humaine $< 20$ ms.
- **Qualité statique & Architecture** :
  - `ruff check` & `ruff format --check` : `0 warning`
  - `mypy --strict` & `pnpm typecheck` : `0 error`
  - `lint-imports` : `5 contracts kept, 0 broken` (0 import croisé `gates`)
  - `lint_spine.py` : `ok: true, 0 findings`
  - `gitnexus_detect_changes()` : Périmètre conforme.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a & 1b** : Exactitude des ratios et conformité des libellés UI au filtre anti-jargon.
- **Couche 2** : Requêtes SQL sur conteneur réel PostgreSQL 18 sans aucune dépendance framework.
- **Couche 3** : Respect strict du contrat d'isolation hexagonale `import-linter`.
- **Couche 4** : Évaluation déterministe à 0 $ validant les alertes de relecture rapide.
- **Couche 5** : Scénario E2E Playwright validant l'application sécurisée d'une recommandation.

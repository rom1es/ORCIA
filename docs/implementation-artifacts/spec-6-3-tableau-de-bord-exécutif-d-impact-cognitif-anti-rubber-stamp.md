---
story_key: "6-3-tableau-de-bord-exécutif-d-impact-cognitif-anti-rubber-stamp"
status: "ready-for-dev"
epic: "epic-6"
title: "Story 6.3 : Tableau de Bord Exécutif d'Impact Cognitif, Anti-Rubber-Stamping & Indice de Réversibilité Humaine"
date: "2026-11-16"
authors:
  - "Winston (bmad-agent-architect 🏗️)"
  - "Sally (bmad-agent-ux-designer 🎨)"
capabilities:
  - "CAP-200"
---

# Spécification d'Implémentation — Story 6.3 : Tableau de Bord Exécutif d'Impact Cognitif, Anti-Rubber-Stamping & Indice de Réversibilité Humaine

- **Story Key** : `6-3-tableau-de-bord-exécutif-d-impact-cognitif-anti-rubber-stamp`
- **Epic** : Epic 6 — Gouvernance Exécutive, Provenance Auditable Immuable, FinOps Consolidé & Réversibilité Humaine
- **Capacité rattachée** : `CAP-200` (Tableau de bord FinOps & gouvernance de maîtrise cognitive)
- **Références architecturales** : `FR-27`, `AD-17`, `AD-19`, `AD-20`, `SM-C1`, `SM-C2`, `SM-C3`, `UX-DR2`, `UX-DR5`

---

## 1. Intent & Boundaries

### 1.1 Problem & Approach
L'adoption massive des capacités génératives et de l'orchestration autonome risque de dégrader la posture intellectuelle des experts en les reléguant à de simples approbateurs passifs validant des livrables sans lecture critique approfondie (*Rubber-Stamping*), tout en favorisant une dérive architecturale insidieuse (*Pattern Drift*).
Cette story implémente :
1. L'agrégation directe en SQL pur (dans `orcia_core/audit_finops/_internal/sql_cognitive_impact.py`) des 3 contre-métriques d'impact cognitif et de maîtrise humaine (`FR-27`) :
   - **Ratio de Cadrage Actif d'Expert (*Human-Led Think*, `SM-C2`)** : cible $\ge 40\%$.
   - **Taux de Validation Expéditive / Rubber-Stamping (`SM-C1`)** : seuil toléré $< 5\%$.
   - **Indice de Dérive d'Architecture & Réversibilité (`SM-C3`)** : cible absolue $0\%$.
2. Un moteur de recommandations d'ajustement actionnables détectant les workflows ayant $> 98\%$ d'approbations rapides sans modification/commentaire sur 30 jours, proposant soit d'alléger la Gate en politique par échantillonnage (`sampling` 20%) ou basée sur le risque (`risk_based`), soit de renforcer les ancres humaines en amont.
3. L'onglet `@orcia/ui` `FinopsHumanMasteryTab.tsx` intégré dans `/finops` avec un vocabulaire **strictement exempt de tout jargon** dans les fichiers de traduction (`fr.ts`, `en.ts`) et dans les libellés JSX (validé par `i18n-and-shell.test.tsx`).
4. Le respect strict de la frontière `AD-19` : **zéro import de `orcia_core.gates`** dans `orcia_core.audit_finops` (les tables `gate_evaluations`, `human_anchor_signatures` et `human_arbitration_requests` sont lues directement via SQL).

### 1.2 Boundaries & Constraints
- **Toujours (`Always`)** :
  - Respecter l'isolation modulaire `AD-19` : `audit_finops` (Couche 2) ne doit **jamais** importer le module pair `orcia_core.gates` (Couche 2) ; toutes les requêtes croisées s'effectuent par requêtes SQL asynchrones.
  - Calculer les métriques sur fenêtres temporelles glissantes paramétrables (`7D`, `30D`, `90D`) avec support des filtres hiérarchiques (`GLOBAL`, `BU`, `TEAM`, `WORKSPACE`).
  - Utiliser une terminologie claire et accessible dans l'interface : « Maîtrise humaine et qualité », « Cadrage actif d'intention », « Validation expéditive », « Temps de relecture trop court », « Écart de conformité architecturale ».
  - Protéger l'application des recommandations via `enforce_scope_mutation_guard` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`).
  - Couvrir les calculs et alertes par des évaluations déterministes à `0 $` (`tests/evals/test_story_6_3_cognitive_governance_evals.py`).
- **Jamais (`Never`)** :
  - Ne jamais introduire de termes anglais bruts ou de jargon dans les textes visibles utilisateur (interdiction formelle de `Rubber-Stamping`, `Pattern Drift`, `< 15 s` dans `fr.ts`/`en.ts`/JSX selon `i18n-and-shell.test.tsx`).
  - Ne jamais modifier automatiquement la politique de validation d'un workflow sans le consentement explicite et signé d'un responsable (`Marc UJ-5` ou `Claire UJ-8`).
  - Ne jamais injecter de logique de dépendance circulaire entre domaines dans le backend FastAPI.

### 1.3 I/O & Edge-Case Matrix

| Contexte / Indicateur | Mesure Observée | Résultat Métier | Statut / Alerte UI |
| :--- | :--- | :--- | :--- |
| Cadrage actif d'intention | Ratio $\ge 40\%$ | Équilibre sain entre cadrage amont et revue | Badge vert « Équilibré » |
| Dérive vers relecture passive | Ratio $< 40\%$ | Trop de temps passé à corriger au lieu de cadrer | Alerte ambre « Déséquilibre intention » |
| Approbation d'artefact lourd | Relecture $< 15$ s sur $> 1000$ mots | Marqueur `fast_approval_warning` activé | Comptabilisé dans le taux de validation expéditive |
| Taux de validation expéditive | Taux $\ge 5\%$ sur le périmètre | Risque élevé d'approbations aveugles | Alerte rouge pour le responsable d'équipe |
| Écart aux standards spine | Écart non couvert par dérogation | Non-conformité d'architecture détectée | Alerte rouge « Écart architectural » |
| Workflow ultra-stable | $> 98\%$ validation rapide, 0 modif sur 30j | Recommandation : basculer en `sampling` 20% | Carte d'action avec bouton « Appliquer » |
| Mode observateur | Clic sur « Appliquer la recommandation » | Rejet formel avec enveloppe RFC 9457 | `403 Forbidden` (`ERR_OBSERVER_MODE_READ_ONLY`) |

---

## 2. Acceptance Criteria (Given / When / Then)

### Critère 1 : Calcul des 3 Contre-Métriques de Maîtrise Humaine (`FR-27`)
- **Given** les données enregistrées dans `human_anchor_signatures`, `human_arbitration_requests`, `gate_evaluations` et `audit_ledger`,
- **When** l'utilisateur consulte l'onglet Maîtrise humaine & Qualité de l'écran `/finops`,
- **Then** le système calcule et affiche sur la fenêtre sélectionnée :
  1. Le **Ratio de Cadrage Actif d'Intention** ($\frac{\text{Temps ancrages} + \text{arbitrages} + \text{challenges}}{\text{Temps humain total}}$), avec alerte ambre dès lors qu'il descend sous $40\%$ ;
  2. Le **Taux de Validation Expéditive** (part des approbations avec `fast_approval_warning: true` ou sans consultation du briefing de revue), avec alerte rouge dès lors qu'il atteint ou dépasse $5\%$ ;
  3. L'**Indice de Dérive et Conformité Architecturale** (écarts constatés vis-à-vis des règles de l'Architecture Spine hors dérogations formelles), avec cible à $0\%$.

### Critère 2 : Moteur de Recommandations Actionnables d'Ajustement des Gates
- **Given** un workflow présentant sur 30 jours un taux de succès aux Gates $> 98\%$, avec un temps médian inférieur au seuil minimal et `0` modification ou commentaire,
- **When** le moteur d'impact cognitif évalue ce workflow,
- **Then** il émet une recommandation actionnable proposant :
  - soit d'alléger la Gate en politique par échantillonnage (`sampling` 20%) ou basée sur le risque (`risk_based`) afin d'éviter la lassitude des relecteurs (*Gate Fatigue*),
  - soit de renforcer les ancrages humains obligatoires en amont.

### Critère 3 : Isolation Hexagonale Stricte `import-linter` (`AD-19`)
- **Given** le package `packages/orcia-core/src/orcia_core/audit_finops/`,
- **When** la suite `.venv/bin/lint-imports` est exécutée,
- **Then** aucune importation directe du module `orcia_core.gates` n'est détectée dans `audit_finops`,
- **And** le contrat `Contract 2` d'orthogonalité Couche 2 est respecté avec `0` violation.

### Critère 4 : Interface Utilisateur `@orcia/ui` & Vocabulaire Sans Jargon
- **Given** le composant `FinopsHumanMasteryTab.tsx` monté dans l'écran `/finops`,
- **When** l'interface est affichée en français ou en anglais,
- **Then** tous les libellés utilisent un français et un anglais soignés, exempts de tout jargon interne ou anglicisme brut,
- **And** le test automatisé `apps/web/src/__tests__/i18n-and-shell.test.tsx` valide l'absence totale de termes proscrits dans le DOM.

### Critère 5 : Application Sécurisée des Recommandations & Pyramide des Tests
- **Given** une recommandation d'ajustement affichée dans l'interface,
- **When** un utilisateur en rôle contributeur ou responsable clique sur « Appliquer l'ajustement »,
- **Then** l'endpoint `POST /api/v1/finops/gates/policy-recommendation/{id}/apply` met à jour la politique de la Gate du workflow sous la garde `enforce_scope_mutation_guard`,
- **And** un auditeur en mode `READ_ONLY_OBSERVER` reçoit un code `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`.

---

## 3. Code Map

```
ORCIA/
├── packages/
│   ├── orcia-core/src/orcia_core/
│   │   └── audit_finops/
│   │       ├── cognitive_impact_service.py              [CRÉATION - Moteur de calcul des 3 métriques et recommandations]
│   │       └── _internal/
│   │           └── sql_cognitive_impact.py              [CRÉATION - Agrégation SQL asynchrone sans import gates]
│   └── ui/src/
│       ├── index.ts                                     [MODIFICATION - Export FinopsHumanMasteryTab]
│       └── primitives/finops/
│           ├── FinopsHumanMasteryTab.tsx                [CRÉATION - Onglet Maîtrise humaine & Qualité]
│           └── CognitiveMetricCard.tsx                  [CRÉATION - Carte de métrique avec jauge visuelle]
├── apps/
│   ├── api/src/orcia_api/
│   │   ├── schemas/
│   │   │   └── finops.py                                [MODIFICATION - Schémas RFC 9457 impact cognitif]
│   │   └── routers/
│   │       └── finops.py                                [MODIFICATION - Endpoints /api/v1/finops/cognitive-impact]
│   └── web/src/
│       ├── features/finops/
│       │   └── index.tsx                                [MODIFICATION - Intégration onglet Maîtrise humaine]
│       ├── i18n/locales/
│       │   ├── fr.ts                                    [MODIFICATION - Textes soignés sans jargon]
│       │   └── en.ts                                    [MODIFICATION - Textes anglais soignés]
│       └── e2e/
│           └── 12-finops-and-audit-provenance.spec.ts   [CRÉATION - Scénario E2E Playwright gouvernance]
└── tests/
    ├── unit/
    │   └── test_story_6_3_cognitive_impact_service.py   [CRÉATION - Tests unitaires calculs et règles d'alerte]
    ├── integration/
    │   └── test_story_6_3_cognitive_impact_postgres18.py[CRÉATION - Testcontainers PG18 requêtes d'agrégation]
    └── evals/
        └── test_story_6_3_cognitive_governance_evals.py [CRÉATION - Évaluations déterministes 0 $]
```

---

## 4. Ordered Tasks (Dependencies First)

### Tâche 1 : Requêtes d'Agrégation SQL Pures (Sans Import `gates`)
- Créer `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_cognitive_impact.py`.
- Rédiger les requêtes SQL asynchrones interrogeant `gate_evaluations`, `human_anchor_signatures`, `human_arbitration_requests` et `audit_ledger` pour agréger les durées actives, les avertissements `fast_approval_warning` et les dérives.
- Valider l'absence totale d'import de `orcia_core.gates`.

### Tâche 2 : Service Métier & Moteur de Recommandations
- Créer `packages/orcia-core/src/orcia_core/audit_finops/cognitive_impact_service.py`.
- Implémenter le calcul des 3 ratios : Ratio de cadrage actif, Taux de validation expéditive, Indice de conformité d'architecture.
- Implémenter le moteur de détection des situations de lassitude des relecteurs (taux $> 98\%$, revue rapide, 0 modif) et génération de recommandations.

### Tâche 3 : Endpoints Backend FastAPI & SDK OpenAPI
- Enrichir `apps/api/src/orcia_api/schemas/finops.py` avec les schémas d'impact cognitif et de recommandations.
- Ajouter dans `apps/api/src/orcia_api/routers/finops.py` :
  - `GET /api/v1/finops/cognitive-impact`
  - `POST /api/v1/finops/gates/policy-recommendation/{recommendation_id}/apply` (protégé par `enforce_scope_mutation_guard`).
- Régénérer le SDK client OpenAPI via `scripts/export_openapi.py` (`0-diff`).

### Tâche 4 : Composants `@orcia/ui` & Textes i18n Sans Jargon
- Développer `packages/ui/src/primitives/finops/FinopsHumanMasteryTab.tsx` et `CognitiveMetricCard.tsx`.
- Enrichir `apps/web/src/i18n/locales/{fr,en}.ts` avec un vocabulaire accessible (« Maîtrise humaine et qualité », « Cadrage actif d'intention », « Validation expéditive »).
- Valider le montage dans `apps/web/src/features/finops/index.tsx` sous l'onglet dédié.
- Vérifier la conformité au test `i18n-and-shell.test.tsx`.

### Tâche 5 : Pyramide des Tests `AD-17`, Evals & E2E
- Couche 1a : Tests unitaires Python des formules de ratios et des seuils d'alerte.
- Couche 1b : Tests composants Vitest et survie au rafraîchissement `F5`.
- Couche 2 : Test d'intégration `testcontainers` PostgreSQL 18 vérifiant la restitution exacte des indicateurs calculés sur données réelles.
- Couche 4 : Évaluation déterministe à 0 $ dans `tests/evals/test_story_6_3_cognitive_governance_evals.py`.
- Couche 5 : Scénario E2E Playwright `apps/web/e2e/12-finops-and-audit-provenance.spec.ts`.

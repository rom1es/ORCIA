# 2026-11-08 — TEST-06 : specs Playwright E2E P2 (pack-builder + aide ⓘ, ⌘K, écrans sans 5xx)

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-test-06-e2e-p2-specs` (`Ajustement Transverse` — tests, `Epic 13`, ticket `TEST-06`)
- **Capacité(s)** : `none (hygiène/NFR)` — classification `hygiène` ; couvre CAP-062, CAP-064, CAP-083 (partiel) et le chargement sans erreur serveur des écrans CAP-002/010/011/052-058/065/200
- **Branche dédiée** : `test/e2e-coverage-plan`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Suite de `TEST-04/05` : l'audit croisé avec `capabilities.yaml` montrait des capacités sans aucun E2E (Configuration, Ontologie, Catalogue, Journal d'activité, Coûts). Une spec « écrans sans 5xx » les protège à coût faible.

### 1.2 Exploration, Impact GitNexus, Factorisation & Dette
- **GitNexus** : specs Playwright uniquement ; aucun symbole applicatif modifié.
- **Factorisation** : `e2e/support/apiErrors.ts` (`watchApiServerErrors`) — collecte des réponses `/api/*` ≥ 500.

---

## 2. Plan d'Implémentation
- 2.4 : `09-pack-builder-and-contextual-help`, `10-command-palette-search`, `11-screens-smoke-without-server-errors`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

| Spec | Statut | Capacités / défaut |
| :--- | :--- | :--- |
| `09-pack-builder-and-contextual-help` | ✅ écran Processus (pack ORCIA) + colonne d'aide contextuelle ouvrable/fermable, zéro 5xx | CAP-064, CAP-083 (partiel) |
| `10-command-palette-search` | ✅ Ctrl+K / saisie / Escape ; ⚠️ recherche fédérée vitesse 2 en `test.fail` → **BUG-E2E-06** (422 + résultat local fabriqué) | CAP-062 |
| `11-screens-smoke-without-server-errors` | ✅ 7 écrans (cockpit, configuration, ontologie, catalogue, activité, coûts, aide) sans 5xx | CAP-002/010/011/052-058/065/200 |

- **Non couvert** : création/validation d'un pack via l'atelier (processus 1→5) et replay après Permission Broker (UJ-7) ; `PermissionBrokerCard` à rechercher dans le portail (probablement non monté, à qualifier).
- Aucun code applicatif modifié.

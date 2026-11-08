# 2026-11-08 — TEST-02 : réécriture de `shell.spec.ts` sur le shell 4 zones réel (Epic 12)

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-test-02-reparation-shell-spec-e2e` (`Ajustement Transverse` — tests, `Epic 13`, ticket `TEST-02`)
- **Capacité(s)** : `none (hygiène/NFR)` — classification `hygiène` ; couvre en E2E `CAP-060` (shell 4 zones) et `CAP-061` (accostage Jour 0)
- **Branche dédiée** : `test/e2e-coverage-plan`
- **Commits associés** : à renseigner.

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- `apps/web/e2e/shell.spec.ts` (≈130 lignes) cible l'ancien shell des Epics 1–2 : `sidebar-nav-item-*`, `global-sidebar`, `assistant-dock`, 8 libellés « Cockpit & Chat… », mode `?fixture=test`, boutons de simulation (`simulate-permission-denied-confluence-btn`…).
- Ce n'est **pas** une simple substitution de sélecteurs : le shell réel est `FourZoneDirectionCShell` (`eight-menu-item-*`, `four-zone-*`), le mode « fixture » et les données fictives ont été **purgés** (rapport 2026-11-05, politique zéro donnée fictive) et les parcours Catalogue/Ontologie/Bootstrap/Gates simulés n'existent plus sous cette forme.
- Les parcours métier sont repris, avec la vraie pile (TEST-01), par `TEST-04` à `TEST-06` ; `TEST-02` ne couvre donc que la **structure du shell** et l'état Jour 0.

### 1.2 Exploration, Impact GitNexus, Factorisation & Dette
- **GitNexus** : aucun symbole applicatif modifié (spec Playwright uniquement) → impact nul.
- **Sélecteurs réels** (`FourZoneDirectionCShell.tsx`) : `four-zone-direction-c-shell`, `four-zone-top-header-bar`, `four-zone-sidebar` (`data-rail-collapsed`), `four-zone-central-workspace`, `eight-menu-item-{cockpit,assistant,processes,agents,spaces,finops,configuration,help}` (`data-disabled-reason`, `aria-disabled` au Jour 0), `sidebar-rail-toggle-btn`, raccourci `[`, `topbar-contextual-help-toggle` / `four-zone-contextual-help-column`.
- **Dette** : suppression d'un test obsolète dont les assertions fonctionnelles (catalogue, ontologie, bootstrap, gates) sont à reconstruire dans `TEST-04..06` ; consignée dans la description de ces tickets.

---

## 2. Plan d'Implémentation
- 2.1 / 2.2 / 2.3 : non applicables.
- 2.4 : réécrire `apps/web/e2e/shell.spec.ts` (reset Jour 0 via `resetDay0()`, modale premier administrateur, 4 zones, 8 entrées sans préfixe numérique, état grisé Jour 0, raccourci `[`, colonne d'aide) ; exécuter sur `desktop-cockpit` et `mobile-companion` (assertions adaptées au viewport).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers
| Fichier | Nature | Description |
| :--- | :--- | :--- |
| `apps/web/e2e/shell.spec.ts` | Réécriture | Ancien parcours fictif (≈130 l., `sidebar-nav-item-*`, `?fixture=test`) remplacé par 4 tests sur la vraie pile : 4 zones + 8 entrées sans préfixe numérique, entrées grisées au Jour 0 (`data-disabled-reason`), raccourci `[`, modale Jour 0 accessible (`role=dialog`, `aria-modal`) qui bloque le shell |

### 3.2 Résultats
- `playwright test e2e/shell.spec.ts` : **7 passés, 1 ignoré** (raccourci `[` : bureau uniquement), 2 viewports, ~36 s ; `tsc --noEmit` exécuté.
- Premier essai : un test « bouton de repli » échouait car la modale Jour 0 **intercepte** les clics — comportement attendu ; remplacé par une assertion explicite du blocage.
- Les parcours fonctionnels de l'ancien spec (catalogue, ontologie, bootstrap, gates) ne sont pas portés ici : ils dépendaient de données fictives purgées ; ils sont à reconstruire dans `TEST-04..06`.
- Aucun code applicatif modifié ; `gitnexus_detect_changes` non applicable.

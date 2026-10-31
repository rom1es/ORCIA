# Story 9.1 — Coquille 4 Zones Direction C (8 Menus Non Numérotés, Terminologie Fixe `Espace`, Cockpit Épuré avec Extinction `0/0/0/0` & Séparation Cockpit vs Vue Fokus de Revue `Run #ID`)

- **Date** : 2026-10-31
- **Story / Clé Sprint** : `9-1-coquille-4-zones-direction-c-8-menus-non-numérotés-cockpit-ép` (`Epic 9`)
- **Auteur / Contexte** : Implémentation de la Coquille Ergonomique à 4 Zones (`TopHeaderBar 52px`, `Sidebar 240px/68px` aux 8 menus fixes non numérotés avec terminologie invariante `Espace`, `Zone Centrale 1fr` et `Colonne d'Aide Contextuelle ? 340px` auto-repliée sur `< 1440px` dès que `total >= 1`), extinction automatique des compteurs KPI `0/0/0/0` quand `total == 0`, et séparation entre décisions courtes `Tie-Break` sur place et bascule vers la Vue Fokus de Revue (`Run #ID`) avec verrou de présence Redis `SET lock:step:<step_execution_id> <user_id> NX EX 900` (`Principes A, C, E, F, G`, `AD-4`, `AD-19`, `UX-DR1`, `UX-DR2`).
- **Commits associés** : `Story 9.1`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- L'expérience utilisateur d'ORCIA nécessite dès la première seconde une coquille auto-descriptive à **4 zones strictes** évitant toute surcharge cognitive (Loi de Hick) :
  1. `TopHeaderBar` (`52px`) avec sélecteur fixe **`Espace : [Nom] ⌄`** (`⌘W`), recherche fédérée `⌘K`, bouton `? Aide`, tiroir `🔔 Notifications` (`420px`) et bouton `👤 Login` avec badge de Casquette métier.
  2. `Sidebar` (`240px` / `68px` Rail via `[`) présentant exactement les **8 entrées non numérotées** (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`) et en pied le sélecteur de Pack Métier.
  3. `Zone Centrale` (`1fr`).
  4. `Colonne d'Aide Contextuelle ?` (`340px` à droite, auto-repliée par défaut sur `< 1440px` dès que `total >= 1` décision est en attente).
- Sur le `Cockpit` (`/`), lorsque `total == 0`, l'affichage de compteurs `0/0/0/0` et de barres de filtres vides crée un bruit visuel inutile : ils doivent s'éteindre automatiquement au profit d'une bannière sobre `✅ Aucune décision en attente`, de l'accès rapide à `Mon Assistant` et des 3 cartes d'orientation. Lorsque `total >= 1`, les arbitrages courts (`Tie-Break` à 2–3 options) se tranchent en 1 clic sur place, tandis que les revues lourdes (`Ancrage Humain Violet`, `Briefing 4 blocs`, `Validation par Découpage`, `Challenge Amont What-If`) ouvrent la **Vue Fokus de Revue (`Mes Processus › Exécutions & Décisions › Run #ID`)** en acquérant automatiquement le verrou Redis (`SET lock:step:<step_execution_id> <user_id> NX EX 900`, `AD-4`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `repo: "ORCIA"`)** :
  - `AppShell` (`packages/ui/src/shell/AppShell.tsx`) : `risk: LOW`, `impactedCount: 3` (`InnerShellContainer` dans `apps/web/src/components/ShellContainer.tsx` et `RootLayoutComponent` dans `apps/web/src/routes/__root.tsx`).
  - `CockpitFeaturePanel` (`apps/web/src/features/cockpit/index.tsx`) : `risk: LOW`, `impactedCount: 11` (`ModuleWorkspaceView` et routes TanStack Router).
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 300 lignes`)** :
  - Création de deux primitives dédiées et pures dans `@orcia/ui` (`packages/ui/src/primitives/`) :
    1. `FourZoneDirectionCShell.tsx` (`< 250 lignes`) encapsulant les 4 zones, les 8 entrées non numérotées, le sélecteur `Espace : [Nom] ⌄` (`⌘W`), le tiroir `🔔 Notifications` (`420px`), le raccourci `[` (`240px` $\leftrightarrow$ `68px`) et la règle responsive d'auto-repli de la colonne `? Aide` (`340px`) sur `< 1440px` quand `total >= 1`.
    2. `StreamlinedCockpitView.tsx` (`< 250 lignes`) encapsulant l'extinction `0/0/0/0` quand `total == 0`, la résolution 1-clic des `Tie-Break` sur place et la bascule vers la `Vue Fokus de Revue (Run #ID)` avec acquisition du verrou `lock:step:<step_execution_id>`.
  - Extraction des dictionnaires bilingues `FR`/`EN` de l'Epic 9 dans `apps/web/src/i18n/locales/epic9_labels.ts` avec parité récursive à 100 % vérifiée par test automatique.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune nouvelle table SQL requise pour la Story 9.1 (s'appuie sur le verrou de présence Redis `lock:step:<step_execution_id>` défini par `AD-4`).

### 2.2 Noyau Métier & Primitives Design System (`packages/ui/`)
- `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` :
  - Implémentation de la grille 4 zones (`TopHeaderBar 52px`, `Sidebar 240px/68px` à 8 entrées non numérotées + sélecteur de Pack, `Zone Centrale 1fr`, `Colonne d'Aide Contextuelle ? 340px`) et de `computeDefaultHelpColumnOpen(viewportWidth, pendingDecisionsTotal)`.
- `packages/ui/src/primitives/StreamlinedCockpitView.tsx` :
  - Implémentation du Cockpit épuré (`total == 0` vs `total >= 1`, résolution `Tie-Break` en 1 clic sur place vs ouverture de la `Vue Fokus de Revue Run #ID` avec verrou `SET lock:step:<step_execution_id> <user_id> NX EX 900`).

### 2.3 Couche Frontend & i18n (`apps/web/`)
- `apps/web/src/i18n/locales/epic9_labels.ts`, `fr.ts`, `en.ts`, `types.ts` :
  - Dictionnaires typés `FR`/`EN` pour les 8 menus non numérotés, la coquille 4 zones et le Cockpit épuré.
- `apps/web/src/features/cockpit/index.tsx` :
  - Intégration du `StreamlinedCockpitView` tout en préservant les contrôles d'initialisation Jour 0 existants.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | Création | Coquille 4 zones (`52px`, `240px/68px`, `1fr`, `340px`), 8 menus non numérotés, sélecteur `Espace` & auto-repli `< 1440px` |
| `packages/ui/src/primitives/StreamlinedCockpitView.tsx` | Création | Cockpit épuré (extinction `0/0/0/0`, `Tie-Break` 1-clic sur place & bascule Vue Fokus de Revue `Run #ID` avec verrou Redis `AD-4`) |
| `packages/ui/src/index.ts` | Modification | Export public des primitives et types de la Story 9.1 |
| `apps/web/src/i18n/locales/epic9_labels.ts` | Création | Labels bilingues `FR`/`EN` de l'Epic 9 |
| `apps/web/src/features/cockpit/PlatformOnboardingChecklistCard.tsx` | Création | Extraction de la checklist d'initialisation Jour 0 pour ramener `features/cockpit/index.tsx` de 473 à 326 lignes |
| `apps/web/src/features/cockpit/index.tsx` | Modification | Intégration de la bannière `✅ Aucune décision en attente` et de l'atelier Fokus de Revue dans le Cockpit |
| `packages/ui/src/__tests__/epic9-shell-and-cockpit.test.tsx` | Création | Suite de tests unitaires Vitest couvrant l'intégralité des critères d'acceptation de la Story 9.1 |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `>= 90 %` sur `@orcia/ui` et `@orcia/web`.
- **Qualité statique & Architecture** :
  - `pnpm turbo run lint typecheck test` : `0 error`
  - `.venv/bin/lint-imports` : `0 broken`
  - `lint_spine.py` : `ok: true, 0 findings`

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 (Vitest)** : Vérification des 4 zones, des 8 entrées sans numéro, du repli `[` (`240px` $\leftrightarrow$ `68px`), de l'auto-repli de la Colonne `?` (`340px`) sur `< 1440px` quand `total >= 1`, de l'extinction des compteurs `0/0/0/0` quand `total == 0`, du `Tie-Break` sur place et de l'ouverture de la Vue Fokus de Revue `Run #ID` avec acquisition du verrou `SET lock:step:<step_execution_id> <user_id> NX EX 900`.

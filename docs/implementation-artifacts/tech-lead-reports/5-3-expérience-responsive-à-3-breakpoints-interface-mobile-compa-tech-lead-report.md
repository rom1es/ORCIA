# Story 5.3 — Expérience Responsive à 3 Breakpoints, Interface Mobile Companion Restreinte (3 Onglets) & Conformité Accessibilité WCAG 2.2 AA

- **Date** : 2026-10-30
- **Story / Clé Sprint** : `5-3-expérience-responsive-à-3-breakpoints-interface-mobile-compa` (`Epic 5`)
- **Auteur / Contexte** : Mise en œuvre des 3 paliers responsives (`Desktop >= 1280px`, `Laptop 768px - 1279px`, `Mobile Companion < 768px`), de l'interface Mobile Companion à 3 onglets bas (`🔔 Inbox`, `💬 Arbitrage/Chat`, `📄 Briefing`), du blocage explicite des fonctions lourdes sur mobile (*"Fonctionnalité réservée au poste Desktop"*, `UX-DR16`) et des badges sémantiques multi-signaux WCAG 2.2 AA (`NFR-A11Y-1`, `NFR-TEST-1`, `AD-17`).
- **Commits associés** : `working-tree`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Un valideur ou Tech Lead en déplacement doit pouvoir débloquer son équipe en moins de 10 minutes depuis un smartphone (`390x844`) sur les actions critiques (Claim, Arbitrage, Briefing 4 blocs) tout en étant protégé contre les manipulations lourdes inadaptées au mobile (édition YAML, co-édition multi-pages, administration).

### 1.2 Exploration, Factorisation & Contrôle de Volumétrie
- Création du composant isolé `<MobileCompanionView />` et de la fonction pure `resolveResponsiveBreakpoint(viewportWidthPx)` dans `packages/ui/src/primitives/MobileCompanionView.tsx` (`231` lignes), zéro couleur hexadécimale en dur, 100% piloté par le dictionnaire i18n FR/EN.

---

## 2. Plan d'Implémentation

### 2.1 Interface Utilisateur & Conformité WCAG 2.2 AA (`packages/ui/src/primitives/MobileCompanionView.tsx`)
- **Paliers responsives** : `DESKTOP` (`>= 1280px`), `LAPTOP` (`768–1279px`), `MOBILE` (`< 768px`).
- **Barre d'onglets basse Mobile Companion (3 entrées)** : `🔔 Inbox`, `💬 Arbitrage/Chat`, `📄 Briefing` avec approbation par découpage.
- **Restriction Desktop-Only (`UX-DR16`)** : bannière `role="alert"` *"Fonctionnalité réservée au poste Desktop"* affichée dès qu'une fonctionnalité lourde (`YAML_EDITOR`, `HEAVY_CO_EDITING`, `ADMIN_MODULE`) est sollicitée sur mobile.
- **Conformité WCAG 2.2 AA (`NFR-A11Y-1`)** :
  - Badges combinant **Couleur sémantique + Icône dédiée + Libellé explicite** : `✍️ Ancrage Humain`, `⚖️ Arbitrage IA`, `🛡️ Gate`, `🚨 Obsolète`.
  - Région `aria-live="polite"` annonçant les notifications et verrous SSE.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/ui/src/primitives/MobileCompanionView.tsx` | Création | Vue Mobile Companion 3 onglets, restriction Desktop-only et badges WCAG 2.2 AA |
| `apps/web/src/i18n/locales/epic5_labels.ts` | Création | Traductions FR/EN complètes pour Mobile Companion et badges WCAG |
| `packages/ui/src/__tests__/epic5-primitives.test.tsx` | Création | Tests Vitest des 3 breakpoints, de la bannière Desktop-only et des badges WCAG |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests Vitest `@orcia/ui`** : `22 passed` (`0` erreur TypeScript, `0` hexadécimal en dur).

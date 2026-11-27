## Epic 13: Évolutions Continues & Traçabilité des Capacités (Travaux Hors Epic Rattachés au PRD)

Garantir qu'aucune évolution fonctionnelle livrée hors Story ne reste orpheline : chaque demande ad-hoc fonctionnelle est rattachée à un FR du PRD, à une capacité `CAP-xxx` de `docs/product/capabilities.yaml` et à une Story rétroactive `13.x`. Les travaux d'hygiène (purge, accessibilité, câblage, refactoring) ne sont pas des fonctionnalités : ils se traitent comme NFR / garde-fous.
**FRs covered:** `FR-31`, `FR-32`, `FR-33`, `FR-34`, `FR-35`, `FR-36` (rattachement rétroactif des travaux hors epic).

### Story 13.1: Registre des Capacités, Contrôle de Couverture CI & Régularisation PRD v2

As a Product Owner / Tech Lead,
I want un registre unique des capacités livrées, relié au PRD, aux epics et aux surfaces réelles, contrôlé en CI,
So that je sache à tout moment ce qui est en place, quelle en est l'origine (epic ou ad-hoc), et que toute nouvelle route ou tout nouveau routeur soit rattaché à une capacité.

**Acceptance Criteria:**

**Given** `docs/product/capabilities.yaml`
**When** `pnpm site:check` s'exécute
**Then** il échoue si un `id` est dupliqué, un champ obligatoire manque, un `FR-n` n'existe pas dans le PRD, ou si une route SPA / un routeur FastAPI n'est ni référencé par une capacité ni listé dans `coverage_exemptions` avec une raison
**And** le PRD v2.0 définit `FR-31` à `FR-36` (§4.10) et la FR Coverage Map les référence.

### Story 13.2 (gabarit) : Évolution Fonctionnelle Rétroactive `13.x`

Toute demande ad-hoc fonctionnelle crée une Story `13.x` (rattachée au `FR-3x` concerné) ainsi qu'une entrée ou mise à jour `CAP-xxx` ; le rapport Tech Lead porte le champ `Capacité(s)`.

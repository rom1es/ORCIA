# Registre des Rapports d'Implémentation Tech Lead (Tech Lead Implementation Log)

Ce répertoire centralise l'historique et la traçabilité de toutes les implémentations de User Stories, décisions techniques et évolutions architecturales d'**ORCIA**.

---

## 📋 Standard d'Implémentation Obligatoire

Pour chaque User Story (`Story N.M`) ou évolution structurante, un rapport Tech Lead pérenne doit être rédigé dans ce dossier selon la convention de nommage :
`{story-key}-tech-lead-report.md` (s'appuyer sur le modèle officiel [`../TECH-LEAD-REPORT-TEMPLATE.md`](../TECH-LEAD-REPORT-TEMPLATE.md)).

Chaque document **doit obligatoirement comporter les 3 sections suivantes** :

1. **Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)** :
   - Contexte & problématique métier / technique.
   - Analyse d'impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`).
   - Exploration & chiffres clés (base de données, volumétrie des fichiers, cas limites).
   - Opportunités de factorisation (`DRY`) & tickets de dette technique créés (`sprint-status.yaml` / `epics.md`).
2. **Plan d'Implémentation** :
   - Schéma de données & migrations Alembic (`infra/migrations/versions/`).
   - Noyau hexagonal, algorithmes & workers (`packages/orcia-core/`, `apps/worker/`, `infra/scripts/maintenance/`).
   - Couche Backend FastAPI & contrats OpenAPI (`apps/api/`, `packages/api-client/`).
   - Design System (`packages/ui` / `@orcia/ui`), `i18n` (`fr`/`en`) & interface Next.js Direction C (`apps/web/`).
3. **Bilan des Modifications & Résultats (Post-Implémentation)** :
   - Tableau synthétique des fichiers développés et modifiés.
   - Résultats chiffrés, métriques & couverture de tests ($\ge 90\%$).
   - Validation des 5 couches de tests (`AD-17`) et résultat `gitnexus_detect_changes()`.

---

## 📚 Index des Rapports Tech Lead

| Date | Story | Fichier | Domaine | Résumé |
| :--- | :--- | :--- | :--- | :--- |
| **2026-10-25** | `Story 1.1` | [`1-1-amorçage-du-monorepo-hybride-coquille-ui-direction-c-7-modul-tech-lead-report.md`](./1-1-amorçage-du-monorepo-hybride-coquille-ui-direction-c-7-modul-tech-lead-report.md) | Monorepo Hybride / `@orcia/ui` Direction C / `i18n` (`fr`/`en`) / Tests 5 Couches | Initialisation du monorepo hybride (`pnpm` + `Turborepo` / Python 3.12 `.venv`), librairie Design System isolée `@orcia/ui` (coquille 3 colonnes, 7 modules), fondation `i18n` bout-en-bout (`fr` défaut, `en` supporté), SDK OpenAPI 3.1 `0-diff`, révision Alembic `0001` (`pgvector` + trigger Append-Only) et harnais de tests à 5 couches (`99.27 %` de couverture). |
| **2026-10-25** | `Story 1.2` | [`1-2-authentification-hybride-bi-mode-oidc-locale-arbre-hiérarchi-tech-lead-report.md`](./1-2-authentification-hybride-bi-mode-oidc-locale-arbre-hiérarchi-tech-lead-report.md) | Auth Bi-Mode (`OIDC` + `Argon2id/TOTP`) / Arbre `OrgUnit` & `Workspaces` Multi-Sources / 5 Permissions & `AES-256-GCM` | Migration Alembic `0002` (9 tables `UUIDv7`), authentification bi-mode JWT `15 min` + Refresh Token Redis révocable, coffre *Passthrough* `AES-256-GCM`, évaluateur matriciel `packages/orcia-core/permissions` (*Roll-up* ascendant `READ_ONLY_OBSERVER` + FinOps, isolation `CONFIDENTIAL_RESTRICTED`, héritage descendant des 5 permissions avec boîte noire `ERR_READ_SOURCE_DENIED`) et `ScopeAccessGuard`. |

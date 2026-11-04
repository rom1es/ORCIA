# 2026-11-05 — Réécriture intégrale du README.md pour un public IT sans jargon interne

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-reecriture-readme-clair-public-it-sans-jargon-interne` (`Ajustement Transverse Documentation`)
- **Auteur / Contexte** : Réécriture complète du fichier `README.md` à la racine du dépôt afin de remplacer le jargon interne de conception BMAD/ORCIA par une documentation claire, fluide et standard immédiatement compréhensible par des professionnels IT (développeurs, architectes, DevOps, chefs de projet, DSI) découvrant la plateforme pour la première fois.
- **Commits associés** : `ac515c9`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème identifié** : Le fichier `README.md` actuel (325 lignes) a été rédigé avec le vocabulaire interne de conception du projet (identifiants `AD-1`..`AD-21`, `UX-DR1`..`UX-DR16`, `FR-*`, `NFR-*`, `UJ-*`, `Direction C`, `Verrou V1..V5`, `Palier 1a / 1b / 2`, `Couche 5`, `HumanLedAnchorCard`, `ProgressiveDay0AccostageBanner`, `AssistantHarness`, `Blackboard append-only`, `run-lock.json`, `DNA DIRECTIVE -> NORME -> MECANISME`, `Passthrough vs Service Principal`, `Tie-Break`, `Rubber-stamping`, `orcia://system/bootstrap/*`, personas internes). Pour un professionnel IT externe qui découvre le dépôt, ces termes obscurcissent la compréhension de la proposition de valeur, du fonctionnement des 8 écrans de l'application et de l'architecture technique.
- **Comportement attendu** :
  1. Supprimer intégralement tous les codes, identifiants et acronymes propres à la conception interne d'ORCIA dans `README.md`.
  2. Présenter clairement ce qu'est ORCIA : une plateforme d'orchestration d'agents IA, de compétences réutilisables (*Skills*) et de processus métiers gouvernés par l'humain.
  3. Exposer les 4 problèmes concrets résolus pour les équipes IT et métiers : maîtrise humaine et traçabilité des sources (fin de l'effet « boîte noire »), organisation par espaces de travail connectés aux outils de l'entreprise (Git, Confluence, Jira, bases de données, outils MCP), distinction claire entre Assistant conversationnel, Agents, Compétences (*Skills*) et Processus, et maîtrise de la sécurité et des coûts d'utilisation des modèles IA.
  4. Décrire les 8 écrans de l'application (*Cockpit*, *Mon Assistant*, *Mes Espaces*, *Mes Agents & Compétences*, *Mes Processus*, *Centre de Contrôle & Coûts*, *Paramètres*, *Aide contextuelle*), l'architecture technique avec des termes standards de l'industrie, la structure du monorepo, le guide de démarrage rapide (incluant la création du premier compte administrateur au premier lancement et la remise à zéro via `pnpm db:reset`) et les commandes utiles au quotidien.
- **Contraintes spécifiques** : Aucune modification du code applicatif ni des documents d'architecture (`docs/planning-artifacts/`); maintien de la conformité de `lint_spine.py` (`0 findings`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus** :
  - Périmètre strictement documentaire (`README.md` et registre des rapports Tech Lead `docs/implementation-artifacts/tech-lead-reports/`). Aucun symbole Python ou TypeScript indexé dans le graphe d'appels n'est modifié.
- **Exploration & Chiffres Clés** :
  - Analyse du `README.md` existant (325 lignes) et recensement exhaustif des termes internes à proscrire afin de garantir `0` occurrence résiduelle.
  - Vérification des commandes de démarrage rapide (`pnpm db:up`, `pnpm db:migrate`, `pnpm db:seed`, `pnpm db:reset`, `./manage.sh`, ports `3100` et `8000`) pour s'assurer de leur exactitude opérationnelle.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Structuration claire et modulaire du `README.md` en 8 sections lisibles avec diagramme Mermaid standardisé, tableaux synthétiques et parcours pas-à-pas. Aucun ticket de dette technique supplémentaire requis.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Sans objet (modification documentaire uniquement, aucune migration Alembic).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Sans objet (aucune modification du noyau Python ou des workers).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Sans objet (aucune modification des routes FastAPI ni du client OpenAPI).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`) et Documentation Racine (`README.md`)
- Réécriture complète de `README.md` selon le plan suivant :
  1. **Présentation générale d'ORCIA** : Définition claire de la plateforme (orchestration d'agents IA, de compétences réutilisables et de processus métiers gouvernés par l'humain).
  2. **À quels problèmes concrets répond ORCIA ?** :
     - Sortir de l'effet « boîte noire » de l'IA (étapes de validation humaine explicites, citations vérifiables des sources) ;
     - Organiser le travail par Espaces de travail connectés au système d'information (Git, Confluence, Jira, bases de données, serveurs MCP) ;
     - Structurer clairement les usages : Assistant conversationnel, Agents spécialisés, Compétences (*Skills*) et Processus ;
     - Maîtriser la sécurité (contrôle d'accès par rôle et périmètre, chiffrement des secrets, exécution isolée) et les coûts (suivi budgétaire et quotas).
  3. **Concepts clés** : Tableau récapitulatif distinguant *Espace de travail*, *Assistant conversationnel*, *Agent*, *Compétence (Skill)* et *Processus*.
  4. **Vue d'ensemble fonctionnelle (Les 8 écrans de l'application)** : Présentation orientée utilisateur de *Cockpit*, *Mon Assistant*, *Mes Espaces*, *Mes Agents & Compétences*, *Mes Processus*, *Centre de Contrôle & Coûts*, *Paramètres* et *Aide contextuelle*.
  5. **Architecture technique** : Schéma Mermaid et tableau des briques technologiques standards (Frontend React 19 / TypeScript / Vite, API REST Python 3.12 / FastAPI, traitements asynchrones et workflows résilients aux pannes, PostgreSQL 18 avec recherche vectorielle et plein texte, Redis 7.4, stockage objet S3 SeaweedFS, exécution isolée de scripts).
  6. **Organisation du dépôt (Monorepo)** : Arborescence commentée (`apps/web`, `apps/api`, `apps/worker`, `packages/`, `infra/`, `scripts/`, `tests/`, `docs/`).
  7. **Guide de démarrage rapide (Quickstart)** : Prérequis, configuration `.env`, lancement Docker, installation Python/Node, initialisation de la base de données, accès Web (`http://localhost:3100`) et API (`http://localhost:8000/docs`), création du premier compte administrateur au premier lancement, et remise à zéro de la base (`pnpm db:reset`).
  8. **Commandes utiles au quotidien** : Gestion des services (`./manage.sh`, `pnpm dev:*`), exécution des tests, contrôle de la qualité du code et réinitialisation de l'environnement.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `README.md` | Modification (Réécriture intégrale) | Remplacement complet de l'ancien `README.md` (325 lignes de jargon interne) par une documentation claire et structurée en 7 sections (256 lignes) destinée aux professionnels IT découvrant ORCIA : proposition de valeur, réponses aux 4 problématiques concrètes, tableau comparatif Assistant / Agents / Compétences / Processus, présentation des 8 écrans de l'application, architecture technique standard (Mermaid + tableau), structure du monorepo, guide de démarrage rapide pas-à-pas (`http://localhost:3100`, création du premier compte administrateur au premier lancement, `pnpm db:reset`) et commandes utiles au quotidien. |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-05-reecriture-readme-clair-public-it-sans-jargon-interne-tech-lead-report.md` | Création | Rapport Tech Lead d'analyse et d'implémentation documentant la refonte du `README.md`. |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Ajout de l'entrée du rapport du `2026-11-05` dans l'index des rapports Tech Lead. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Vérification d'absence de jargon interne dans `README.md`** : `0` occurrence des termes internes (`AD-*`, `UX-DR*`, `FR-*`, `NFR-*`, `UJ-*`, `Direction C`, `Verrou V*`, `Palier 1/2`, `Couche 5`, personas internes, `HumanLedAnchorCard`, `ProgressiveDay0AccostageBanner`, `AssistantHarness`, `Blackboard`, `run-lock.json`, `DIRECTIVE -> NORME -> MECANISME`, `Passthrough`, `Service Principal`, `Tie-Break`, `Rubber-stamping`, `orcia://system/bootstrap/*`).
- **Qualité statique & Architecture** :
  - `lint_spine.py` : `{"ok": true, "spine": "ARCHITECTURE-SPINE.md", "total_findings": 0}`
  - Impact code applicatif : `0` fichier Python ou TypeScript modifié.

### 3.3 Validation & Procédure de Test
- **Contrôle documentaire et structurel** :
  - Vérification par expression régulière étendue de l'absence totale de jargon interne dans `README.md` (`exit code 0`).
  - Validation du linter d'architecture `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` (`0 findings`).
  - Vérification de l'exactitude de toutes les commandes Quickstart (`./manage.sh init-secrets`, `pnpm db:up`, `pnpm db:migrate`, `pnpm db:seed`, `./manage.sh start all`, `pnpm dev:api`, `pnpm dev:web`, `pnpm db:reset`) et des URLs (`http://localhost:3100`, `http://localhost:8000/docs`).

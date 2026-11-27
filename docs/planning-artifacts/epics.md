---
status: final
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - 'docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md'
  - 'docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md'
  - 'docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md'
  - 'docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md'
  - 'docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md'
  - 'docs/planning-artifacts/research/stack-review-2026-10-27.md'
  - 'docs/planning-artifacts/research/modularity-analysis-2026-10-27.md'
  - 'docs/planning-artifacts/research/technical-frontend-spa-nextjs-vs-vite-tanstack-rou-2026-10-27/report.md'
  - 'docs/planning-artifacts/sprint-change-proposal-2026-10-27.md'
  - 'docs/planning-artifacts/research/architecture-decoupling-audit-2026-10-28.md'
  - 'docs/planning-artifacts/sprint-change-proposal-2026-10-30-epic8-and-ux-rework.md'
  - 'docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/draft-ux-principes-et-architecture-2026-10-30.md'
---

# ORCIA - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for ORCIA, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

Full `FR-1..FR-36`, `NFR-*`, `AR-*`, `UX-DR*` definitions & coverage map live in [`epics/00-requirements-inventory.md`](epics/00-requirements-inventory.md).

## Epic Index

Individual epics and stories live in `docs/planning-artifacts/epics/epic-NN.md`.

| Epic | Title | File |
| :--- | :--- | :--- |
| Epic 1 | Amorçage Gouverné de l'Organisation, Onboarding Autonome d'Équipe (`TEAM_LEAD`), Catalogue Fédéré & Permission Broker connecté à Jira | [`epics/epic-01.md`](epics/epic-01.md) |
| Epic 2 | Ontologie Dynamique à 4 Niveaux, Simulation d'Impact (*What-If*) & RAG Hybride sur Graphe Tripartite (`Confluence ↔ Jira ↔ Git`) | [`epics/epic-02.md`](epics/epic-02.md) |
| Epic 3 | Cockpit "Human-Led", Agent Assistant Adaptatif, Moteur d'Orchestration Durable & Sous-Workflows Fractals (`SUB_WORKFLOW <= 3`) | [`epics/epic-03.md`](epics/epic-03.md) |
| Epic 4 | Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution (Actions Jira, Sandbox & MCP IDE) | [`epics/epic-04.md`](epics/epic-04.md) |
| Epic 5 | Centre de Notifications Temps Réel (`< 500ms`), Supervision Multi-Runs, Centre de Pilotage Unifié Multi-Niveaux des Workspaces (`/workspaces`) & Expérience Mobile Companion | [`epics/epic-05.md`](epics/epic-05.md) |
| Epic 6 | Gouvernance Exécutive, Provenance Auditable Immuable, FinOps Consolidé (LLM Internes + Télémétrie MCP/Agents Distants) & Réversibilité Humaine | [`epics/epic-06.md`](epics/epic-06.md) |
| Epic 7 | Agents & Workflows Autonomes sous Contrat, Socle d'Observabilité 12-Factor & OpenShift, Déclencheurs Événementiels Idempotents & Gouvernance Post-Hoc | [`epics/epic-07.md`](epics/epic-07.md) |
| Epic 8 | Hub de Paramétrage Post-Jour 0 (`/settings/*`), Gouvernance d'Entreprise à 6 Verbes (`RBAC/ABAC`), Routage Cognitif Abstrait (`simple/medium/complex/auto` & Effort), Studio Visuel Avancé (`Couches`, `Contrat`, `Pré-prompt`) & Wizards d'Initialisation Durables | [`epics/epic-08.md`](epics/epic-08.md) |
| Epic 9 | Coquille Ergonomique 4 Zones (Style Portals / EXEMPLE), Recherche Fédérée `⌘K` à 2 Vitesses (*Zero Layout Shift*), Compte Utilisateur (`UserSettingsModal`), Accostage Jour 0 (`Accostage 1/6`) & Aide Contextuelle Hybride (`❓`) | [`epics/epic-09.md`](epics/epic-09.md) |
| Epic 10 | `Mon Assistant` Tout-en-Un (Style EXEMPLE) — Personnalisation à 4 Niveaux (Mode A & Mode B), Routage à 3 Vitesses (`TTFT < 1,2 s`), Citations Déterministes (`[S1]/[G1]/[O1]`) & Dossiers Thématiques Collaboratifs (`📁 Dossiers`) | [`epics/epic-10.md`](epics/epic-10.md) |
| Epic 11 | Gouvernance Métier de l'Espace (`Mes Espaces` à 5 Onglets, Chaîne Causale `DIRECTIVE ➔ NORME ➔ MÉCANISME`, Compilateur `Text-to-Starlark` Palier 1b `< 2 ms`, Cycle de Vie du Glossaire `✨ À valider`, Routage des Artefacts à 4 Niveaux), Exposition & Banc de Test MCP/A2A `🔌` & Atelier `orcia-pack-builder` | [`epics/epic-11.md`](epics/epic-11.md) |
| Epic 12 | Intégration Bout-en-Bout du Portail SPA (`apps/web`) — Bascule sur le Shell 4 Zones Direction C (8 Entrées Fixes), Cockpit Épuré, `Mon Assistant` (Epic 10), `Mes Espaces` 5 Onglets & Atelier `orcia-pack-builder` (Epic 11) | [`epics/epic-12.md`](epics/epic-12.md) |
| Epic 13 | Évolutions Continues & Traçabilité des Capacités (Travaux Hors Epic Rattachés au PRD) | [`epics/epic-13.md`](epics/epic-13.md) |
| Epic 14 | ORCIA Process Studio v2 — Cartographie VSM (`ValueStreamMapSpec`), Studio Agentique Déterministe à 5 Blocs (`Control-M`), Gates Multi-Niveaux Auto-Heal (3x) & Portail HITL 4 Actions (`specs/epic-09-process-studio/`) | [`epics/epic-14.md`](epics/epic-14.md) |
| Epic 15 | Simplification Architecturale des Packs & Connecteurs (`packages/orcia-connectors`, Fusion `orcia-kernel` dans `orcia-core` & Packs 100 % Déclaratifs `packs/<domaine>/`) (`specs/epic-10-packs-simplification/`) | [`epics/epic-15.md`](epics/epic-15.md) |
| Epic 16 | Orchestration Réflexive (`Mon Assistant`, `Mes Agents` & Processus Pilotés par l'Objectif) et Articulation avec les Processus Pilotés par les Jalons (`specs/epic-16-reflexive-agent-harness/`, `CAP-160`) | [`epics/epic-16.md`](epics/epic-16.md) |
| Epic 17 | Refonte de la Gouvernance IAM par Délégation Hiérarchique, Organigramme en Modales, Annuaire des Comptes & `Mon Compte`, Connecteurs Socle vs Sources `Passthrough` et Coquille `@orcia/ui` | [`epics/epic-17.md`](epics/epic-17.md) |
| Epic 18 | Refonte Multi-Nature des Sources d'Espace (`/workspaces/$wsId/sources`), Moteur de Fraîcheur Différentiel (`SHA-256` & Sonde `24h`), Contrat d'Outils Normalisé `codegraph-mcp` & Service Souverain `GitNexus` | [`epics/epic-18.md`](epics/epic-18.md) |
| Epic 19 | Hub Modèles IA Fiable, Découverte 0 Token, Test Réel & Embeddings Sémantiques (AD-24) | [`epics/epic-19.md`](epics/epic-19.md) |
| Epic 20 | Gouvernance Déléguée (« Mon Organisation » & Audit Scopé), Glossaire PG18 & Rôle `ONTOLOGY_LEAD`, Consolidation « Mon Compte » (Style ChatGPT) et Page « Profil » | [`epics/epic-20.md`](epics/epic-20.md) |
| Epic 21 | Couverture Intégrale par User Journeys (UJ-1..UJ-20), Campagne End-to-End avec Vérité PostgreSQL 18, Captures d'État Final, Audit Croisé UX/Architecture & Préparation de l'Epic 22 | [`epics/epic-21.md`](epics/epic-21.md) |
| Epic 22 | Remédiation E2E Vérité PostgreSQL 18, Portails & Shell Direction C, Purge Jargon, Gardes CI, Assainissement Fail-Closed, Campagne Intégrale & Initialisation Epic 23 (`Stories 22.1`..`22.10` + `22.8a`) | [`epics/epic-22.md`](epics/epic-22.md) |
| Epic 23 | Déblocage Reset PG18/Redis, Transport SSE Authentifié, Zone 4 & Accostage `X/6`, Sobriété Direction C, Durcissement Anti-Goodhart, Campagne Desktop `52/52` & Clôture Conditionnelle | [`epics/epic-23.md`](epics/epic-23.md) |
| Epic 24 | Remédiation Finale `Case B` post-`23.7` — Persistance PG18 (Jira Staged, MCP, VSM v2), Triggers UUIDv7, Refonte CSS Tailwind v4, Navigation Zone 4, Zéro Jargon, Correctifs Utilisateur (`USER24-BUG-1..6`) & Preuve Desktop `52/52` | [`epics/epic-24.md`](epics/epic-24.md) |
| Epic 25 | Sobriété Cockpit Jour 0, Coquille 9 Entrées (Mon Organisation & Administration), Espace Personnel Automatique PG18, Hub Modèles IA Fiable & Découplage Mon Assistant / RAG (AD-24) | [`epics/epic-25.md`](epics/epic-25.md) |
| Epic 26 | Unified, Governed & Persistent "Mon Assistant" Harness — Single Turn Engine, Governed Tool Loop, Real Context, Scope Security & Zero RAM State (AD-3, AD-15, AD-19, AD-24, proposed AD-25) | [`epics/epic-26.md`](epics/epic-26.md) |
| Epic 27 | English-Only Development & Documentation Governance, 100% Bilingual FR/EN Web Application & Deterministic i18n Controls (`AD-17`, `AD-19`, RFC 9457) | [`epics/epic-27.md`](epics/epic-27.md) |
| Epic 28 | Unified "Mes Espaces" (`/workspaces`) 5-Tab Screen, Component De-Duplication & Direction C Sobriety (`Stories 28.1`..`28.4`) | [`epics/epic-28.md`](epics/epic-28.md) |
| Epic 29 | Canonical Page Headers (`<OrciaPageHeader />`), Multi-Workspace Scope & `CONFIDENTIAL_RESTRICTED` Hardening, Visual Grammar & Cross-Screen Consistency (`Stories 29.1`..`29.7`) | [`epics/epic-29.md`](epics/epic-29.md) |
| Epic 30 | Honest Save Semantics, Clean Conversational Prompts, Real PG18 Process Runs & Focus Review, and Agent Lifecycle Hardening (`Stories 30.1`..`30.6`) | [`epics/epic-30.md`](epics/epic-30.md) |
| Epic 31 | Declarative APM-Compatible Business Packs, Unified Workspace Activation, Qualified Namespacing & Pack Composer (`Stories 31.1`..`31.7`) | [`epics/epic-31.md`](epics/epic-31.md) |
| Epic 32 | Test Pyramid Pruning, Token Economy & Anti-Bloat Tech Debt (`Stories 32.1`..`32.5`) | [`epics/epic-32.md`](epics/epic-32.md) |

import type { OrciaShowcaseArchitectureLabels } from "@orcia/ui";
import type { SupportedWebLocale } from "../i18n/types";

export const SHOWCASE_ARCHITECTURE_LABELS_BY_LOCALE: Record<
  SupportedWebLocale,
  OrciaShowcaseArchitectureLabels
> = {
  fr: {
    modularMonolithTitle:
      "3.1 Monolithe Modulaire Hybride (TypeScript / Python 3.12+) & Isolation Hexagonale",
    modularMonolithSubtitle:
      "Graphe acyclique de packages vérifié par lint-imports (5 contrats) et lint_spine.py contre le référentiel d'architecture.",
    frontendBoundaryCard: {
      title: "Frontière Frontend SPA Pure (pnpm 10.6 + Turborepo 2.4)",
      description:
        "Application SPA Vite 6.4 + TanStack Router 1.166 (React 19.1, Tailwind CSS 4.3) découpée en 8 modules feature isolés, consommant exclusivement la librairie Design System @orcia/ui et le SDK OpenAPI 3.1 généré (0-diff).",
    },
    backendCoreCard: {
      title: "Noyau Python 3.12+ Hexagonal (uv 0.13.5 Workspace)",
      description:
        "Flux strictement unidirectionnel orcia-kernel ← orcia-core (8 domaines sans cycle, zéro import fastapi / sqlalchemy / dbos / dramatiq / redis / litellm / docling / wasmtime dans domain/ et ports/) ← FastAPI (Pydantic v2, RFC 9457) & worker.",
    },
    humanLedImplTitle: "3.2 Implémentation Technique des Garanties « Human-Led »",
    humanLedImplSubtitle:
      "Comment FastAPI, PostgreSQL 18 et Redis 7.4 verrouillent matériellement l'autorité humaine.",
    humanAnchorImplCard: {
      title: "Signatures SHA-256 dans human_anchor_signatures",
      description:
        "Rejet matériel (statut 422) sur toute écriture provenant d'une identité d'agent ciblant un champ à ancrage humain obligatoire, y compris sur le serveur MCP entrant GovernedMcpServerService (/api/v1/mcp).",
    },
    adaptiveGateImplCard: {
      title: "AdaptiveHumanGateService & Garde Anti-Validation Hâtive < 15 s",
      description:
        "Table chunk_approvals bloquant la transition tant qu'un tronçon reste en attente et garde temporel rejetant les validations d'artefacts > 1 000 mots soumises en moins de 15 secondes.",
    },
    redisLocksImplCard: {
      title: "Verrous Atomiques Redis 7.4 & Baux ResourceLeaseService",
      description:
        "Prise en charge d'équipe par verrou Redis atomique relayé en SSE (< 500 ms), baux PostgreSQL resource_leases avec jetons de fencing monotones transmis à ConnectorPort.invoke, et RunAccessGuard rejetant le mode observateur (statut 403).",
    },
    externalRebaseImplCard: {
      title: "ExternalEditRebaser & Actions Préparées Staged",
      description:
        "Diff structurel Markdown/AST marquant les modifications humaines faites hors plateforme comme inviolables par l'agent aval, actions externes préparées dans draft_artifact_jsonb signées par run-lock.json, et verrou contre l'écriture SI directe.",
    },
    deterministicImplTitle:
      "3.3 Implémentation des Mécanismes Déterministes (Zéro Hallucination, Reproductibilité & Sandboxes)",
    deterministicImplSubtitle:
      "Validation statique DAG, run-lock.json sur SeaweedFS CAS, Wasmtime Palier 1a, Starlark + RE2 O(n) Palier 1b, gVisor Palier 2 et vérificateur de citations < 5 ms.",
    workflowValidatorCard: {
      title: "WorkflowYamlValidator & RunLockService (SeaweedFS 4.17 CAS)",
      description:
        "Détection statique des cycles DAG, profondeur des sous-workflows <= 3 et ancres obligatoires. Épinglage SHA-256 immuable de chaque source et sous-workflow dans run_lock_jsonb et cas/<sha256>.",
    },
    tier1aSandboxCard: {
      title: "Sandbox Palier 1a (Wasmtime / SubprocessTier1SandboxAdapter)",
      description:
        "Exécution isolée < 5 000 ms, 256 MB RAM, zéro réseau pour les validateurs structurels universels : JSON Schema, contrat Markdown, axiomes et détection de Pattern Drift.",
    },
    tier1bStarlarkCard: {
      title: "Compilateur Text-to-Starlark & Sandbox Palier 1b (StarlarkMechanismSandbox)",
      description:
        "Exécution < 2 ms (0 € LLM au Run-Time) de règles métiers Starlark adossées à google-re2 garantissant une complexité linéaire O(n) anti-ReDoS pour la chaîne causale DIRECTIVE ➔ NORME ➔ MÉCANISME, avec auto-tests déterministes.",
    },
    tier2SandboxCard: {
      title: "Sandbox Palier 2 (BimodalSandboxAdapter) & Vérificateur de Citations < 5 ms",
      description:
        "Conteneur isolé gVisor/Rootless < 60 s (--network=none, snapshot CAS lecture seule) exécutant pytest, vitest, ruff, mypy, tsc. En sortie de stream, AssistantCitationAndV5GuardService vérifie en < 5 ms chaque citation [S1], [G1], [O1].",
    },
    probabilisticImplTitle:
      "3.4 Implémentation des Mécanismes Probabilistes Gouvernés (Orthogonalité des Modèles, RAG Hybride & Replay Ciblé)",
    probabilisticImplSubtitle:
      "Juge orthogonal multi-familles à 5 lentilles, recherche hybride PostgreSQL 18 + pgvector halfvec(1024) + RRF (k=60) et orchestration durable DBOS Transact 2.14.",
    agenticGateCard: {
      title: "AgenticGateService & CognitiveRouterService",
      description:
        "Impose evaluator_model_family != executor_model_family à l'intérieur du niveau de souveraineté (C0..C3), purge la chaîne de pensée (CoT) de l'exécuteur et exécute en parallèle les 5 lentilles d'audit (dont fact_verification).",
    },
    hybridRagCard: {
      title: "RAG Hybride PostgreSQL 18 + pgvector 0.8.7 + RRF (k=60)",
      description:
        "Ingestion documentaire via Docling sur workers Dramatiq, vecteurs halfvec(1024) indexés HNSW combinés à la recherche plein texte tsvector (ts_rank_cd) par Reciprocal Rank Fusion RRF (k=60), Graphe Tripartite (WITH RECURSIVE depth <= 2) et détection auditDocVsCode.",
    },
    dbosReplayCard: {
      title: "DBOS Transact 2.14 & UpstreamChallengeAndReplayService",
      description:
        "Orchestration durable sur PostgreSQL 18 via SQLAlchemy 2.1 Asyncio, table append-only blackboard_snapshots protégée par trigger de non-mutation, calcul d'impact DAG via input_uris et fork ciblé à l'étape N avec 0 token amont consommé.",
    },
    securityDsTitle: "3.5 Sécurité, Cryptographie & Design System @orcia/ui",
    securityDsSubtitle:
      "Authentification bi-mode, chiffrement par enveloppe DEK/KEK, scrubbing PII réversible et isolation en 3 couches du Design System.",
    authVaultCard: {
      title: "OIDC PKCE + Argon2id / TOTP & Enveloppe DEK/KEK",
      description:
        "Protection anti-prise de contrôle initiale par verrou SQL exclusif sur users, coffre EnvelopeVaultSecretProvider (DEK/KEK par Workspace, SecretRef non-sérialisable), PiiReversibleScrubber sous TTL Redis, et neutralisation anti-gestionnaire de mots de passe hors /login.",
    },
    threeLayerDsCard: {
      title: "Séparation 3 Couches : @orcia/ui (tokens.css) / i18n / @orcia/api-client",
      description:
        "100 % des variables CSS sémantiques et classes .orcia-ds-* résident dans tokens.css. @orcia/ui ne contient aucun appel réseau ni dépendance de routage, les textes FR/EN sont typés de bout en bout, et le contrat OpenAPI 3.1 est vérifié à 0-diff.",
    },
  },
  en: {
    modularMonolithTitle:
      "3.1 Hybrid Modular Monolith (TypeScript / Python 3.12+) & Hexagonal Isolation",
    modularMonolithSubtitle:
      "Acyclic package graph verified by lint-imports (5 contracts) and lint_spine.py against the architecture spine.",
    frontendBoundaryCard: {
      title: "Pure SPA Frontend Boundary (pnpm 10.6 + Turborepo 2.4)",
      description:
        "Pure SPA built with Vite 6.4 + TanStack Router 1.166 (React 19.1, Tailwind CSS 4.3) sliced into 8 isolated feature modules, consuming exclusively the isolated @orcia/ui Design System and the OpenAPI 3.1 @orcia/api-client SDK (0-diff).",
    },
    backendCoreCard: {
      title: "Hexagonal Python 3.12+ Core (uv 0.13.5 Workspace)",
      description:
        "Strictly unidirectional flow orcia-kernel ← orcia-core (8 acyclic domains, zero fastapi / sqlalchemy / dbos / dramatiq / redis / litellm / docling / wasmtime imports in domain/ and ports/) ← FastAPI (Pydantic v2 schemas, RFC 9457) & worker.",
    },
    humanLedImplTitle: "3.2 Technical Implementation of 'Human-Led' Guarantees",
    humanLedImplSubtitle:
      "How FastAPI, PostgreSQL 18, and Redis 7.4 materially enforce human authority.",
    humanAnchorImplCard: {
      title: "SHA-256 Signatures in human_anchor_signatures",
      description:
        "Material rejection (status 422) on any agent-initiated write targeting a mandatory human-authored field, including through GovernedMcpServerService (/api/v1/mcp).",
    },
    adaptiveGateImplCard: {
      title: "AdaptiveHumanGateService & < 15 s Anti-Hasty-Approval Guard",
      description:
        "chunk_approvals table blocking transition while any chunk remains unapproved and time guard rejecting approvals of > 1,000-word artifacts submitted in under 15 seconds.",
    },
    redisLocksImplCard: {
      title: "Atomic Redis 7.4 Locks & ResourceLeaseService Leases",
      description:
        "Team claim via atomic Redis lock broadcast over SSE (< 500 ms), PostgreSQL resource_leases with monotonic fencing tokens passed to ConnectorPort.invoke, and RunAccessGuard rejecting read-only observer writes (status 403).",
    },
    externalRebaseImplCard: {
      title: "ExternalEditRebaser & Staged Actions",
      description:
        "Structural Markdown/AST diff marking external human edits as inviolable by downstream agents, staged actions in draft_artifact_jsonb signed with run-lock.json, and direct external write guard.",
    },
    deterministicImplTitle:
      "3.3 Deterministic Mechanisms Implementation (Zero Hallucination, Reproducibility & Sandboxes)",
    deterministicImplSubtitle:
      "Static DAG validation, run-lock.json on SeaweedFS CAS, Tier 1a Wasmtime, Tier 1b Starlark + RE2 O(n), Tier 2 gVisor, and < 5 ms citation verifier.",
    workflowValidatorCard: {
      title: "WorkflowYamlValidator & RunLockService (SeaweedFS 4.17 CAS)",
      description:
        "Static detection of DAG cycles, sub-workflow depth <= 3, and required anchors. Immutable SHA-256 pinning of every source and sub-workflow in run_lock_jsonb and cas/<sha256>.",
    },
    tier1aSandboxCard: {
      title: "Tier 1a Sandbox (Wasmtime / SubprocessTier1SandboxAdapter)",
      description:
        "Isolated < 5,000 ms, 256 MB RAM, zero-network execution for universal structural validators: JSON Schema, Markdown contract, axioms, and Pattern Drift detection.",
    },
    tier1bStarlarkCard: {
      title: "Text-to-Starlark Compiler & Tier 1b Sandbox (StarlarkMechanismSandbox)",
      description:
        "< 2 ms ($0 runtime LLM cost) execution of Starlark business rules backed by google-re2 guaranteeing linear O(n) anti-ReDoS complexity for the DIRECTIVE ➔ NORM ➔ MECHANISM causal chain, with deterministic self-tests.",
    },
    tier2SandboxCard: {
      title: "Tier 2 Sandbox (BimodalSandboxAdapter) & < 5 ms Citation Verifier",
      description:
        "Isolated gVisor/Rootless < 60 s container (--network=none, read-only CAS snapshot) running pytest, vitest, ruff, mypy, tsc. Post-stream, AssistantCitationAndV5GuardService verifies every [S1], [G1], [O1] citation in < 5 ms.",
    },
    probabilisticImplTitle:
      "3.4 Governed Probabilistic Mechanisms (Model Orthogonality, Hybrid RAG & Targeted Replay)",
    probabilisticImplSubtitle:
      "Cross-family 5-lens orthogonal judge, PostgreSQL 18 + pgvector halfvec(1024) + RRF (k=60) hybrid search, and DBOS Transact 2.14 durable orchestration.",
    agenticGateCard: {
      title: "AgenticGateService & CognitiveRouterService",
      description:
        "Enforces evaluator_model_family != executor_model_family within the SovereigntyTier (C0..C3), purges executor Chain-of-Thought (CoT), and runs the 5 audit lenses in parallel (including fact_verification).",
    },
    hybridRagCard: {
      title: "Hybrid RAG PostgreSQL 18 + pgvector 0.8.7 + RRF (k=60)",
      description:
        "Document ingestion via Docling on Dramatiq workers, HNSW-indexed halfvec(1024) vectors combined with tsvector (ts_rank_cd) full-text search via Reciprocal Rank Fusion RRF (k=60), Tripartite Graph (WITH RECURSIVE depth <= 2), and auditDocVsCode.",
    },
    dbosReplayCard: {
      title: "DBOS Transact 2.14 & UpstreamChallengeAndReplayService",
      description:
        "Durable orchestration on PostgreSQL 18 via SQLAlchemy 2.1 Asyncio, append-only blackboard_snapshots table protected by immutability trigger, DAG impact calculation via input_uris, and targeted fork at Step N with 0 upstream tokens consumed.",
    },
    securityDsTitle: "3.5 Security, Cryptography & @orcia/ui Design System",
    securityDsSubtitle:
      "Bi-mode authentication, DEK/KEK envelope encryption, reversible PII scrubbing, and 3-layer Design System isolation.",
    authVaultCard: {
      title: "OIDC PKCE + Argon2id / TOTP & DEK/KEK Envelope",
      description:
        "Anti-First-User Takeover protection via exclusive SQL table lock on users, EnvelopeVaultSecretProvider vault (per-Workspace DEK/KEK, non-serializable SecretRef), Redis-TTL PiiReversibleScrubber, and password-manager protection outside /login.",
    },
    threeLayerDsCard: {
      title: "3-Layer Separation: @orcia/ui (tokens.css) / i18n / @orcia/api-client",
      description:
        "100% of semantic CSS variables and .orcia-ds-* classes live in tokens.css. @orcia/ui has zero network or router dependencies, FR/EN dictionaries are strictly typed end-to-end, and the OpenAPI 3.1 contract is verified at 0-diff.",
    },
  },
};

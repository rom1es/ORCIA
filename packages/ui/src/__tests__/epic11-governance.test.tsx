import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  DnaStarlarkCompilerAndGlossaryLifecycleView,
  type DnaStarlarkAndGlossaryLabels,
} from "../primitives/DnaStarlarkCompilerAndGlossaryLifecycleView";
import {
  PackBuilderProcessesStudioView,
  type PackBuilderProcessesStudioLabels,
} from "../primitives/PackBuilderProcessesStudioView";
import {
  RemoteServiceTestBenchAndMcpExposureView,
  type RemoteServiceTestBenchLabels,
} from "../primitives/RemoteServiceTestBenchAndMcpExposureView";
import {
  WorkspaceFiveTabsAndExternalRebaseView,
  type WorkspaceFiveTabsLabels,
} from "../primitives/WorkspaceFiveTabsAndExternalRebaseView";

const LABELS_FR: WorkspaceFiveTabsLabels = {
  heading: "Mes Espaces — Gouvernance & Livrables",
  tabOverview: "Vue d'ensemble",
  tabDocumentsSources: "Documents & Sources",
  tabDeliverablesArtifacts: "Livrables & Artefacts produits",
  tabGlossaryRules: "Glossaire & Règles métiers",
  tabMembersTeam: "Membres & Équipe",
  defaultDestinationTitle: "Destination par défaut",
  roleReferenceBadge: "Référence métier",
  roleActiveBadge: "Périmètre de travail actif",
  modeReadOnlyBadge: "Lecture seule",
  modeReadWriteBadge: "Lecture + Écriture cible",
  waiverSectionTitle: "Dérogations d'exception (Verrou V1)",
  inviolableEnterpriseLockNotice:
    "Les directives 1_ENTERPRISE inviolables ne peuvent pas être dérogées localement par un TEAM_LEAD.",
  externalRebaseTitle: "Rebase externe Git/Confluence (Verrou V2)",
  humanAmendedBadge: "🔒 HUMAN_AMENDED_EXTERNAL",
  supersededMemlogNotice: "[SUPERSEDED_BY_HUMAN_COMMIT]",
  registerWaiverCta: "Acquitter l'écart",
};

const DNA_LABELS_FR: DnaStarlarkAndGlossaryLabels = {
  heading: "Chaîne Causale ADN & Glossaire (Verrou V4)",
  generateStarlarkCta: "⚡ Générer le Mécanisme de Gate (Starlark)",
  signAndActivateCta: "✍️ Signer & Activer la Gate",
  runtimeZeroTokenBadge: "< 2 ms · 0 token LLM",
  queueSectionTitle: "✨ À valider",
  inFlowBriefingTitle: "Promotion In-Flow (Top-3 >= 0.85)",
  promoteInFlowCheckboxLabel: "Promouvoir au Glossaire de l'Espace",
  promoteSelectedCta: "Promouvoir la sélection",
  rejectCandidateCta: "Écarter",
};

const TEST_BENCH_LABELS_FR: RemoteServiceTestBenchLabels = {
  heading: "Banc de Test à Chaud & Découverte (🔌)",
  testAndDiscoverCta: "🔌 Tester la connexion & Découvrir les capacités",
  activateConnectorCta: "Activer le service",
  testWithPersonalTokenCta: "Tester avec mon jeton personnel",
  mcpExposureHeading: "Serveur MCP Gouverné (/api/v1/mcp)",
  exposeMcpToggleLabel: "🔌 Exposer en MCP",
  mcpIdeBadge: "💻 Appelé via MCP (IDE)",
  ipProtectionNotice: "execute != read : protection du system_prompt et des SecretRef.",
};

describe("Story 11.1 — WorkspaceFiveTabsAndExternalRebaseView", () => {
  it("renders the 5 workspace sub-tabs, sources, DNA waivers, and HUMAN_AMENDED_EXTERNAL lock", () => {
    const onSelectTab = vi.fn();
    const onRegisterWaiver = vi.fn();

    render(
      <WorkspaceFiveTabsAndExternalRebaseView
        workspaceSlug="claims-core"
        activeTab="DOCUMENTS_SOURCES"
        defaultArtifactDestinationUri="git://github.com/orcia/claims-core/docs/specs"
        pendingGlossaryCandidatesCount={4}
        sources={[
          {
            sourceId: "src-1",
            uri: "confluence://SPACE/RGPD-2026",
            title: "Référentiel RGPD",
            authorityRole: "REFERENCE",
            accessMode: "READ_ONLY",
            freshnessStatus: "STALE_WARNING",
          },
        ]}
        activeWaivers={[
          {
            waiverId: "waiver-1",
            sourceUri: "confluence://SPACE/OLD-DOC",
            conflictRuleId: "RULE_STALE_CONFLUENCE",
            normLevel: "3_WORKSPACE",
            hasInviolableEnterpriseDirective: false,
            status: "ACTIVE",
            reason: "En attente de refonte sprint 12",
          },
        ]}
        rebasedChunks={[
          {
            chunkKey: "sec-architecture",
            sectionTitle: "2. Architecture Cible",
            status: "HUMAN_AMENDED_EXTERNAL",
            lockedAgainstAgentOverwrite: true,
          },
        ]}
        labels={LABELS_FR}
        onSelectTab={onSelectTab}
        onRegisterWaiver={onRegisterWaiver}
      />
    );

    expect(screen.getByTestId("workspace-tab-OVERVIEW")).toBeDefined();
    expect(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES")).toBeDefined();
    expect(
      screen.getByTestId("workspace-tab-DELIVERABLES_ARTIFACTS") // pragma: allowlist secret
    ).toBeDefined();
    expect(screen.getByTestId("workspace-tab-GLOSSARY_RULES")).toBeDefined();
    expect(screen.getByTestId("workspace-tab-MEMBERS_TEAM")).toBeDefined();
    expect(screen.getByTestId("workspace-tab-badge-GLOSSARY_RULES").textContent).toBe("4");
    expect(screen.getByTestId("human-amended-badge-sec-architecture").textContent).toContain(
      "HUMAN_AMENDED_EXTERNAL" // pragma: allowlist secret
    );

    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    expect(onSelectTab).toHaveBeenCalledWith("GLOSSARY_RULES");

    fireEvent.click(screen.getByTestId("register-waiver-btn-src-1"));
    expect(onRegisterWaiver).toHaveBeenCalledWith(
      "confluence://SPACE/RGPD-2026",
      "RULE_FRESHNESS_DRIFT"
    );
  });
});

describe("Story 11.2 — DnaStarlarkCompilerAndGlossaryLifecycleView", () => {
  it("renders causal DNA breadcrumb, Starlark self-test badge, and Top-3 In-Flow promotion", () => {
    const onPromoteInFlow = vi.fn();
    render(
      <DnaStarlarkCompilerAndGlossaryLifecycleView
        mechanism={{
          mechanismId: "mech-1",
          ruleId: "RULE_IBAN_MASK",
          scriptName: "rule-iban-mask.star",
          starlarkCode: "def evaluate(doc):\n    pass",
          sha256: "sha256_mechanism_01",
          explanationFr: "Vérifie le masquage IBAN.",
          verifiedBadgeFr: "✓ Vérifié sur cas de test (PASS/FAIL en < 5 ms)",
          causalBreadcrumb:
            "🛡️ [RGPD Art.32] ➔ 📏 [Masquage IBAN] ➔ ⚙️ Vérifié par : rule-iban-mask.star",
          selfCorrected: false,
          signedAndActive: true,
        }}
        pendingQueueCandidates={[
          {
            candidateId: "cand-1",
            canonicalTerm: "Franchise Contractuelle",
            definitionFr: "Montant restant à la charge de l'assuré.",
            confidenceScore: 0.94,
            ontologyConflictWarning: null,
            preCheckedForInFlowPromotion: true,
          },
        ]}
        top3PrecheckedCandidates={[
          {
            candidateId: "cand-1",
            canonicalTerm: "Franchise Contractuelle",
            definitionFr: "Montant restant à la charge de l'assuré.",
            confidenceScore: 0.94,
            ontologyConflictWarning: null,
            preCheckedForInFlowPromotion: true,
          },
        ]}
        labels={DNA_LABELS_FR}
        onPromoteInFlow={onPromoteInFlow}
      />
    );

    expect(screen.getByTestId("dna-causal-breadcrumb").textContent).toContain(
      "rule-iban-mask.star"
    );
    expect(screen.getByTestId("starlark-verified-badge").textContent).toContain(
      "PASS/FAIL en < 5 ms"
    );
    fireEvent.click(screen.getByTestId("promote-in-flow-btn"));
    expect(onPromoteInFlow).toHaveBeenCalledWith(["cand-1"]);
  });
});

describe("Story 11.3 — RemoteServiceTestBenchAndMcpExposureView", () => {
  it("renders the 4 test bench steps, non-blocking Passthrough status, and MCP exposure", () => {
    const onActivate = vi.fn();
    render(
      <RemoteServiceTestBenchAndMcpExposureView
        endpointUrl="https://mcp.orcia.io/sse"
        steps={[
          {
            stepNumber: 1,
            stepCode: "1_NETWORK_TLS_ANTI_SSRF",
            status: "PASS",
            detailFr: "Anti-SSRF validé",
          },
          {
            stepNumber: 2,
            stepCode: "2_AUTHENTICATION",
            status: "WAITING_USER_PASSTHROUGH_TOKEN", // pragma: allowlist secret
            detailFr: "🟠 En attente de jeton utilisateur (Passthrough)",
          },
          {
            stepNumber: 3,
            stepCode: "3_CONTRACT_DISCOVERY",
            status: "PASS",
            detailFr: "2 outils découverts",
          },
          {
            stepNumber: 4,
            stepCode: "4_HOT_DRY_RUN",
            status: "SKIPPED",
            detailFr: "Différé Passthrough",
          },
        ]}
        discoveredCapabilities={[
          {
            toolName: "search_docs",
            qualification: "READ_ONLY",
            badgeFr: "👁️ Lecture seule",
          },
          {
            toolName: "create_issue",
            qualification: "WRITE_STAGED_REQUIRED", // pragma: allowlist secret
            badgeFr: "✍️ Écriture -> Action Staged obligatoire (AD-3)",
          },
        ]}
        canActivate={true}
        mcpExposed={true}
        exposedToolNames={["assistant.ask", "agent.claims-triage"]}
        labels={TEST_BENCH_LABELS_FR}
        onActivateService={onActivate}
      />
    );

    expect(screen.getByTestId("test-bench-status-2").textContent).toBe(
      "WAITING_USER_PASSTHROUGH_TOKEN" // pragma: allowlist secret
    );
    const activateBtn = screen.getByTestId("activate-remote-service-btn") as HTMLButtonElement;
    expect(activateBtn.disabled).toBe(false);
    fireEvent.click(activateBtn);
    expect(onActivate).toHaveBeenCalled();
  });
});

const PACK_BUILDER_LABELS_FR: PackBuilderProcessesStudioLabels = {
  studioTitle: "Atelier Système orcia-pack-builder (Processus 1 à 4)",
  agentsSectionTitle: "4 Agents Spécialisés",
  humanAnchorSectionTitle: "✍️ Ancrage Humain Violet — Intention Métier du Pack (>= 30 caractères)",
  humanAnchorPlaceholder: "Décrivez l'intention métier et réglementaire du Pack...",
  process1CreatePackButtonLabel: "Générer le Pack Métier (Processus 1)",
  process2WhatIfTitle: "Processus 2 — Simulation d'Impact What-If (@vX.Y.Z)",
  runLocksPreservedBadgeLabel: "✓ run-lock.json intacts",
  process3CertifyTitle: "Processus 3 — Certification Starlark Palier 1b (< 2 ms) & Palier 2",
  certifiedBadgeLabel: "✓ Certifié",
  process4PromoteButtonLabel: "Promouvoir une brique depuis un Espace (Processus 4)",
};

describe("Story 11.4 — PackBuilderProcessesStudioView", () => {
  it("enforces Violet Human Anchor (>= 30 chars) and renders What-If & Starlark certifications", () => {
    const onCreate = vi.fn();
    render(
      <PackBuilderProcessesStudioView
        agents={[
          {
            slug: "architecte-metier-pack",
            handle: "@Architecte-Métier-Pack",
            roleDescription: "Structuration ADN",
          },
        ]}
        whatIfImpacts={[
          {
            workspaceKey: "claims-fr-ws",
            impactedWorkflows: ["claims/triage-flow"],
            breakingNorms: ["NORM-FIN-01"],
            activeRunsCount: 3,
            runLocksUntouched: true,
          },
        ]}
        certifications={[
          {
            toolSlug: "mech-fin-solvency",
            sandboxTier: "TIER_1B_STARLARK", // pragma: allowlist secret
            certified: true,
            elapsedMs: 0.42,
            certificateSha256: "abc123",
          },
        ]}
        labels={PACK_BUILDER_LABELS_FR}
        onCreateBusinessPack={onCreate}
      />
    );

    const createBtn = screen.getByTestId("process1-create-pack-btn") as HTMLButtonElement;
    expect(createBtn.disabled).toBe(true);

    fireEvent.change(screen.getByTestId("pack-builder-anchor-input"), {
      target: {
        value:
          "Intention métier Solvabilité II : garantir le contrôle déterministe des provisions techniques.",
      },
    });
    expect(createBtn.disabled).toBe(false);
    fireEvent.click(createBtn);
    expect(onCreate).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("run-locks-preserved-claims-fr-ws").textContent).toBe(
      "✓ run-lock.json intacts"
    );
  });
});

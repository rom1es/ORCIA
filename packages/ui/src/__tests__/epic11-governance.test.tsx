import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

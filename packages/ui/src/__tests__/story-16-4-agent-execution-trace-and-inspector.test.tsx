import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AgentExecutionTrace,
  SourceLineInspectorDrawer,
  type AgentExecutionTraceLabels,
  type SourceLineInspectorLabels,
  type UiAgentTraceEventItem,
} from "../index";

afterEach(() => {
  cleanup();
});

const TRACE_LABELS_FR: AgentExecutionTraceLabels = {
  heading: "Déroulement de l'investigation",
  defaultGroupTitle: "Analyse et recherche dans vos sources",
  runningStatus: "En cours d'analyse...",
  synthesizingStatus: "Synthèse en cours...",
  completedStatus: "Analyse terminée",
  pausedWriteStatus: "En attente de votre confirmation avant publication",
  cancelledStatus: "Exécution interrompue",
  failedStatus: "Interruption sur anomalie",
  stepsCountLabel: (count) => `${count} action${count > 1 ? "s" : ""}`,
  thoughtSummaryLabel: (seconds) => `Réflexion (${seconds}s)`,
  thoughtInProgressLabel: "Réflexion en cours",
  analyzedPrefix: "Analysé",
  linesRangeShort: (start, end) => `#L${start}-${end}`,
  redactedPillSuffix: "Accès requis",
  delegatedPrefix: (agentHandle) => `Délégation à ${agentHandle}`,
  synthesizeNowButtonLabel: "Synthétiser maintenant",
  synthesizeNowButtonHint: "Vous pouvez demander une conclusion immédiate avec les éléments déjà recueillis.",
  writePreviewHeading: "Confirmation requise avant action externe",
  writePreviewTargetPrefix: "Outil cible :",
  approveWriteButtonLabel: "Approuver la publication",
  rejectWriteButtonLabel: "Refuser",
  expandGroupAriaLabel: "Déplier l'étape",
  collapseGroupAriaLabel: "Replier l'étape",
};

const INSPECTOR_LABELS_FR: SourceLineInspectorLabels = {
  dialogAriaLabel: "Inspecteur d'extrait source",
  linesSliceSummary: (start, end, total) => `Lignes ${start} – ${end} sur ${total}`,
  copySliceButtonLabel: (start, end) => `Copier l'extrait #L${start}-${end}`,
  copiedSliceFeedbackLabel: "Extrait copié",
  closeButtonLabel: "Fermer",
  loadingLabel: "Chargement de l'extrait vérifié...",
  redactedTitle: "Extrait protégé (habilitation requise)",
  redactedBody:
    "Votre compte ne dispose pas de l'habilitation de lecture sur cette source. Aucune ligne du document n'est exposée.",
  redactedHintPrefix: "Demande d'accès :",
  emptySliceLabel: "Aucune ligne dans la plage demandée.",
};

const SAMPLE_EVENTS: readonly UiAgentTraceEventItem[] = [
  {
    eventId: "ev-1",
    sequence: 1,
    kind: "GROUP_HEADER",
    label: "Exploration documentaire & architecture",
    actorSlug: "assistant",
    groupKey: "grp-explore",
  },
  {
    eventId: "ev-2",
    sequence: 2,
    kind: "THOUGHT_COMPLETED",
    label: "Réflexion initiale",
    actorSlug: "assistant",
    durationSeconds: 3,
    thoughtContent: "Ligne 1 du raisonnement\nLigne 2 conservée intégralement",
  },
  {
    eventId: "ev-3",
    sequence: 3,
    kind: "CHECK_EXECUTED",
    label: "Recherche de termes clés dans le registre produit",
    actorSlug: "assistant",
  },
  {
    eventId: "ev-4",
    sequence: 4,
    kind: "FILE_ANALYZED",
    label: "Lecture ciblée",
    actorSlug: "assistant",
    resourceUri: "docs/product/capabilities.yaml",
    displayFilename: "capabilities.yaml",
    fileBadgeCode: "Y",
    startLine: 200,
    endLine: 350,
  },
  {
    eventId: "ev-5",
    sequence: 5,
    kind: "AGENT_DELEGATED",
    label: "Vérification de cohérence documentaire",
    actorSlug: "assistant",
    delegatedAgentSlug: "redacteur-documentation-orcia",
  },
  {
    eventId: "ev-6",
    sequence: 6,
    kind: "FILE_ANALYZED",
    label: "Lecture par le spécialiste",
    actorSlug: "redacteur-documentation-orcia",
    resourceUri: "packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml",
    displayFilename: "wf-generate-orcia-documentation.yaml",
    fileBadgeCode: "Y",
    startLine: 1,
    endLine: 35,
  },
];

describe("Story 16.4 — AgentExecutionTrace & SourceLineInspectorDrawer (@orcia/ui)", () => {
  it("renders collapsible groups, collapsed-by-default thoughts preserving newlines, specialist delegations, #L200-350 pill callback, and Synthesize Now CTA", () => {
    const onInspectLines = vi.fn();
    const onSynthesizeNow = vi.fn();
    const onApproveWrite = vi.fn();
    const onRejectWrite = vi.fn();

    render(
      <AgentExecutionTrace
        status="RUNNING"
        events={SAMPLE_EVENTS}
        labels={TRACE_LABELS_FR}
        onInspectLines={onInspectLines}
        onSynthesizeNow={onSynthesizeNow}
        onApproveWrite={onApproveWrite}
        onRejectWrite={onRejectWrite}
      />,
    );

    expect(screen.getByTestId("agent-execution-trace")).toBeInTheDocument();
    expect(screen.getByTestId("trace-status-label")).toHaveTextContent("En cours d'analyse...");
    expect(screen.getByText("Exploration documentaire & architecture")).toBeInTheDocument();

    // Thought is collapsed by default
    expect(screen.queryByTestId("trace-thought-content")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("trace-thought-toggle-btn"));
    const thoughtPre = screen.getByTestId("trace-thought-content");
    expect(thoughtPre.textContent).toBe("Ligne 1 du raisonnement\nLigne 2 conservée intégralement");

    // Specialist delegation is rendered and collapsible
    expect(screen.getByTestId("trace-delegated-agent-block")).toHaveTextContent(
      "Délégation à @redacteur-documentation-orcia",
    );
    const pills = screen.getAllByTestId("trace-file-analyzed-pill");
    expect(pills).toHaveLength(2);

    // Clicking #L200-350 pill triggers onInspectLines with exact coordinates
    fireEvent.click(pills[0]!);
    expect(onInspectLines).toHaveBeenCalledWith({
      uri: "docs/product/capabilities.yaml",
      startLine: 200,
      endLine: 350,
      filename: "capabilities.yaml",
      badgeCode: "Y",
    });

    // Clicking Synthesize Now triggers onSynthesizeNow
    fireEvent.click(screen.getByTestId("trace-synthesize-now-btn"));
    expect(onSynthesizeNow).toHaveBeenCalledTimes(1);

    // Collapsing group hides group items
    fireEvent.click(screen.getByTestId("trace-group-header-btn"));
    expect(screen.queryByTestId("trace-group-items")).not.toBeInTheDocument();
  });

  it("renders WritePreviewCard in WAITING_WRITE_PREVIEW state and triggers approve / reject callbacks", () => {
    const onApproveWrite = vi.fn();
    const onRejectWrite = vi.fn();

    render(
      <AgentExecutionTrace
        status="WAITING_WRITE_PREVIEW"
        events={SAMPLE_EVENTS}
        pendingWritePreview={{
          previewId: "prv-16-4",
          targetConnector: "confluence",
          actionSummary: "Publication de la page de synthèse d'architecture",
        }}
        labels={TRACE_LABELS_FR}
        onInspectLines={vi.fn()}
        onSynthesizeNow={vi.fn()}
        onApproveWrite={onApproveWrite}
        onRejectWrite={onRejectWrite}
      />,
    );

    expect(screen.getByTestId("trace-write-preview-card")).toBeInTheDocument();
    expect(screen.queryByTestId("trace-synthesize-now-btn")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("trace-approve-write-btn"));
    expect(onApproveWrite).toHaveBeenCalledWith("prv-16-4");

    fireEvent.click(screen.getByTestId("trace-reject-write-btn"));
    expect(onRejectWrite).toHaveBeenCalledWith("prv-16-4");
  });

  it("SourceLineInspectorDrawer renders 1-indexed highlighted lines, supports slice copy, and closes on Escape", () => {
    const onCopySlice = vi.fn();

    function Wrapper() {
      const [open, setOpen] = useState(true);
      return (
        <SourceLineInspectorDrawer
          open={open}
          onOpenChange={setOpen}
          resourceUri="docs/product/capabilities.yaml"
          displayFilename="capabilities.yaml"
          fileBadgeCode="Y"
          startLine={2}
          endLine={3}
          totalLines={120}
          lines={[
            { lineNumber: 1, content: "version: 1" },
            { lineNumber: 2, content: "capabilities:" },
            { lineNumber: 3, content: "  - id: CAP-160" },
            { lineNumber: 4, content: "    status: live" },
          ]}
          labels={INSPECTOR_LABELS_FR}
          onCopySlice={onCopySlice}
        />
      );
    }

    render(<Wrapper />);

    expect(screen.getByTestId("source-line-inspector-drawer")).toBeInTheDocument();
    expect(screen.getByTestId("inspector-file-badge")).toHaveTextContent("Y");
    expect(screen.getByTestId("inspector-slice-summary")).toHaveTextContent(
      "Lignes 2 – 3 sur 120",
    );
    expect(screen.getByTestId("inspector-code-line-1")).toHaveAttribute(
      "data-highlighted",
      "false",
    );
    expect(screen.getByTestId("inspector-code-line-2")).toHaveAttribute(
      "data-highlighted",
      "true",
    );
    expect(screen.getByTestId("inspector-code-line-3")).toHaveAttribute(
      "data-highlighted",
      "true",
    );

    fireEvent.click(screen.getByTestId("inspector-copy-slice-btn"));
    expect(onCopySlice).toHaveBeenCalledTimes(1);

    // Escape closes the Radix Dialog drawer
    fireEvent.keyDown(document, { key: "Escape", code: "Escape" });
    expect(screen.queryByTestId("source-line-inspector-drawer")).not.toBeInTheDocument();
  });

  it("SourceLineInspectorDrawer enforces zero code line exposure when redacted === true", () => {
    render(
      <SourceLineInspectorDrawer
        open={true}
        onOpenChange={vi.fn()}
        resourceUri="docs/confidential/board-notes.md"
        displayFilename="board-notes.md"
        fileBadgeCode="M↓"
        startLine={10}
        endLine={25}
        totalLines={80}
        lines={[{ lineNumber: 10, content: "SECRET_SHOULD_NEVER_BE_SHOWN" }]}
        redacted={true}
        redactedReason="READ_SOURCE_REQUIRED"
        permissionRequestHint="Demandez l'habilitation READ_SOURCE auprès du responsable de l'Espace."
        labels={INSPECTOR_LABELS_FR}
        onCopySlice={vi.fn()}
      />,
    );

    expect(screen.getByTestId("inspector-redacted-banner")).toHaveTextContent(
      "Extrait protégé (habilitation requise)",
    );
    expect(screen.getByTestId("inspector-redacted-hint")).toHaveTextContent("READ_SOURCE");
    expect(screen.queryByTestId("inspector-code-lines-list")).not.toBeInTheDocument();
    expect(screen.queryByText("SECRET_SHOULD_NEVER_BE_SHOWN")).not.toBeInTheDocument();
    expect(screen.getByTestId("inspector-copy-slice-btn")).toBeDisabled();
  });
});

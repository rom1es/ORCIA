import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AgentExecutionTrace,
  type AgentExecutionTraceLabels,
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
  synthesizeNowButtonHint: "Synthèse immédiate disponible.",
  writePreviewHeading: "Confirmation requise",
  writePreviewTargetPrefix: "Outil cible :",
  approveWriteButtonLabel: "Approuver",
  rejectWriteButtonLabel: "Refuser",
  expandGroupAriaLabel: "Déplier l'étape",
  collapseGroupAriaLabel: "Replier l'étape",
};

describe("Story 30.3 — Coalesced THOUGHT_DELTA reasoning blocks (@orcia/ui)", () => {
  it("coalesces consecutive THOUGHT_DELTA chunks into a single continuous thought block while preserving tool & phase boundaries", () => {
    const events: UiAgentTraceEventItem[] = [
      {
        eventId: "g1",
        sequence: 1,
        kind: "GROUP_HEADER",
        label: "Phase 1 : Analyse",
        actorSlug: "assistant",
        groupKey: "phase-1",
      },
      {
        eventId: "td-1",
        sequence: 2,
        kind: "THOUGHT_DELTA",
        label: "Réflexion en cours",
        actorSlug: "assistant",
        thoughtContent: "Analysons un extrait ciblé de `spec.md` (`",
      },
      {
        eventId: "td-2",
        sequence: 3,
        kind: "THOUGHT_DELTA",
        label: "Réflexion en cours",
        actorSlug: "assistant",
        thoughtContent: "#L1-35`) afin d'ancrer ",
      },
      {
        eventId: "td-3",
        sequence: 4,
        kind: "THOUGHT_DELTA",
        label: "Réflexion en cours",
        actorSlug: "assistant",
        thoughtContent: "la réponse sur les lignes exactes.",
      },
      {
        eventId: "tc-1",
        sequence: 5,
        kind: "THOUGHT_COMPLETED",
        label: "Réflexion",
        actorSlug: "assistant",
        durationSeconds: 3,
        thoughtContent: "",
      },
      {
        eventId: "file-1",
        sequence: 6,
        kind: "FILE_ANALYZED",
        label: "spec.md",
        actorSlug: "assistant",
        resourceUri: "docs/spec.md",
        displayFilename: "spec.md",
        fileBadgeCode: "M↓",
        startLine: 1,
        endLine: 35,
      },
      {
        eventId: "td-4",
        sequence: 7,
        kind: "THOUGHT_DELTA",
        label: "Réflexion en cours",
        actorSlug: "assistant",
        thoughtContent: "Vérification post-lecture ",
      },
      {
        eventId: "td-5",
        sequence: 8,
        kind: "THOUGHT_DELTA",
        label: "Réflexion en cours",
        actorSlug: "assistant",
        thoughtContent: "complétée.",
      },
    ];

    render(
      <AgentExecutionTrace
        status="RUNNING"
        events={events}
        labels={TRACE_LABELS_FR}
        onInspectLines={vi.fn()}
        onSynthesizeNow={vi.fn()}
        onApproveWrite={vi.fn()}
        onRejectWrite={vi.fn()}
      />,
    );

    const toggles = screen.getAllByTestId("trace-thought-toggle-btn");
    // Exactly 2 coalesced thought blocks (one before FILE_ANALYZED, one after) instead of 6 separate headers
    expect(toggles).toHaveLength(2);
    expect(toggles[0]).toHaveTextContent("Réflexion (3s)");
    expect(toggles[1]).toHaveTextContent("Réflexion en cours");

    fireEvent.click(toggles[0]!);
    fireEvent.click(toggles[1]!);
    const contents = screen.getAllByTestId("trace-thought-content");
    expect(contents).toHaveLength(2);
    expect(contents[0]!.textContent).toContain(
      "Analysons un extrait ciblé de spec.md (#L1-35) afin d'ancrer la réponse sur les lignes exactes.",
    );
    expect(contents[1]!.textContent).toContain("Vérification post-lecture complétée.");
  });

  it("coalesces multiple SYNTHESIS_READY answer chunks into a single trace row without duplicating labels", () => {
    const events: UiAgentTraceEventItem[] = [
      {
        eventId: "g-synth",
        sequence: 1,
        kind: "GROUP_HEADER",
        label: "Consolidation du livrable final",
        actorSlug: "assistant",
        groupKey: "phase-synth",
      },
      {
        eventId: "td-s1",
        sequence: 2,
        kind: "THOUGHT_DELTA",
        label: "Réflexion en cours",
        actorSlug: "assistant",
        thoughtContent: "Synthèse finale prête à partir des observations collectées.",
      },
      {
        eventId: "tc-s1",
        sequence: 3,
        kind: "THOUGHT_COMPLETED",
        label: "Réflexion",
        actorSlug: "assistant",
        durationSeconds: 1,
        thoughtContent: "",
      },
      ...Array.from({ length: 8 }, (_, idx) => ({
        eventId: `ans-${idx + 1}`,
        sequence: 4 + idx,
        kind: "SYNTHESIS_READY" as const,
        label: "Synthèse prête",
        actorSlug: "assistant",
      })),
    ];

    render(
      <AgentExecutionTrace
        status="COMPLETED"
        events={events}
        labels={TRACE_LABELS_FR}
        onInspectLines={vi.fn()}
        onSynthesizeNow={vi.fn()}
        onApproveWrite={vi.fn()}
        onRejectWrite={vi.fn()}
      />,
    );

    const toggles = screen.getAllByTestId("trace-thought-toggle-btn");
    expect(toggles).toHaveLength(1);
    expect(toggles[0]).toHaveTextContent("Réflexion (1s)");
    expect(screen.getAllByText("Synthèse prête")).toHaveLength(1);
    expect(screen.getByTestId("trace-steps-counter")).toHaveTextContent("2 actions");
  });
});

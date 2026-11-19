import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AssistantActiveStreamContent } from "../primitives/AssistantActiveStreamContent";

afterEach(() => {
  cleanup();
});

describe("Story 23.2 — AssistantActiveStreamContent critical 401/403 vs ai_unavailable alert banner", () => {
  it("renders a critical role='alert' banner with reconnect CTA on auth_expired without blaming the AI model", () => {
    const onReconnect = vi.fn();

    render(
      <AssistantActiveStreamContent
        previousTurnsSlot={null}
        shownUserQuestion="Résume le dossier"
        hideDuplicateCompletedStream={false}
        isGenerating={false}
        displayModelBadge="Qwen 32B"
        effortTitle="Équilibré"
        lastSubmittedFiles={[]}
        cleanStreamedText=""
        stepProgress={[]}
        initialElapsedSeconds={0}
        errorMessage="Votre session a expiré ou doit être renouvelée pour continuer la conversation."
        errorKind="auth_expired"
        reconnectCtaLabel="Se reconnecter →"
        onReconnect={onReconnect}
        isStoppedVisible={false}
        mergedRagCitations={[]}
        currentTurnFeedback={null}
        onRegenerate={vi.fn()}
      />,
    );

    const banner = screen.getByTestId("assistant-error-banner");
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.getAttribute("data-error-kind")).toBe("auth_expired");
    expect(banner.className).toContain("orcia-ds-alert-error");
    expect(banner.textContent).not.toContain("HTTP 401");
    expect(banner.textContent).not.toContain("modèle IA");

    const reconnectBtn = screen.getByTestId("assistant-error-reconnect-btn");
    expect(reconnectBtn.textContent).toBe("Se reconnecter →");
    fireEvent.click(reconnectBtn);
    expect(onReconnect).toHaveBeenCalledTimes(1);
  });

  it("renders ai_unavailable warning banner without reconnect CTA when AI service is down", () => {
    render(
      <AssistantActiveStreamContent
        previousTurnsSlot={null}
        shownUserQuestion="Résume le dossier"
        hideDuplicateCompletedStream={false}
        isGenerating={false}
        displayModelBadge="Qwen 32B"
        effortTitle="Équilibré"
        lastSubmittedFiles={[]}
        cleanStreamedText=""
        stepProgress={[]}
        initialElapsedSeconds={0}
        errorMessage="⚠️ Impossible d'obtenir une réponse de Mon Assistant (Modèle indisponible). Vérifiez que le modèle IA configuré est bien démarré."
        errorKind="ai_unavailable"
        onReconnect={vi.fn()}
        isStoppedVisible={false}
        mergedRagCitations={[]}
        currentTurnFeedback={null}
        onRegenerate={vi.fn()}
      />,
    );

    const banner = screen.getByTestId("assistant-error-banner");
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.getAttribute("data-error-kind")).toBe("ai_unavailable");
    expect(banner.textContent).toContain("modèle IA configuré");
    expect(screen.queryByTestId("assistant-error-reconnect-btn")).toBeNull();
  });
});

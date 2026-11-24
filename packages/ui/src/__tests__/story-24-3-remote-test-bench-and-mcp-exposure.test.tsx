import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  RemoteServiceTestBenchAndMcpExposureView,
  type RemoteServiceTestBenchLabels,
} from "../primitives/RemoteServiceTestBenchAndMcpExposureView";

const LABELS_FR: RemoteServiceTestBenchLabels = {
  heading: "🔌 Connexion et Test d'Outils Externes & Accès depuis un Éditeur",
  testAndDiscoverCta: "🔌 Tester la connexion et détecter les actions",
  testingInProgressCta: "⏳ Vérification en cours…",
  testingInProgressNotice:
    "⏳ Vérification en cours auprès du serveur et enregistrement dans le registre d'audit…",
  activateConnectorCta: "✓ Activer ce service dans l'Espace",
  activateDisabledReason: "Validez les 4 étapes du banc d'essai pour activer ce connecteur.",
  testWithPersonalTokenCta: "🔑 Tester avec mon compte personnel",
  mcpExposureHeading: "Accès depuis un Éditeur de Code Externe",
  exposeMcpToggleLabel:
    "Permettre l'utilisation depuis un éditeur externe (Cursor, VS Code, Claude Desktop)",
  mcpIdeBadge: "🔌 Accès éditeur sécurisé · lecture et exécution distinctes",
  ipProtectionNotice:
    "🔒 Confidentialité : Les réglages internes et règles de vérification de vos processus restent protégés.",
  stepLabels: {
    "1_NETWORK_TLS_ANTI_SSRF": "Réseau, chiffrement et protection d'adresse",
    "2_AUTHENTICATION": "Authentification et droits d'accès",
    "3_CONTRACT_DISCOVERY": "Découverte des actions exposées",
    "4_HOT_DRY_RUN": "Essai rapide à blanc",
  },
  statusLabels: {
    PASS: "Validé",
    FAIL: "Échec",
    WAITING_USER_PASSTHROUGH_TOKEN: "En attente de jeton personnel",
    SKIPPED: "Ignoré",
  },
};

const LABELS_EN: RemoteServiceTestBenchLabels = {
  heading: "🔌 Remote Tool Connection, Test Bench & Editor Access",
  testAndDiscoverCta: "🔌 Test connection and discover actions",
  testingInProgressCta: "⏳ Verification in progress…",
  testingInProgressNotice:
    "⏳ Verifying connection with remote server and recording audit trail…",
  activateConnectorCta: "✓ Enable this service in the Space",
  activateDisabledReason: "Complete the 4 test bench verification steps to enable this connector.",
  testWithPersonalTokenCta: "🔑 Test with my personal account",
  mcpExposureHeading: "External Code Editor Access",
  exposeMcpToggleLabel:
    "Allow usage from an external code editor (Cursor, VS Code, Claude Desktop)",
  mcpIdeBadge: "🔌 Secure editor access · separate read and execute permissions",
  ipProtectionNotice:
    "🔒 Confidentiality: Internal process settings and verification rules remain protected.",
  stepLabels: {
    "1_NETWORK_TLS_ANTI_SSRF": "Network, TLS & Address Guard",
    "2_AUTHENTICATION": "Authentication & Access Control",
    "3_CONTRACT_DISCOVERY": "Actions & Contract Discovery",
    "4_HOT_DRY_RUN": "Hot Dry-Run Verification",
  },
  statusLabels: {
    PASS: "Passed",
    FAIL: "Failed",
    WAITING_USER_PASSTHROUGH_TOKEN: "Waiting for personal token",
    SKIPPED: "Skipped",
  },
};

describe("Story 24.3 — RemoteServiceTestBenchAndMcpExposureView (No Optimistic PASS & i18n)", () => {
  it("displays loading banner and disables buttons when isTesting=true without optimistic PASS", () => {
    const onRun = vi.fn();
    render(
      <RemoteServiceTestBenchAndMcpExposureView
        endpointUrl="https://mcp.entreprise.interne/api"
        steps={[]}
        discoveredCapabilities={[]}
        canActivate={false}
        mcpExposed={false}
        exposedToolNames={[]}
        isTesting={true}
        labels={LABELS_FR}
        onRunTestBench={onRun}
      />,
    );

    const loadingBanner = screen.getByTestId("test-bench-loading-banner");
    expect(loadingBanner.getAttribute("role")).toBe("status");
    expect(loadingBanner.textContent).toContain("Vérification en cours");

    const runBtn = screen.getByTestId("run-test-bench-btn") as HTMLButtonElement;
    expect(runBtn.disabled).toBe(true);
    expect(runBtn.textContent).toContain("Vérification en cours");

    const activateBtn = screen.getByTestId("activate-remote-service-btn") as HTMLButtonElement;
    expect(activateBtn.disabled).toBe(true);

    expect(screen.queryByTestId("test-bench-status-1")).toBeNull();
    expect(screen.queryByText("Validé")).toBeNull();
  });

  it("renders translated FR and EN step/status labels while preserving data-status and callbacks", () => {
    const onToggle = vi.fn();
    const onActivate = vi.fn();
    const steps = [
      {
        stepNumber: 1 as const,
        stepCode: "1_NETWORK_TLS_ANTI_SSRF" as const,
        status: "PASS" as const,
        detailFr: "Réseau, TLS & Anti-SSRF validés.",
      },
      {
        stepNumber: 2 as const,
        stepCode: "2_AUTHENTICATION" as const,
        status: "WAITING_USER_PASSTHROUGH_TOKEN" as const,
        detailFr: "En attente de jeton utilisateur",
      },
    ];

    const { rerender } = render(
      <RemoteServiceTestBenchAndMcpExposureView
        endpointUrl="https://mcp.entreprise.interne/api"
        steps={steps}
        discoveredCapabilities={[
          {
            toolName: "search_documents",
            qualification: "READ_ONLY",
            badgeFr: "👁️ Lecture seule",
          },
        ]}
        canActivate={true}
        mcpExposed={false}
        isSavingMcp={false}
        exposedToolNames={["assistant.ask"]}
        labels={LABELS_FR}
        onActivateService={onActivate}
        onToggleMcpExposure={onToggle}
      />,
    );

    expect(screen.getByText(/Réseau, chiffrement et protection d'adresse/)).toBeDefined();
    expect(screen.getByText("Validé")).toBeDefined();
    expect(screen.getByText("En attente de jeton personnel")).toBeDefined();
    expect(screen.getByTestId("test-bench-status-1").getAttribute("data-status")).toBe("PASS");

    fireEvent.click(screen.getByTestId("activate-remote-service-btn"));
    expect(onActivate).toHaveBeenCalledTimes(1);

    const toggle = screen.getByTestId("toggle-mcp-exposure-checkbox") as HTMLInputElement;
    fireEvent.click(toggle);
    expect(onToggle).toHaveBeenCalledWith(true);

    rerender(
      <RemoteServiceTestBenchAndMcpExposureView
        endpointUrl="https://mcp.entreprise.interne/api"
        steps={steps}
        discoveredCapabilities={[]}
        canActivate={true}
        mcpExposed={true}
        isSavingMcp={true}
        exposedToolNames={["assistant.ask", "agent.governed-mcp-connector"]}
        labels={LABELS_EN}
        onActivateService={onActivate}
        onToggleMcpExposure={onToggle}
      />,
    );

    expect(screen.getByText(/Network, TLS & Address Guard/)).toBeDefined();
    expect(screen.getByText("Passed")).toBeDefined();
    expect(screen.getByText("Waiting for personal token")).toBeDefined();
    expect((screen.getByTestId("toggle-mcp-exposure-checkbox") as HTMLInputElement).disabled).toBe(
      true,
    );
  });
});

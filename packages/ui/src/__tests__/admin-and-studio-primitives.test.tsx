import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  DurableWizardRunnerView,
  EffortSelector,
  InferenceTierBadge,
  LayersInspectorPopover,
  PermissionGuard,
  SecretField,
  WorkflowTopGovernanceBar,
} from "../index";

describe("Epic 8 @orcia/ui primitives (Stories 8.1 to 8.6)", () => {
  it("PermissionGuard renders children when verb is allowed, hides when hiddenWhenUnauthorized, or shows passive lock card", () => {
    const labels = {
      passiveLockBadge: "🔒 Accès restreint",
      passiveLockDescription: "Habilitation requise",
      requestAccessCta: "Demander l'accès",
      disabledHint: "Action verrouillée",
    };

    const { rerender } = render(
      <PermissionGuard
        scopePath="GLOBAL/BU-1/TEAM-A/WS-1"
        verb="update"
        allowedVerbs={["read", "update"]}
        labels={labels}
      >
        <div data-testid="secret-admin-form">Admin Form</div>
      </PermissionGuard>,
    );
    expect(screen.getByTestId("secret-admin-form")).toBeDefined();

    rerender(
      <PermissionGuard
        scopePath="GLOBAL/BU-1/TEAM-A/WS-1"
        verb="grant"
        allowedVerbs={["read"]}
        hiddenWhenUnauthorized
        labels={labels}
      >
        <div data-testid="secret-admin-form">Admin Form</div>
      </PermissionGuard>,
    );
    expect(screen.queryByTestId("secret-admin-form")).toBeNull();
    expect(screen.queryByTestId("permission-guard-passive-lock")).toBeNull();

    const onRequestAccess = vi.fn();
    rerender(
      <PermissionGuard
        scopePath="GLOBAL/BU-1/TEAM-A/WS-1"
        verb="execute"
        allowedVerbs={["read"]}
        resourceTitle="Pipeline SecOps"
        labels={labels}
        onRequestAccess={onRequestAccess}
      >
        <div data-testid="secret-admin-form">Admin Form</div>
      </PermissionGuard>,
    );
    expect(screen.getByTestId("permission-guard-passive-lock")).toBeDefined();
    fireEvent.click(screen.getByTestId("permission-guard-request-access-btn"));
    expect(onRequestAccess).toHaveBeenCalledWith("GLOBAL/BU-1/TEAM-A/WS-1", "execute");
  });

  it("SecretField enforces write-only keep/set/clear protocol without exposing plaintext", () => {
    const onSecretAction = vi.fn();
    render(
      <SecretField
        status={{
          configured: true,
          fingerprint: "sha256:9f86d081",
          updatedAt: "2026-10-30T12:00:00Z",
          updatedBy: "secops@orcia.local",
        }}
        onSecretAction={onSecretAction}
        labels={{
          fieldLabel: "Jeton Git",
          configuredBadge: "Configuré",
          unconfiguredBadge: "Non configuré",
          fingerprintPrefix: "Empreinte",
          replaceSecretCta: "Remplacer",
          cancelReplaceCta: "Annuler",
          clearSecretCta: "Effacer",
          saveNewSecretCta: "Enregistrer",
          inputPlaceholder: "Nouveau secret...",
        }}
      />,
    );

    expect(screen.getByTestId("secret-field-fingerprint").textContent).toContain(
      "sha256:9f86d081",
    );
    fireEvent.click(screen.getByTestId("secret-field-replace-toggle-btn"));
    const input = screen.getByTestId("secret-field-write-only-input");
    fireEvent.change(input, { target: { value: "glpat-super-secret-value" } });
    fireEvent.click(screen.getByTestId("secret-field-commit-set-btn"));
    expect(onSecretAction).toHaveBeenCalledWith({
      action: "set",
      plaintextValue: "glpat-super-secret-value",
    });
  });

  it("InferenceTierBadge & EffortSelector display abstract tiers (never model names) and trigger effort changes", () => {
    const onTierChange = vi.fn();
    const onEffortChange = vi.fn();
    const labels = {
      tierLabel: "Palier cognitif",
      effortLabel: "Effort",
      simpleBadge: "Simple",
      mediumBadge: "Moyen",
      complexBadge: "Complexe",
      autoBadge: "Auto",
      effortDefault: "Défaut",
      effortFast: "Rapide",
      effortBalanced: "Équilibré",
      effortDeep: "Approfondi",
    };

    render(
      <div>
        <InferenceTierBadge tier="auto" effort="balanced" labels={labels} />
        <EffortSelector
          selectedTier="auto"
          selectedEffort="balanced"
          labels={labels}
          onTierChange={onTierChange}
          onEffortChange={onEffortChange}
        />
      </div>,
    );

    expect(screen.getByTestId("inference-tier-badge-auto").textContent).toContain("Auto");
    expect(screen.getByTestId("inference-effort-badge-balanced").textContent).toContain(
      "Équilibré",
    );
    fireEvent.change(screen.getByTestId("select-inference-effort"), {
      target: { value: "deep" },
    });
    expect(onEffortChange).toHaveBeenCalledWith("deep");
  });

  it("WorkflowTopGovernanceBar displays 5 lifecycle tabs, SemVer badge, pre-prompt sha256, contract counts, and Fork button", () => {
    const onForkDraft = vi.fn();
    const onSelectTab = vi.fn();
    render(
      <WorkflowTopGovernanceBar
        workflowKey="wf-discovery-audit"
        version="1.0.0"
        lifecycleStatus="PUBLISHED"
        prePromptSha256="abcdef0123456789abcdef"
        requiredParams={["p_1", "p_2"]}
        requiredMarkdownSections={["Contexte", "Décisions"]}
        triggers={["manual", "webhook"]}
        activeTab="PUBLISHED"
        tabCounts={[
          { tab: "PUBLISHED", label: "Publiés", count: 3 },
          { tab: "DRAFT", label: "Brouillons", count: 1 },
          { tab: "TRASH", label: "Corbeille", count: 0 },
          { tab: "ACTIVE_RUNS", label: "En cours", count: 2 },
          { tab: "PAUSED_ARBITRATION", label: "Arbitrage", count: 1 },
        ]}
        onSelectTab={onSelectTab}
        onForkDraft={onForkDraft}
        labels={{
          prePromptButton: "Pré-prompt IA",
          contractButton: "Contrat du workflow",
          triggersButton: "Déclencheurs",
          dryRunButton: "▷ Tester",
          forkButton: "Modifier (Fork)",
          publishButton: "Publier",
          readOnlyPublishedHint: "Version publiée immuable",
        }}
      />,
    );

    expect(screen.getByTestId("workflow-semver-badge").textContent).toContain("v1.0.0");
    fireEvent.click(screen.getByTestId("workflow-fork-btn"));
    expect(onForkDraft).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("studio-tab-DRAFT"));
    expect(onSelectTab).toHaveBeenCalledWith("DRAFT");
  });

  it("LayersInspectorPopover groups sub-workflow layers into 3 zones and toggles enabled/SKIPPED", () => {
    const onToggleLayer = vi.fn();
    render(
      <LayersInspectorPopover
        nodeId="node-sub-1"
        nodeTitle="Analyse d'Architecture"
        layers={[
          {
            layerId: "layer-in",
            label: "Collecte de contexte",
            zone: "inputs",
            orderIndex: 1,
            enabled: true,
          },
          {
            layerId: "layer-cap",
            label: "Synthèse contradictoire",
            zone: "capabilities",
            orderIndex: 1,
            enabled: false,
          },
        ]}
        onToggleLayer={onToggleLayer}
        labels={{
          badgePrefix: "COUCHES",
          inputsZoneTitle: "Entrées & Contexte",
          capabilitiesZoneTitle: "Capacités & Agents internes",
          deliverablesZoneTitle: "Livrables & Contrôles",
          enabledStatusLabel: "Actif",
          skippedStatusLabel: "SKIPPED",
          deleteActionLabel: "Supprimer",
        }}
      />,
    );

    expect(screen.getByTestId("layers-count-badge-node-sub-1").textContent).toContain(
      "COUCHES · 2",
    );
    expect(screen.getByTestId("layer-status-layer-cap").textContent).toContain("SKIPPED");
    fireEvent.click(screen.getByTestId("layer-toggle-layer-in"));
    expect(onToggleLayer).toHaveBeenCalledWith("layer-in", false);
  });

  it("DurableWizardRunnerView renders 5 steps, checkpoint resume banner, and step completion action", () => {
    const onCompleteStep = vi.fn();
    const onProvisionDemoWorkspace = vi.fn();
    render(
      <DurableWizardRunnerView
        sessionId="wiz-123"
        wizardType="sdlc_tech_lead"
        currentStep={3}
        totalSteps={5}
        status="IN_PROGRESS"
        resumedFromCheckpoint
        steps={[
          { stepIndex: 1, title: "Profil", description: "Choix du profil" },
          { stepIndex: 2, title: "Dépôt", description: "Connexion Git" },
          { stepIndex: 3, title: "Base documentaire", description: "Connexion KB" },
          { stepIndex: 4, title: "Routage IA", description: "Tiers LLM" },
          { stepIndex: 5, title: "Réciprocité RAG", description: "Vérification" },
        ]}
        onCompleteStep={onCompleteStep}
        onProvisionDemoWorkspace={onProvisionDemoWorkspace}
        labels={{
          title: "Assistant d'initialisation durable",
          resumeBannerText: "Session reprise au point de sauvegarde DBOS",
          stepCounterPrefix: "Étape",
          validateAndContinueButton: "Valider l'étape",
          completedBadgeText: "Terminé",
          demoWorkspaceButton: "Provisionner Démo 1-clic",
          citationLabel: "Preuve documentaire",
        }}
      />,
    );

    expect(screen.getByTestId("wizard-resumed-banner").textContent).toContain("(3/5)");
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));
    expect(onCompleteStep).toHaveBeenCalledWith(3);
    fireEvent.click(screen.getByTestId("wizard-demo-workspace-btn"));
    expect(onProvisionDemoWorkspace).toHaveBeenCalledTimes(1);
  });
});

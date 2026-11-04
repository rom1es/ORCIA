import {
  DurableWizardRunnerView,
  type DurableWizardProfileType,
  type DurableWizardStepDescriptor,
} from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import { usePlatformSetup } from "../components/platformSetupStore";
import { useI18n } from "../i18n";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

const WIZARD_STEPS: readonly DurableWizardStepDescriptor[] = [
  {
    stepIndex: 1,
    title: "1. Organisation & Équipe",
    description: "Création de votre Direction (BU) ou Équipe et choix de votre rôle.",
  },
  {
    stepIndex: 2,
    title: "2. Création de l'Espace de Travail",
    description: "Choix du nom, du niveau de confidentialité et de la phase actuelle.",
  },
  {
    stepIndex: 3,
    title: "3. Connexion d'une Source Documentaire",
    description: "Ajout d'un dépôt de code, d'un espace documentaire ou d'un outil de suivi.",
  },
  {
    stepIndex: 4,
    title: "4. Choix du Modèle IA",
    description: "Association d'un modèle IA principal pour vos questions et processus.",
  },
  {
    stepIndex: 5,
    title: "5. Vérification & Mise en Service",
    description: "Récapitulatif de vos réglages et ouverture de votre Espace de travail.",
  },
];

function WizardsRouteComponent() {
  const { dictionary, locale } = useI18n();
  const labels = dictionary.settingsHub.wizardLabels;
  const isFr = locale === "fr";
  const {
    addOrgUnit,
    createWorkspace,
    registerDatasource,
    upsertLlmTier,
  } = usePlatformSetup();

  const [wizardProfile, setWizardProfile] =
    useState<DurableWizardProfileType>("sdlc_tech_lead");
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [status, setStatus] = useState<"IN_PROGRESS" | "COMPLETED">("IN_PROGRESS");

  // Step inputs (all start empty!)
  const [orgUnitName, setOrgUnitName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [connectorAlias, setConnectorAlias] = useState("");
  const [connectorUri, setConnectorUri] = useState("");
  const [primaryModelId, setPrimaryModelId] = useState("");

  const handleCompleteStep = (stepNumber: number) => {
    if (stepNumber === 1 && orgUnitName.trim()) {
      addOrgUnit({
        name: orgUnitName.trim(),
        slug: orgUnitName.trim().toLowerCase().replace(/\s+/g, "-"),
        level: "TEAM",
        parentId: "scope-global",
      });
    } else if (stepNumber === 2 && workspaceName.trim()) {
      createWorkspace({
        name: workspaceName.trim(),
        slug: workspaceName.trim().toLowerCase().replace(/\s+/g, "-"),
        visibilityMode: "STANDARD",
        lifecyclePhase: "BUILD",
      });
    } else if (stepNumber === 3 && connectorAlias.trim() && connectorUri.trim()) {
      registerDatasource({
        workspaceName: workspaceName.trim() || "Plateforme Globale ORCIA",
        alias: connectorAlias.trim(),
        scheme: "git",
        uri: connectorUri.trim(),
        executionIdentity: "passthrough",
        freshnessTtlDays: 30,
      });
    } else if (stepNumber === 4 && primaryModelId.trim()) {
      upsertLlmTier({
        tier: "medium",
        primaryModel: primaryModelId.trim(),
        secondaryModel: primaryModelId.trim(),
        modelFamily: "family-a",
        defaultEffort: "balanced",
      });
    }

    if (stepNumber >= 5) {
      setStatus("COMPLETED");
    } else {
      setCurrentStep(stepNumber + 1);
    }
  };

  const inputStyle: React.CSSProperties = {
    padding: "7px 10px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--color-border)",
    backgroundColor: "var(--color-surface-card)",
    color: "var(--color-foreground)",
    width: "100%",
    boxSizing: "border-box",
  };

  return (
    <div
      data-testid="wizards-route-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div
        className="orcia-bento-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div>
          <strong style={{ fontSize: "15px" }}>
            {isFr
              ? "Choisir un Parcours de Configuration Guidé"
              : "Choose a Guided Setup Journey"}
          </strong>
          <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr
              ? "Vous accompagne étape par étape pour configurer votre environnement."
              : "Guides you step by step to set up your environment."}
          </p>
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <select
            data-testid="wizard-profile-selector"
            value={wizardProfile}
            onChange={(e) => {
              setWizardProfile(e.target.value as DurableWizardProfileType);
              setCurrentStep(1);
              setStatus("IN_PROGRESS");
            }}
            style={{
              padding: "6px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
            }}
          >
            <option value="sdlc_tech_lead">
              {isFr ? "Création d'un Espace de travail d'équipe" : "Team Workspace Setup"}
            </option>
            <option value="secops_admin">
              {isFr ? "Configuration initiale de l'organisation" : "Initial Organization Setup"}
            </option>
            <option value="ops_manager">
              {isFr ? "Connexion d'une source documentaire ou outil" : "Connect a Document Source or Tool"}
            </option>
          </select>

          {currentStep > 1 && status !== "COMPLETED" && (
            <button
              type="button"
              data-testid="wizard-step-back-btn"
              onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1))}
              style={{
                padding: "6px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor: "var(--color-surface-card)",
                cursor: "pointer",
              }}
            >
              {isFr ? "← Étape précédente" : "← Previous step"}
            </button>
          )}
        </div>
      </div>

      {status !== "COMPLETED" && (
        <div
          data-testid={`wizard-step-form-${currentStep}`}
          className="orcia-bento-card"
          style={{ display: "flex", flexDirection: "column", gap: "10px" }}
        >
          {currentStep === 1 && (
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontWeight: 600, fontSize: "13px" }}>
                {isFr ? "Nom de la Direction (BU) ou de l'Équipe" : "Division (BU) or Team Name"}
              </span>
              <input
                type="text"
                data-testid="wizard-input-org-unit"
                value={orgUnitName}
                onChange={(e) => setOrgUnitName(e.target.value)}
                placeholder={isFr ? "Saisir le nom de l'équipe ou de la direction..." : "Enter Team or Division name..."}
                style={inputStyle}
              />
            </label>
          )}

          {currentStep === 2 && (
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontWeight: 600, fontSize: "13px" }}>
                {isFr ? "Nom de l'Espace de Travail" : "Workspace Name"}
              </span>
              <input
                type="text"
                data-testid="wizard-input-workspace-name"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                placeholder={isFr ? "Saisir le nom de l'Espace..." : "Enter Workspace name..."}
                style={inputStyle}
              />
            </label>
          )}

          {currentStep === 3 && (
            <div style={{ display: "grid", gap: "8px" }}>
              <input
                type="text"
                data-testid="wizard-input-connector-alias"
                value={connectorAlias}
                onChange={(e) => setConnectorAlias(e.target.value)}
                placeholder={isFr ? "Nom donné à cette source..." : "Source display name..."}
                style={inputStyle}
              />
              <input
                type="text"
                data-testid="wizard-input-connector-uri"
                value={connectorUri}
                onChange={(e) => setConnectorUri(e.target.value)}
                placeholder={isFr ? "Adresse de la source (ex: https://...)" : "Source address (e.g. https://...)"}
                style={inputStyle}
              />
            </div>
          )}

          {currentStep === 4 && (
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontWeight: 600, fontSize: "13px" }}>
                {isFr ? "Nom du Modèle IA Principal (Niveau Standard)" : "Primary AI Model Name (Standard Level)"}
              </span>
              <input
                type="text"
                data-testid="wizard-input-primary-model"
                value={primaryModelId}
                onChange={(e) => setPrimaryModelId(e.target.value)}
                placeholder={isFr ? "Saisir le nom du modèle IA..." : "Enter AI model name..."}
                style={inputStyle}
              />
            </label>
          )}

          {currentStep === 5 && (
            <p style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
              {isFr
                ? "Vérifiez vos paramètres puis cliquez sur « Valider et continuer » pour ouvrir votre Espace."
                : "Review your settings and click 'Validate and continue' to open your Workspace."}
            </p>
          )}
        </div>
      )}

      <DurableWizardRunnerView
        sessionId="wiz-session-initial"
        wizardType={wizardProfile}
        currentStep={currentStep}
        totalSteps={5}
        status={status}
        steps={WIZARD_STEPS}
        resumedFromCheckpoint={false}
        reciprocityCitationUri={null}
        onCompleteStep={handleCompleteStep}
        labels={labels}
      />
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/wizards",
  validateSearch: validateOrciaRouteSearch,
  component: WizardsRouteComponent,
});

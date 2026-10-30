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
    title: "1. Organisation & Périmètre",
    description: "Initialisation de l'unité d'organisation (BU / Équipe) et du profil.",
  },
  {
    stepIndex: 2,
    title: "2. Création de l'Espace de Travail",
    description: "Paramétrage du nom, du niveau de visibilité et de la phase du cycle de vie.",
  },
  {
    stepIndex: 3,
    title: "3. Connecteur & Source Documentaire",
    description: "Rattachement d'un connecteur (Git / Confluence / Jira / DB) write-only.",
  },
  {
    stepIndex: 4,
    title: "4. Paliers Cognitifs IA",
    description: "Configuration des paliers simple / medium / complex / auto (AD-10).",
  },
  {
    stepIndex: 5,
    title: "5. Validation Finale & Activation",
    description: "Vérification des 4 prérequis et activation opérationnelle du périmètre.",
  },
];

function WizardsRouteComponent() {
  const { dictionary, locale } = useI18n();
  const labels = dictionary.epic8SettingsHub.wizardLabels;
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
              ? "Sélection du Parcours d'Initialisation Guidé"
              : "Select Guided Onboarding Wizard"}
          </strong>
          <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr
              ? "Accompagne pas-à-pas la création des entités à partir d'un environnement vierge."
              : "Guides step-by-step entity creation from a blank environment."}
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
            <option value="sdlc_tech_lead">orcia://system/wizards/workspace-onboarding@1.0.0</option>
            <option value="secops_admin">orcia://system/wizards/platform-bootstrap@1.0.0</option>
            <option value="ops_manager">orcia://system/wizards/connector-setup@1.0.0</option>
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
                {isFr ? "Nom de l'Unité d'Organisation (BU / Équipe)" : "Organization Unit Name (BU / Team)"}
              </span>
              <input
                type="text"
                data-testid="wizard-input-org-unit"
                value={orgUnitName}
                onChange={(e) => setOrgUnitName(e.target.value)}
                placeholder={isFr ? "Saisir le nom de l'équipe ou BU..." : "Enter Team or BU name..."}
                style={inputStyle}
              />
            </label>
          )}

          {currentStep === 2 && (
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontWeight: 600, fontSize: "13px" }}>
                {isFr ? "Nom de l'Espace de Travail (Workspace)" : "Workspace Name"}
              </span>
              <input
                type="text"
                data-testid="wizard-input-workspace-name"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                placeholder={isFr ? "Saisir le nom du Workspace..." : "Enter Workspace name..."}
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
                placeholder={isFr ? "Alias du connecteur..." : "Connector alias..."}
                style={inputStyle}
              />
              <input
                type="text"
                data-testid="wizard-input-connector-uri"
                value={connectorUri}
                onChange={(e) => setConnectorUri(e.target.value)}
                placeholder={isFr ? "URI de la source (ex: git://...)" : "Source URI (e.g. git://...)"}
                style={inputStyle}
              />
            </div>
          )}

          {currentStep === 4 && (
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontWeight: 600, fontSize: "13px" }}>
                {isFr ? "Identifiant du Modèle IA Primaire (Palier Medium)" : "Primary AI Model ID (Medium Tier)"}
              </span>
              <input
                type="text"
                data-testid="wizard-input-primary-model"
                value={primaryModelId}
                onChange={(e) => setPrimaryModelId(e.target.value)}
                placeholder={isFr ? "Saisir l'identifiant du modèle..." : "Enter model identifier..."}
                style={inputStyle}
              />
            </label>
          )}

          {currentStep === 5 && (
            <p style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
              {isFr
                ? "Vérifiez vos paramètres puis cliquez sur « Valider l'étape » pour activer l'environnement."
                : "Review your settings and click Validate Step to activate the environment."}
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

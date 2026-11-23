import { OrciaProblemError } from "@orcia/api-client";
import type { DurableWizardStepDescriptor } from "@orcia/ui";
import type React from "react";

export function extractWizardStepString(
  stateJsonb: Record<string, unknown> | undefined,
  stepKey: string,
  fieldKey: string,
): string {
  const stepData = stateJsonb?.[stepKey];
  if (stepData && typeof stepData === "object" && !Array.isArray(stepData)) {
    const val = (stepData as Record<string, unknown>)[fieldKey];
    if (typeof val === "string") return val;
  }
  return "";
}

export function formatWizardError(err: unknown, fallback: string): string {
  if (err instanceof OrciaProblemError) {
    return `${err.problem.detail} (${err.problem.error_code})`;
  }
  if (err instanceof Error && err.message.trim()) {
    return err.message;
  }
  return fallback;
}

export const WIZARD_STEPS_FR: readonly DurableWizardStepDescriptor[] = [
  {
    stepIndex: 1,
    title: "Organisation & Équipe",
    description: "Création de votre Direction (BU) ou Équipe et choix de votre rôle.",
  },
  {
    stepIndex: 2,
    title: "Création de l'Espace de Travail",
    description: "Choix du nom, du niveau de confidentialité et de la phase actuelle.",
  },
  {
    stepIndex: 3,
    title: "Connexion d'une Source Documentaire",
    description: "Ajout d'un dépôt de code, d'un espace documentaire ou d'un outil de suivi.",
  },
  {
    stepIndex: 4,
    title: "Choix du Modèle IA",
    description: "Association d'un modèle IA principal pour vos questions et processus.",
  },
  {
    stepIndex: 5,
    title: "Vérification & Mise en Service",
    description: "Récapitulatif de vos réglages et ouverture de votre Espace de travail.",
  },
];

export const WIZARD_STEPS_EN: readonly DurableWizardStepDescriptor[] = [
  {
    stepIndex: 1,
    title: "Organization & Team",
    description: "Create your Division (BU) or Team and select your role.",
  },
  {
    stepIndex: 2,
    title: "Workspace Creation",
    description: "Choose the workspace name, confidentiality level, and initial phase.",
  },
  {
    stepIndex: 3,
    title: "Connect a Document Source",
    description: "Add a code repository, documentation space, or issue tracker.",
  },
  {
    stepIndex: 4,
    title: "Primary AI Model",
    description: "Assign a primary AI model for your questions and processes.",
  },
  {
    stepIndex: 5,
    title: "Verification & Go-Live",
    description: "Review your configuration and open your Workspace.",
  },
];

export const WIZARD_STEPS_BY_LOCALE = {
  fr: WIZARD_STEPS_FR,
  en: WIZARD_STEPS_EN,
} as const;

export interface WizardsStepFormProps {
  readonly currentStep: number;
  readonly status: "IN_PROGRESS" | "PAUSED" | "COMPLETED" | "ABANDONED";
  readonly isFr: boolean;
  readonly orgUnitName: string;
  readonly workspaceName: string;
  readonly connectorAlias: string;
  readonly connectorUri: string;
  readonly primaryModelId: string;
  readonly onOrgUnitNameChange: (val: string) => void;
  readonly onWorkspaceNameChange: (val: string) => void;
  readonly onConnectorAliasChange: (val: string) => void;
  readonly onConnectorUriChange: (val: string) => void;
  readonly onPrimaryModelIdChange: (val: string) => void;
}

const INPUT_STYLE: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  width: "100%",
  boxSizing: "border-box",
};

export function WizardsStepForm({
  currentStep,
  status,
  isFr,
  orgUnitName,
  workspaceName,
  connectorAlias,
  connectorUri,
  primaryModelId,
  onOrgUnitNameChange,
  onWorkspaceNameChange,
  onConnectorAliasChange,
  onConnectorUriChange,
  onPrimaryModelIdChange,
}: WizardsStepFormProps): React.ReactElement | null {
  if (status === "COMPLETED") {
    return null;
  }

  return (
    <div
      data-testid={`wizard-step-form-${currentStep}`}
      style={{ display: "flex", flexDirection: "column", gap: "10px" }}
    >
      {currentStep === 1 && (
        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontWeight: 600, fontSize: "13px" }}>
            {isFr ? "Nom de la Direction (BU) ou de l'Équipe" : "Division (BU) or Team Name"}
          </span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="wizard-input-org-unit"
            value={orgUnitName}
            onChange={(e) => onOrgUnitNameChange(e.target.value)}
            placeholder={
              isFr
                ? "Saisir le nom de l'équipe ou de la direction..."
                : "Enter Team or Division name..."
            }
            style={INPUT_STYLE}
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
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="wizard-input-workspace-name"
            value={workspaceName}
            onChange={(e) => onWorkspaceNameChange(e.target.value)}
            placeholder={isFr ? "Saisir le nom de l'Espace..." : "Enter Workspace name..."}
            style={INPUT_STYLE}
          />
        </label>
      )}

      {currentStep === 3 && (
        <div style={{ display: "grid", gap: "8px" }}>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="wizard-input-connector-alias"
            value={connectorAlias}
            onChange={(e) => onConnectorAliasChange(e.target.value)}
            placeholder={isFr ? "Nom donné à cette source..." : "Source display name..."}
            style={INPUT_STYLE}
          />
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="wizard-input-connector-uri"
            value={connectorUri}
            onChange={(e) => onConnectorUriChange(e.target.value)}
            placeholder={
              isFr ? "Adresse de la source (ex: https://...)" : "Source address (e.g. https://...)"
            }
            style={INPUT_STYLE}
          />
        </div>
      )}

      {currentStep === 4 && (
        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontWeight: 600, fontSize: "13px" }}>
            {isFr
              ? "Nom du Modèle IA Principal (Niveau Standard)"
              : "Primary AI Model Name (Standard Level)"}
          </span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="wizard-input-primary-model"
            value={primaryModelId}
            onChange={(e) => onPrimaryModelIdChange(e.target.value)}
            placeholder={isFr ? "Saisir le nom du modèle IA..." : "Enter AI model name..."}
            style={INPUT_STYLE}
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
  );
}

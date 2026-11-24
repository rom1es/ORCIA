import { OrciaProblemError } from "@orcia/api-client";
import type { DurableWizardStepDescriptor } from "@orcia/ui";
import type React from "react";
import { DICTIONARIES, resolveDictionaryForFlag } from "../../i18n";

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

export const WIZARD_STEPS_FR: readonly DurableWizardStepDescriptor[] =
  DICTIONARIES.fr.routesAndWizards.wizardsStepForm.steps;

export const WIZARD_STEPS_EN: readonly DurableWizardStepDescriptor[] =
  DICTIONARIES.en.routesAndWizards.wizardsStepForm.steps;

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
  const copy = resolveDictionaryForFlag(isFr).routesAndWizards.wizardsStepForm;

  return (
    <div
      data-testid={`wizard-step-form-${currentStep}`}
      style={{ display: "flex", flexDirection: "column", gap: "10px" }}
    >
      {currentStep === 1 && (
        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontWeight: 600, fontSize: "13px" }}>{copy.orgUnitLabel}</span>
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
            placeholder={copy.orgUnitPlaceholder}
            style={INPUT_STYLE}
          />
        </label>
      )}

      {currentStep === 2 && (
        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontWeight: 600, fontSize: "13px" }}>{copy.workspaceLabel}</span>
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
            placeholder={copy.workspacePlaceholder}
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
            placeholder={copy.connectorAliasPlaceholder}
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
            placeholder={copy.connectorUriPlaceholder}
            style={INPUT_STYLE}
          />
        </div>
      )}

      {currentStep === 4 && (
        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontWeight: 600, fontSize: "13px" }}>{copy.primaryModelLabel}</span>
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
            placeholder={copy.primaryModelPlaceholder}
            style={INPUT_STYLE}
          />
        </label>
      )}

      {currentStep === 5 && (
        <p style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
          {copy.reviewInstruction}
        </p>
      )}
    </div>
  );
}

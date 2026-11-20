import React, { useEffect, useState } from "react";
import { OrciaDialog } from "../RadixDesignSystemPrimitives";

export interface FinopsBudgetPolicyModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly currentScopeType?: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  readonly currentScopeId?: string | null;
  readonly scopeIdsByLevel?: Partial<Record<"BU" | "TEAM" | "WORKSPACE", string | null>>;
  readonly defaultMonthlyBudgetUsd?: number;
  readonly defaultWarningPct?: number;
  readonly defaultHardStopPct?: number;
  readonly labels: {
    budgetTitle: string;
    budgetDescription: string;
    monthlyLimitLabel: string;
    warningThresholdLabel: string;
    hardStopLabel: string;
    scopeLabel: string;
    scopeGlobalLabel?: string;
    scopeBuLabel?: string;
    scopeTeamLabel?: string;
    scopeWorkspaceLabel?: string;
    saveButton: string;
    cancelButton: string;
  };
  readonly onSaveBudget?: (
    scopeType: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE",
    scopeId: string | null,
    monthlyBudgetUsd: number,
    warningThresholdPct: number,
    hardStopPct: number,
  ) => void;
}

export function FinopsBudgetPolicyModal({
  open,
  onOpenChange,
  currentScopeType = "GLOBAL",
  currentScopeId = null,
  scopeIdsByLevel,
  defaultMonthlyBudgetUsd = 100,
  defaultWarningPct = 80,
  defaultHardStopPct = 100,
  labels,
  onSaveBudget,
}: FinopsBudgetPolicyModalProps): React.ReactElement {
  const [monthlyBudget, setMonthlyBudget] = useState<number>(defaultMonthlyBudgetUsd);
  const [warningPct, setWarningPct] = useState<number>(defaultWarningPct);
  const [hardStopPct, setHardStopPct] = useState<number>(defaultHardStopPct);
  const [scopeType, setScopeType] = useState<"GLOBAL" | "BU" | "TEAM" | "WORKSPACE">(currentScopeType);

  useEffect(() => {
    if (!open) return;
    setScopeType(currentScopeType);
    setMonthlyBudget(defaultMonthlyBudgetUsd);
    setWarningPct(defaultWarningPct);
    setHardStopPct(defaultHardStopPct);
  }, [open, currentScopeType, currentScopeId, defaultMonthlyBudgetUsd, defaultWarningPct, defaultHardStopPct]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const resolvedScopeId =
      scopeType === "GLOBAL"
        ? null
        : scopeType === currentScopeType
          ? currentScopeId
          : (scopeIdsByLevel?.[scopeType] ?? currentScopeId ?? null);
    onSaveBudget?.(scopeType, resolvedScopeId, monthlyBudget, warningPct, hardStopPct);
    onOpenChange(false);
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={labels.budgetTitle}
      description={labels.budgetDescription}
      testId="finops-budget-modal"
      closeLabel={labels.cancelButton}
      hideHeaderCloseButton
    >
      <form
        onSubmit={handleSubmit}
        data-testid="finops-budget-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "12px" }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="finops-budget-scope-select" style={{ fontSize: "12px", fontWeight: 600 }}>{labels.scopeLabel}</label>
          <select
            id="finops-budget-scope-select"
            data-testid="finops-budget-scope-select"
            value={scopeType}
            onChange={(e) => setScopeType(e.target.value as "GLOBAL" | "BU" | "TEAM" | "WORKSPACE")}
            className="orcia-ds-input"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
          >
            <option value="GLOBAL">{labels.scopeGlobalLabel ?? "Plateforme entière"}</option>
            <option value="BU">{labels.scopeBuLabel ?? "Direction"}</option>
            <option value="TEAM">{labels.scopeTeamLabel ?? "Équipe"}</option>
            <option value="WORKSPACE">{labels.scopeWorkspaceLabel ?? "Espace"}</option>
          </select>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="finops-budget-monthly-limit" style={{ fontSize: "12px", fontWeight: 600 }}>{labels.monthlyLimitLabel}</label>
          <input
            id="finops-budget-monthly-limit"
            data-testid="finops-budget-monthly-limit"
            type="number"
            min="0"
            step="10"
            value={monthlyBudget}
            onChange={(e) => setMonthlyBudget(Number(e.target.value))}
            className="orcia-ds-input"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="finops-budget-warning-pct" style={{ fontSize: "12px", fontWeight: 600 }}>{labels.warningThresholdLabel}</label>
            <input
              id="finops-budget-warning-pct"
              data-testid="finops-budget-warning-pct"
              type="number"
              min="1"
              max="100"
              value={warningPct}
              onChange={(e) => setWarningPct(Number(e.target.value))}
              className="orcia-ds-input"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="finops-budget-hardstop-pct" style={{ fontSize: "12px", fontWeight: 600 }}>{labels.hardStopLabel}</label>
            <input
              id="finops-budget-hardstop-pct"
              data-testid="finops-budget-hardstop-pct"
              type="number"
              min={warningPct}
              max="200"
              value={hardStopPct}
              onChange={(e) => setHardStopPct(Number(e.target.value))}
              className="orcia-ds-input"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
            />
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "12px" }}>
          <button
            type="button"
            data-testid="finops-budget-cancel-btn"
            className="orcia-ds-btn orcia-ds-btn-secondary"
            onClick={() => onOpenChange(false)}
          >
            {labels.cancelButton}
          </button>
          <button
            type="submit"
            data-testid="finops-budget-save-btn"
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {labels.saveButton}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}

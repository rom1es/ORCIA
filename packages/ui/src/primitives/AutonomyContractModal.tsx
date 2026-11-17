import React, { useEffect, useState } from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { OrciaIcon } from "../components/icons";
import {
  OrciaAlertBanner,
  OrciaButton,
  OrciaDialog,
  OrciaInput,
  OrciaSelect,
} from "./DesignSystemControls";

export type UiAutonomyTieBreakPolicy =
  | "ONTOLOGY_AXIOM_FIRST"
  | "DEFER_AND_CONTINUE_WITH_ASSUMPTION"
  | "PAUSE_AND_ESCALATE";

export interface UiEligibleServiceAccountOption {
  readonly id: string;
  readonly displayName: string;
  readonly principalId: string;
}

export interface UiActiveAutonomyContractView {
  readonly id: string;
  readonly servicePrincipalId: string;
  readonly allowedReadSources: readonly string[];
  readonly allowedWriteActions: readonly string[];
  readonly maxCostPerRunUsd: number;
  readonly tieBreakPolicy: UiAutonomyTieBreakPolicy;
  readonly signedByRoleLabel: string;
  readonly signedAtIso: string;
  readonly signatureSha256: string;
}

export interface SignAutonomyContractDraft {
  readonly servicePrincipalId: string;
  readonly allowedReadSources: readonly string[];
  readonly allowedWriteActions: readonly string[];
  readonly maxCostPerRunUsd: number;
  readonly tieBreakPolicy: UiAutonomyTieBreakPolicy;
}

export interface AutonomyContractModalLabels {
  readonly title: string;
  readonly description: string;
  readonly helpButtonLabel: string;
  readonly activeBannerTitle: string;
  readonly signerRolePrefix: string;
  readonly serviceAccountLabel: string;
  readonly serviceAccountEmptyHint: string;
  readonly readSourcesLabel: string;
  readonly writeActionsLabel: string;
  readonly maxCostLabel: string;
  readonly tieBreakPolicyLabel: string;
  readonly tieBreakOntologyFirst: string;
  readonly tieBreakDeferAssumption: string;
  readonly tieBreakPauseEscalate: string;
  readonly criticalBlockedNotice: string;
  readonly signButton: string;
  readonly signingButton: string;
  readonly revokeButton: string;
  readonly closeButton: string;
}

export interface AutonomyContractModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly workflowTitle: string;
  readonly isCriticalWorkflow?: boolean;
  readonly eligibleServiceAccounts: readonly UiEligibleServiceAccountOption[];
  readonly availableReadSources: readonly string[];
  readonly availableWriteActions: readonly string[];
  readonly activeContract: UiActiveAutonomyContractView | null;
  readonly submitting?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: AutonomyContractModalLabels;
  readonly onSignContract: (draft: SignAutonomyContractDraft) => Promise<void> | void;
  readonly onRevokeContract: () => Promise<void> | void;
  readonly onOpenHelpSection: (sectionId: string) => void;
}

export function AutonomyContractModal({
  open,
  onOpenChange,
  workflowTitle,
  isCriticalWorkflow = false,
  eligibleServiceAccounts,
  availableReadSources,
  availableWriteActions,
  activeContract,
  submitting = false,
  errorMessage = null,
  labels,
  onSignContract,
  onRevokeContract,
  onOpenHelpSection,
}: AutonomyContractModalProps): React.ReactElement {
  const [selectedSpId, setSelectedSpId] = useState<string>("");
  const [selectedReads, setSelectedReads] = useState<string[]>([]);
  const [selectedWrites, setSelectedWrites] = useState<string[]>([]);
  const [maxCostUsd, setMaxCostUsd] = useState<string>("5");
  const [tieBreak, setTieBreak] = useState<UiAutonomyTieBreakPolicy>("ONTOLOGY_AXIOM_FIRST");

  useEffect(() => {
    if (!open) return;
    setSelectedSpId(
      activeContract?.servicePrincipalId ?? eligibleServiceAccounts[0]?.id ?? "",
    );
    setSelectedReads(
      activeContract ? [...activeContract.allowedReadSources] : [...availableReadSources],
    );
    setSelectedWrites(
      activeContract ? [...activeContract.allowedWriteActions] : [...availableWriteActions],
    );
    setMaxCostUsd(String(activeContract?.maxCostPerRunUsd ?? 5));
    setTieBreak(activeContract?.tieBreakPolicy ?? "ONTOLOGY_AXIOM_FIRST");
  }, [open, activeContract, eligibleServiceAccounts, availableReadSources, availableWriteActions]);

  const toggleItem = (current: string[], value: string, setter: (next: string[]) => void) => {
    setter(current.includes(value) ? current.filter((v) => v !== value) : [...current, value]);
  };

  const submitContract = () => {
    if (!selectedSpId || submitting) return;
    const parsedCost = Number.parseFloat(maxCostUsd);
    void onSignContract({
      servicePrincipalId: selectedSpId,
      allowedReadSources: selectedReads,
      allowedWriteActions: selectedWrites,
      maxCostPerRunUsd: Number.isFinite(parsedCost) && parsedCost > 0 ? parsedCost : 5,
      tieBreakPolicy: tieBreak,
    });
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    submitContract();
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={labels.title}
      description={`${workflowTitle} — ${labels.description}`}
      testId="autonomy-contract-modal"
      closeLabel={labels.closeButton}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "6px" }}>
          <ContextualInfoTriggerButton
            sectionId="autonomy-contract"
            label={labels.helpButtonLabel}
            onOpenHelpSection={onOpenHelpSection}
            testId="autonomy-contract-help-trigger"
          />
        </div>

        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="autonomy-contract-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        {isCriticalWorkflow ? (
          <OrciaAlertBanner tone="amber" testId="autonomy-contract-critical-warning">
            {labels.criticalBlockedNotice}
          </OrciaAlertBanner>
        ) : null}

        {activeContract ? (
          <OrciaAlertBanner
            tone="emerald"
            testId="autonomy-contract-active-banner"
            action={
              <OrciaButton
                type="button"
                variant="danger"
                testId="autonomy-contract-revoke-btn"
                disabled={submitting}
                onClick={() => {
                  void onRevokeContract();
                }}
              >
                <OrciaIcon name="cross" size={14} />
                <span>{labels.revokeButton}</span>
              </OrciaButton>
            }
          >
            <strong>{labels.activeBannerTitle}</strong> · {labels.signerRolePrefix}{" "}
            {activeContract.signedByRoleLabel} · {activeContract.maxCostPerRunUsd} $
          </OrciaAlertBanner>
        ) : null}

        <form
          onSubmit={handleSubmit}
          data-testid="autonomy-contract-form"
          autoComplete="off"
          data-lpignore="true"
          data-form-type="other"
          style={{ display: "flex", flexDirection: "column", gap: "12px" }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="autonomy-sp-select" style={{ fontSize: "12px", fontWeight: 600 }}>
              {labels.serviceAccountLabel}
            </label>
            {eligibleServiceAccounts.length === 0 ? (
              <div
                data-testid="autonomy-contract-no-sp-hint"
                style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}
              >
                {labels.serviceAccountEmptyHint}
              </div>
            ) : (
              <OrciaSelect
                id="autonomy-sp-select"
                testId="autonomy-contract-sp-select"
                value={selectedSpId}
                onChange={(e) => setSelectedSpId(e.target.value)}
              >
                {eligibleServiceAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.displayName} ({acc.principalId})
                  </option>
                ))}
              </OrciaSelect>
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600 }}>{labels.readSourcesLabel}</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {availableReadSources.map((src) => (
                <label
                  key={src}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "12px",
                  }}
                >
                  <input
                    type="checkbox"
                    autoComplete="off"
                    data-lpignore="true"
                    data-1p-ignore="true"
                    data-bwignore="true"
                    data-protonpass-ignore="true"
                    data-form-type="other"
                    checked={selectedReads.includes(src)}
                    onChange={() => toggleItem(selectedReads, src, setSelectedReads)}
                  />
                  <span>{src}</span>
                </label>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600 }}>{labels.writeActionsLabel}</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {availableWriteActions.map((act) => (
                <label
                  key={act}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "12px",
                  }}
                >
                  <input
                    type="checkbox"
                    autoComplete="off"
                    data-lpignore="true"
                    data-1p-ignore="true"
                    data-bwignore="true"
                    data-protonpass-ignore="true"
                    data-form-type="other"
                    data-testid={`autonomy-write-action-${act}`}
                    checked={selectedWrites.includes(act)}
                    onChange={() => toggleItem(selectedWrites, act, setSelectedWrites)}
                  />
                  <span>{act}</span>
                </label>
              ))}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label htmlFor="autonomy-max-cost" style={{ fontSize: "12px", fontWeight: 600 }}>
                {labels.maxCostLabel}
              </label>
              <OrciaInput
                id="autonomy-max-cost"
                testId="autonomy-contract-max-cost-input"
                type="number"
                min="0.1"
                step="0.5"
                value={maxCostUsd}
                onChange={(e) => setMaxCostUsd(e.target.value)}
                required
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label htmlFor="autonomy-tie-break" style={{ fontSize: "12px", fontWeight: 600 }}>
                {labels.tieBreakPolicyLabel}
              </label>
              <OrciaSelect
                id="autonomy-tie-break"
                testId="autonomy-contract-tiebreak-select"
                value={tieBreak}
                onChange={(e) => setTieBreak(e.target.value as UiAutonomyTieBreakPolicy)}
              >
                <option value="ONTOLOGY_AXIOM_FIRST">{labels.tieBreakOntologyFirst}</option>
                <option value="DEFER_AND_CONTINUE_WITH_ASSUMPTION">
                  {labels.tieBreakDeferAssumption}
                </option>
                <option value="PAUSE_AND_ESCALATE">{labels.tieBreakPauseEscalate}</option>
              </OrciaSelect>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
            <OrciaButton
              type="button"
              variant="secondary"
              testId="autonomy-contract-close-btn"
              onClick={() => onOpenChange(false)}
            >
              {labels.closeButton}
            </OrciaButton>
            <OrciaButton
              type="button"
              variant="primary"
              testId="autonomy-contract-sign-btn"
              disabled={submitting || !selectedSpId}
              onClick={submitContract}
            >
              <OrciaIcon name="shield" size={14} />
              <span>{submitting ? labels.signingButton : labels.signButton}</span>
            </OrciaButton>
          </div>
        </form>
      </div>
    </OrciaDialog>
  );
}

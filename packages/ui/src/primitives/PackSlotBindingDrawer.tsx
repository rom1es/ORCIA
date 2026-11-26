import React, { useEffect, useState } from "react";
import { OrciaAlertBanner } from "./OrciaAlertBanner";
import { OrciaDialog } from "./OrciaDialog";
import type {
  PackSlotBindingDrawerLabels,
  UiPackSlotTargetCandidate,
  UiPackSlotTargetKind,
  UiWorkspacePackItem,
} from "./PackUiTypes";
import { StatusBadge } from "./StatusBadge";

export interface PackSlotBindingDraftEntry {
  readonly slotKey: string;
  readonly targetKind: UiPackSlotTargetKind;
  readonly targetId: string | null;
  readonly connectorScheme: string | null;
}

export interface PackSlotBindingDrawerProps {
  readonly open: boolean;
  readonly pack: UiWorkspacePackItem | null;
  readonly candidates: readonly UiPackSlotTargetCandidate[];
  readonly highlightedMissingSlots?: readonly string[];
  readonly readOnlyObserver?: boolean;
  readonly isSaving?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: PackSlotBindingDrawerLabels;
  readonly onOpenChange: (open: boolean) => void;
  readonly onSaveBindings: (
    pack: UiWorkspacePackItem,
    bindings: readonly PackSlotBindingDraftEntry[],
  ) => Promise<void> | void;
}

function encodeCandidateValue(
  targetKind: UiPackSlotTargetKind,
  targetId: string | null,
): string {
  if (targetKind === "UNBOUND" || !targetId) return "UNBOUND";
  return `${targetKind}::${targetId}`;
}

function decodeCandidateValue(raw: string): {
  readonly targetKind: UiPackSlotTargetKind;
  readonly targetId: string | null;
} {
  if (!raw || raw === "UNBOUND") {
    return { targetKind: "UNBOUND", targetId: null };
  }
  const sepIdx = raw.indexOf("::");
  if (sepIdx <= 0) {
    return { targetKind: "WORKSPACE_DATASOURCE", targetId: raw };
  }
  return {
    targetKind: raw.slice(0, sepIdx) as UiPackSlotTargetKind,
    targetId: raw.slice(sepIdx + 2),
  };
}

export function PackSlotBindingDrawer({
  open,
  pack,
  candidates,
  highlightedMissingSlots = [],
  readOnlyObserver = false,
  isSaving = false,
  errorMessage = null,
  labels,
  onOpenChange,
  onSaveBindings,
}: PackSlotBindingDrawerProps): React.ReactElement {
  const [draftSelections, setDraftSelections] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!pack) {
      setDraftSelections({});
      return;
    }
    const next: Record<string, string> = {};
    for (const slot of pack.declaredSlots) {
      const existing = pack.slotBindings.find((b) => b.slotKey === slot.slotKey);
      next[slot.slotKey] = existing
        ? encodeCandidateValue(existing.targetKind, existing.targetId)
        : "UNBOUND";
    }
    setDraftSelections(next);
  }, [pack]);

  const missingSet = new Set([
    ...(pack?.missingSlots ?? []),
    ...highlightedMissingSlots,
  ]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!pack || readOnlyObserver || isSaving) return;
    const bindings: PackSlotBindingDraftEntry[] = pack.declaredSlots.map((slot) => {
      const encoded = draftSelections[slot.slotKey] ?? "UNBOUND";
      const decoded = decodeCandidateValue(encoded);
      const matched = candidates.find(
        (c) => c.targetKind === decoded.targetKind && c.targetId === decoded.targetId,
      );
      return {
        slotKey: slot.slotKey,
        targetKind: decoded.targetKind,
        targetId: decoded.targetId,
        connectorScheme: matched?.scheme ?? slot.scheme ?? null,
      };
    });
    void onSaveBindings(pack, bindings);
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={pack ? `${labels.drawerTitlePrefix} · ${pack.name}` : labels.drawerTitlePrefix}
      description={labels.drawerDescription}
      testId="pack-slot-binding-drawer"
      closeLabel={labels.closeLabel}
      headerExtra={
        pack ? (
          <StatusBadge label={`v${pack.version}`} tone="cobalt" monospace />
        ) : undefined
      }
    >
      <form
        onSubmit={handleSubmit}
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        className="orcia-ds-dialog-body flex flex-col gap-3"
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" role="alert" testId="pack-slot-drawer-error-alert">
            <div>{errorMessage}</div>
            {missingSet.size > 0 ? (
              <div className="mt-1 font-mono text-[11px]">
                {labels.missingSlotsAlertTitle}: {Array.from(missingSet).join(", ")}
              </div>
            ) : null}
          </OrciaAlertBanner>
        ) : null}

        {readOnlyObserver ? (
          <OrciaAlertBanner tone="amber" role="status" testId="pack-slot-drawer-observer-banner">
            {labels.observerBlockedHint}
          </OrciaAlertBanner>
        ) : null}

        {!pack || pack.declaredSlots.length === 0 ? (
          <p
            data-testid="pack-slot-drawer-empty"
            className="text-xs text-[var(--orcia-text-secondary)]"
          >
            {labels.noSlotsMessage}
          </p>
        ) : (
          <div className="flex flex-col gap-2.5">
            {pack.declaredSlots.map((slot) => {
              const currentValue = draftSelections[slot.slotKey] ?? "UNBOUND";
              const isUnbound = currentValue === "UNBOUND";
              const isMissingRequired = slot.required && (missingSet.has(slot.slotKey) || isUnbound);
              const isOptionalUnbound = !slot.required && isUnbound;
              const matchingCandidates = candidates.filter(
                (c) =>
                  !slot.scheme ||
                  c.scheme.toLowerCase() === slot.scheme.toLowerCase() ||
                  c.scheme === "",
              );
              const visibleCandidates =
                matchingCandidates.length > 0 ? matchingCandidates : candidates;

              return (
                <div
                  key={slot.slotKey}
                  data-testid={`pack-slot-row-${slot.slotKey}`}
                  data-slot-missing={isMissingRequired ? "true" : "false"}
                  className="flex flex-col gap-2 rounded border p-3"
                  style={{
                    borderColor: isMissingRequired
                      ? "var(--color-stale-crimson)"
                      : "var(--color-border-subtle)",
                    backgroundColor: isMissingRequired
                      ? "var(--color-stale-bg)"
                      : "var(--color-bg-elevated)",
                  }}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <code className="font-mono text-xs font-semibold">{slot.slotKey}</code>
                      <StatusBadge
                        label={slot.required ? labels.requiredBadge : labels.optionalBadge}
                        tone={slot.required ? "cobalt" : "neutral"}
                      />
                    </div>
                    <StatusBadge
                      label={
                        !isUnbound
                          ? labels.readyBadge
                          : slot.required
                            ? labels.missingBadge
                            : labels.optionalUnboundBadge
                      }
                      tone={!isUnbound ? "emerald" : slot.required ? "crimson" : "amber"}
                    />
                  </div>
                  {slot.description ? (
                    <p className="m-0 text-xs text-[var(--orcia-text-secondary)]">
                      {slot.description}
                    </p>
                  ) : null}
                  <label className="orcia-ds-label">
                    <span>{labels.targetSelectLabel}</span>
                    <select
                      data-testid={`pack-slot-select-${slot.slotKey}`}
                      aria-label={`${labels.targetSelectLabel} ${slot.slotKey}`}
                      value={currentValue}
                      disabled={readOnlyObserver || isSaving}
                      onChange={(e) =>
                        setDraftSelections((prev) => ({
                          ...prev,
                          [slot.slotKey]: e.target.value,
                        }))
                      }
                      className="orcia-ds-select"
                    >
                      <option value="UNBOUND">{labels.unboundOptionLabel}</option>
                      {visibleCandidates.map((cand) => {
                        const encoded = encodeCandidateValue(cand.targetKind, cand.targetId);
                        return (
                          <option key={encoded} value={encoded}>
                            {cand.label} ({cand.uri})
                          </option>
                        );
                      })}
                    </select>
                  </label>
                  {isOptionalUnbound ? (
                    <span
                      data-testid={`pack-slot-optional-unbound-${slot.slotKey}`}
                      data-slot-status="optional_unbound"
                      className="font-mono text-[11px] text-[var(--orcia-text-secondary)]"
                    >
                      {labels.optionalUnboundBadge}
                    </span>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}

        <div className="orcia-ds-dialog-footer flex justify-end gap-2 pt-2">
          <button
            type="button"
            data-testid="pack-slot-drawer-cancel-btn"
            onClick={() => onOpenChange(false)}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            {labels.cancelBtn}
          </button>
          <button
            type="submit"
            data-testid="save-pack-slot-bindings-btn"
            disabled={
              readOnlyObserver || isSaving || !pack || pack.declaredSlots.length === 0
            }
            className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
          >
            {isSaving ? labels.savingBtn : labels.saveBtn}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}

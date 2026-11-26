import React from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaAlertBanner } from "./OrciaAlertBanner";
import { OrciaDataCard } from "./OrciaDataCard";
import type { UiWorkspacePackItem, WorkspacePacksPanelLabels } from "./PackUiTypes";
import { StatusBadge } from "./StatusBadge";

export interface WorkspacePacksPanelProps {
  readonly packs: readonly UiWorkspacePackItem[];
  readonly readOnlyObserver?: boolean;
  readonly busySlug?: string | null;
  readonly errorMessage?: string | null;
  readonly labels: WorkspacePacksPanelLabels;
  readonly onToggleActivate: (pack: UiWorkspacePackItem) => void;
  readonly onMovePriority: (packSlug: string, direction: "up" | "down") => void;
  readonly onOpenSlotDrawer: (pack: UiWorkspacePackItem) => void;
}

export function WorkspacePacksPanel({
  packs,
  readOnlyObserver = false,
  busySlug = null,
  errorMessage = null,
  labels,
  onToggleActivate,
  onMovePriority,
  onOpenSlotDrawer,
}: WorkspacePacksPanelProps): React.ReactElement {
  const activePacks = packs
    .filter((p) => p.isActive)
    .sort((a, b) => (a.priorityOrder ?? 999) - (b.priorityOrder ?? 999));

  return (
    <OrciaDataCard
      testId="workspace-packs-panel"
      icon="pack"
      title={labels.cardTitle}
      subtitle={labels.cardSubtitle}
    >
      {errorMessage ? (
        <OrciaAlertBanner tone="crimson" role="alert" testId="workspace-packs-error-alert">
          {errorMessage}
        </OrciaAlertBanner>
      ) : null}

      {readOnlyObserver ? (
        <OrciaAlertBanner tone="amber" role="status" testId="workspace-packs-observer-banner">
          {labels.observerReadOnlyNotice}
        </OrciaAlertBanner>
      ) : null}

      {packs.length === 0 ? (
        <p
          data-testid="workspace-packs-empty"
          className="m-0 text-xs text-[var(--orcia-text-secondary)]"
        >
          {labels.emptyMessage}
        </p>
      ) : (
        <div className="flex flex-col gap-2.5">
          {packs.map((pack) => {
            const isBusy = busySlug === pack.slug;
            const activeIndex = activePacks.findIndex((a) => a.slug === pack.slug);
            const hasRequiredMissing = !pack.readinessOk || pack.missingSlots.length > 0;
            const hasOptionalUnbound =
              !hasRequiredMissing &&
              pack.declaredSlots.some(
                (slot) =>
                  !slot.required &&
                  !pack.slotBindings.some(
                    (b) => b.slotKey === slot.slotKey && b.isEffectiveBound,
                  ),
              );
            const slotStatusLabel = hasRequiredMissing
              ? labels.slotUnboundBadge
              : hasOptionalUnbound
                ? labels.slotOptionalUnboundBadge
                : labels.slotReadyBadge;
            const slotStatusTone = hasRequiredMissing
              ? "crimson"
              : hasOptionalUnbound
                ? "amber"
                : "emerald";

            return (
              <div
                key={pack.bundleId || pack.slug}
                data-testid={`workspace-pack-row-${pack.slug}`}
                className="flex flex-wrap items-center justify-between gap-3 rounded border p-3"
                style={{
                  borderColor: "var(--color-border-subtle)",
                  backgroundColor: "var(--color-bg-elevated)",
                }}
              >
                <div className="flex min-w-0 flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <strong className="text-sm">{pack.name}</strong>
                    <StatusBadge label={`v${pack.version}`} tone="cobalt" monospace />
                    <StatusBadge
                      label={
                        pack.bundleKind === "CUSTOM"
                          ? labels.customOriginBadge
                          : labels.systemOriginBadge
                      }
                      tone="neutral"
                    />
                    <StatusBadge
                      label={pack.isActive ? labels.activeBadge : labels.inactiveBadge}
                      tone={pack.isActive ? "emerald" : "neutral"}
                    />
                    {pack.isActive && pack.priorityOrder !== null ? (
                      <StatusBadge
                        label={`${labels.priorityPrefix}${pack.priorityOrder}`}
                        tone="cobalt"
                        monospace
                      />
                    ) : null}
                    {pack.declaredSlots.length > 0 ? (
                      <StatusBadge label={slotStatusLabel} tone={slotStatusTone} />
                    ) : null}
                  </div>
                  {pack.description ? (
                    <span className="text-xs text-[var(--orcia-text-secondary)]">
                      {pack.description}
                    </span>
                  ) : null}
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {pack.isActive && activePacks.length > 1 ? (
                    <>
                      <button
                        type="button"
                        aria-label={labels.moveUpAriaLabel}
                        data-testid={`workspace-pack-move-up-${pack.slug}`}
                        disabled={readOnlyObserver || isBusy || activeIndex <= 0}
                        onClick={() => onMovePriority(pack.slug, "up")}
                        className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
                      >
                        <OrciaIcon name="arrowUp" size={13} />
                      </button>
                      <button
                        type="button"
                        aria-label={labels.moveDownAriaLabel}
                        data-testid={`workspace-pack-move-down-${pack.slug}`}
                        disabled={
                          readOnlyObserver ||
                          isBusy ||
                          activeIndex < 0 ||
                          activeIndex >= activePacks.length - 1
                        }
                        onClick={() => onMovePriority(pack.slug, "down")}
                        className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
                      >
                        <OrciaIcon name="arrowDown" size={13} />
                      </button>
                    </>
                  ) : null}

                  {pack.declaredSlots.length > 0 ? (
                    <button
                      type="button"
                      data-testid={`workspace-pack-slots-btn-${pack.slug}`}
                      disabled={isBusy}
                      onClick={() => onOpenSlotDrawer(pack)}
                      className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
                    >
                      {labels.configureSlotsBtn}
                    </button>
                  ) : null}

                  <button
                    type="button"
                    data-testid={`workspace-pack-toggle-${pack.slug}`}
                    disabled={readOnlyObserver || isBusy}
                    onClick={() => onToggleActivate(pack)}
                    className={
                      pack.isActive
                        ? "orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
                        : "orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
                    }
                  >
                    {pack.isActive ? labels.deactivateBtn : labels.activateBtn}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </OrciaDataCard>
  );
}

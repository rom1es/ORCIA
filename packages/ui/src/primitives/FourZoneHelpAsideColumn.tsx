import React from "react";
import { OrciaIcon } from "../components/icons";
import type { FourZoneDirectionCShellLabels } from "./FourZoneShellTypes";

export interface FourZoneHelpAsideColumnProps {
  readonly isMobile: boolean;
  readonly labels: Pick<
    FourZoneDirectionCShellLabels,
    "helpColumnTitle" | "helpColumnExpectedTitle" | "helpColumnExpectedBody"
  >;
  readonly helpColumnContent?: React.ReactNode;
  readonly onClose: () => void;
}

export function FourZoneHelpAsideColumn({
  isMobile,
  labels,
  helpColumnContent,
  onClose,
}: FourZoneHelpAsideColumnProps) {
  return (
    <aside
      data-testid="four-zone-contextual-help-column"
      className={
        isMobile
          ? "fixed inset-x-0 top-[52px] bottom-[58px] z-40 overflow-y-auto border-t p-4"
          : "min-h-0 shrink-0 overflow-y-auto border-l p-4"
      }
      style={{
        width: isMobile ? "100%" : "340px",
        maxHeight: isMobile ? undefined : "calc(100vh - 52px)",
        overflowY: "auto",
        position: isMobile ? "fixed" : "sticky",
        top: "52px",
        backgroundColor: "var(--color-bg-surface)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold">{labels.helpColumnTitle}</h2>
        <button
          type="button"
          data-testid="contextual-help-close-btn"
          onClick={onClose}
          className="text-xs"
        >
          <OrciaIcon name="close" />
        </button>
      </div>
      <div
        className="mt-3 rounded border p-3"
        style={{
          backgroundColor: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-subtle)",
        }}
      >
        <h3 className="text-xs font-semibold">{labels.helpColumnExpectedTitle}</h3>
        <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
          {labels.helpColumnExpectedBody}
        </p>
      </div>
      {helpColumnContent && <div className="mt-3">{helpColumnContent}</div>}
    </aside>
  );
}

import React from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import type { UiCatalogExplorerLabels, UiRunLockTripletView } from "./types";

const monoBannerStyle: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "var(--font-size-mono)",
};

const rowWrapStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  flexWrap: "wrap",
  gap: "8px",
};

export interface CatalogExplorerOverridesSectionProps {
  readonly labels: UiCatalogExplorerLabels;
  readonly runLockTriplets: UiRunLockTripletView[];
  readonly bmadImported: boolean;
  readonly onImportBmad: () => void;
}

export function CatalogExplorerOverridesSection({
  labels,
  runLockTriplets,
  bmadImported,
  onImportBmad,
}: CatalogExplorerOverridesSectionProps): React.ReactElement {
  return (
    <>
      <div
        data-testid="four-layer-override-section"
        style={{
          borderTop: "1px solid var(--color-border)",
          paddingTop: "12px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <strong>{labels.overrideSectionTitle}</strong>
        <span style={{ color: "var(--color-muted-foreground)" }}>
          {labels.overrideSectionSubtitle}
        </span>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <StatusBadge label={labels.overrideLayers.base} tone="neutral" monospace />
          <StatusBadge label={labels.overrideLayers.teamParent} tone="cobalt" monospace />
          <StatusBadge label={labels.overrideLayers.teamSub} tone="cobalt" monospace />
          <StatusBadge label={labels.overrideLayers.workspace} tone="emerald" monospace />
          <StatusBadge label={labels.overrideLayers.user} tone="amber" monospace />
        </div>
        <div
          data-testid="run-lock-manifest-preview"
          style={{
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface-bg)",
            border: "1px solid var(--color-border)",
            ...monoBannerStyle,
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: "4px" }}>{labels.runLockTitle}</div>
          {runLockTriplets.map((t) => (
            <div key={t.alias} data-testid={`run-lock-triplet-${t.alias}`}>
              {`${t.alias} -> ${t.uri}@${t.resolvedVersion} (cas/${t.sha256Short})`}
            </div>
          ))}
        </div>
      </div>

      <div
        data-testid="bmad-adapter-section"
        style={{ borderTop: "1px solid var(--color-border)", paddingTop: "12px", ...rowWrapStyle }}
      >
        <strong>{labels.bmadAdapterTitle}</strong>
        <button
          type="button"
          data-testid="bmad-import-trigger-btn"
          onClick={onImportBmad}
          style={{
            padding: "4px 10px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-primary-cobalt)",
            backgroundColor: "var(--color-primary-cobalt)",
            color: "var(--color-primary-foreground)",
            cursor: "pointer",
          }}
        >
          {labels.bmadImportButtonLabel}
        </button>
        {bmadImported && (
          <div
            data-testid="bmad-import-result"
            style={{ width: "100%", ...monoBannerStyle, color: "var(--color-gate-emerald)" }}
          >
            {labels.bmadImportedBanner}
          </div>
        )}
      </div>
    </>
  );
}

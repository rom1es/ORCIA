import { OrciaIcon } from "@orcia/ui";
import React from "react";

export interface WorkspaceSourcesColdStartBannerProps {
  readonly bannerText: string;
  readonly ctaLabel: string;
  readonly onOpenMyAccount: () => void;
}

export function WorkspaceSourcesColdStartBanner({
  bannerText,
  ctaLabel,
  onOpenMyAccount,
}: WorkspaceSourcesColdStartBannerProps): React.ReactElement {
  return (
    <div
      data-testid="rag-passthrough-cold-start-banner"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 14px",
        borderRadius: "var(--radius-sm)",
        backgroundColor: "rgba(59, 130, 246, 0.08)",
        border: "1px solid rgba(59, 130, 246, 0.2)",
        fontSize: "12px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <OrciaIcon name="plug" size={16} />
        <span>{bannerText}</span>
      </div>
      <button
        type="button"
        data-testid="open-my-account-passthrough-cta"
        onClick={onOpenMyAccount}
        className="orcia-ds-btn-secondary"
        style={{ padding: "4px 10px", fontSize: "11px", whiteSpace: "nowrap" }}
      >
        {ctaLabel}
      </button>
    </div>
  );
}

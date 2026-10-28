import { StatusBadge } from "@orcia/ui";
import React from "react";
import { useI18n } from "../../i18n";

export function FinopsFeaturePanel() {
  const { dictionary } = useI18n();
  const copy = dictionary.modulePages.finops;

  return (
    <div className="orcia-bento-card" data-testid="finops-feature-panel">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
        <span>{copy.subtitle}</span>
        <StatusBadge testId="finops-uri-badge" label={copy.uriBadgeExample} tone="cobalt" monospace />
      </div>
    </div>
  );
}

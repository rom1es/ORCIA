import { StatusBadge } from "@orcia/ui";
import React from "react";
import { useI18n } from "../../i18n";

export function InboxFeaturePanel() {
  const { dictionary } = useI18n();
  const copy = dictionary.modulePages.inbox;

  return (
    <div className="orcia-bento-card" data-testid="inbox-feature-panel">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
        <span>{copy.subtitle}</span>
        <StatusBadge testId="inbox-uri-badge" label={copy.uriBadgeExample} tone="cobalt" monospace />
      </div>
    </div>
  );
}

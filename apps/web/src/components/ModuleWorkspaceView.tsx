"use client";

import { HumanLedAnchorCard, StatusBadge, type UiModuleKey } from "@orcia/ui";
import React, { useState } from "react";
import { useI18n } from "../i18n";

export function ModuleWorkspaceView({ moduleKey }: { moduleKey: UiModuleKey }) {
  const { dictionary } = useI18n();
  const pageCopy = dictionary.modulePages[moduleKey];
  const [customAnchorText, setCustomAnchorText] = useState<string | null>(null);
  const anchorText = customAnchorText ?? dictionary.humanAnchor.defaultValue;

  return (
    <div
      data-testid={`module-view-${moduleKey}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <div
        style={{
          backgroundColor: "var(--color-surface-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "8px",
            flexWrap: "wrap",
          }}
        >
          <strong>{pageCopy.subtitle}</strong>
          <StatusBadge
            testId={`module-uri-badge-${moduleKey}`}
            label={pageCopy.uriBadgeExample}
            tone="cobalt"
            monospace
          />
        </div>
        <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>{pageCopy.description}</p>
      </div>

      {moduleKey === "cockpit" && (
        <HumanLedAnchorCard
          sectionKey="architecture-intent"
          sectionTitle={dictionary.humanAnchor.defaultSectionTitle}
          authorName={dictionary.humanAnchor.defaultAuthorName}
          value={anchorText}
          labels={dictionary.humanAnchor}
          onChange={setCustomAnchorText}
        />
      )}
    </div>
  );
}

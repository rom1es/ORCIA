import { StatusBadge } from "@orcia/ui";
import React from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useI18n } from "../../i18n";

export function FinopsFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { runs, llmTiers } = usePlatformSetup();
  const copy = dictionary.modulePages.finops;
  const isFr = locale === "fr";
  const totalUsd = runs.reduce((acc, r) => acc + r.budgetConsumedUsd, 0);

  return (
    <div
      className="orcia-bento-card"
      data-testid="finops-feature-panel"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        <span>{copy.subtitle}</span>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <StatusBadge
            testId="finops-total-usd-badge"
            label={`${totalUsd.toFixed(2)} USD`}
            tone="emerald"
            monospace
          />
          <StatusBadge
            testId="finops-uri-badge"
            label={copy.uriBadgeExample}
            tone="cobalt"
            monospace
          />
        </div>
      </div>

      <p
        data-testid="finops-empty-summary"
        style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
      >
        {isFr
          ? `${runs.length} Run(s) comptabilisé(s) · ${llmTiers.length} palier(s) cognitif(s) configuré(s).`
          : `${runs.length} Run(s) accounted · ${llmTiers.length} cognitive tier(s) configured.`}
      </p>
    </div>
  );
}

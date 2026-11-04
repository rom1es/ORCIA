import { createOrciaApiClient } from "@orcia/api-client";
import { StatusBadge } from "@orcia/ui";
import React, { useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useI18n } from "../../i18n";

const FINOPS_SNAPSHOT_STORAGE_KEY = "orcia.finops.overview.v1";

interface PersistedFinopsSnapshot {
  consolidatedFinopsUsd: number;
  accountedRunsCount: number;
}

function resolveApiBaseUrl(): string {
  const envUrl = (import.meta as unknown as { env?: Record<string, string | undefined> }).env
    ?.VITE_ORCIA_API_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.trim();
  }
  return "http://localhost:8000";
}

function readPersistedFinopsSnapshot(): PersistedFinopsSnapshot | null {
  try {
    const raw = globalThis.localStorage?.getItem(FINOPS_SNAPSHOT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PersistedFinopsSnapshot>;
    if (
      typeof parsed.consolidatedFinopsUsd === "number" &&
      typeof parsed.accountedRunsCount === "number"
    ) {
      return {
        consolidatedFinopsUsd: parsed.consolidatedFinopsUsd,
        accountedRunsCount: parsed.accountedRunsCount,
      };
    }
  } catch {
    // Ignore malformed storage entries
  }
  return null;
}

export function FinopsFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { runs, llmTiers } = usePlatformSetup();
  const [remoteSnapshot, setRemoteSnapshot] = useState<PersistedFinopsSnapshot | null>(() =>
    readPersistedFinopsSnapshot(),
  );

  const apiClient = useMemo(
    () =>
      createOrciaApiClient({
        baseUrl: resolveApiBaseUrl(),
        locale,
      }),
    [locale],
  );

  useEffect(() => {
    let active = true;
    void apiClient
      .getControlCenterOverview({ scopeType: "GLOBAL" })
      .then((overview) => {
        if (!active || typeof overview?.consolidated_finops_usd !== "number") return;
        const accountedRuns =
          (overview.contributor_runs?.length ?? 0) + (overview.observer_runs?.length ?? 0);
        const snap: PersistedFinopsSnapshot = {
          consolidatedFinopsUsd: overview.consolidated_finops_usd,
          accountedRunsCount: accountedRuns,
        };
        setRemoteSnapshot(snap);
        try {
          globalThis.localStorage?.setItem(FINOPS_SNAPSHOT_STORAGE_KEY, JSON.stringify(snap));
        } catch {
          // Ignore storage quota errors
        }
      })
      .catch(() => {
        // Offline / unit test environment without mock fetch
      });
    return () => {
      active = false;
    };
  }, [apiClient]);

  const copy = dictionary.modulePages.finops;
  const isFr = locale === "fr";
  const localTotalUsd = runs.reduce((acc, r) => acc + r.budgetConsumedUsd, 0);
  const totalUsd =
    runs.length > 0 ? localTotalUsd : (remoteSnapshot?.consolidatedFinopsUsd ?? localTotalUsd);
  const accountedRunsCount =
    runs.length > 0 ? runs.length : (remoteSnapshot?.accountedRunsCount ?? runs.length);

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
          ? `${accountedRunsCount} Run(s) comptabilisé(s) · ${llmTiers.length} palier(s) cognitif(s) configuré(s).`
          : `${accountedRunsCount} Run(s) accounted · ${llmTiers.length} cognitive tier(s) configured.`}
      </p>
    </div>
  );
}

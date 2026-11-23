import { OrciaAlertBanner } from "@orcia/ui";
import React from "react";
import { useI18n } from "../../../i18n";
import { ProcessStudioAndPackAuthoringSection } from "../../processes/ProcessStudioAndPackAuthoringSection";
import { PackCardItem } from "./PackCardItem";
import { usePacksRegistryHealthchecks } from "./usePacksRegistryHealthchecks";

export function PacksRegistryPage() {
  const { dictionary, isFr, locale } = useI18n();
  const packsCopy = dictionary.featureAdminCatalogSettings.packsRegistry;
  const {
    packs,
    isLoading,
    selectedWorkspaceId,
    setSelectedWorkspaceId,
    selectedPackId,
    setSelectedPackId,
    statusMessage,
    errorMessage,
    exportedArchiveName,
    workspaceOptions,
    handleRefreshHealthchecks,
    handleExportWorkspaceZip,
    handleExportPackBundleZip,
  } = usePacksRegistryHealthchecks(locale);

  return (
    <section
      data-testid="packs-registry-v2-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div
        className="orcia-bento-card"
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <h2 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>
              {packsCopy.title}
            </h2>
            <span
              className="rounded px-2 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-gate-emerald-bg)",
                color: "var(--color-gate-emerald)",
              }}
            >
              {packsCopy.declarativeBadge}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)" }}>
            {packsCopy.subtitle}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="refresh-pack-connectors-health-btn"
            onClick={handleRefreshHealthchecks}
            disabled={isLoading}
            className="orcia-ds-btn-secondary"
          >
            {packsCopy.checkConnectorsBtn}
          </button>

          <select
            aria-label={packsCopy.selectWorkspaceAriaLabel}
            data-testid="pack-export-workspace-select"
            value={selectedWorkspaceId}
            onChange={(e) => setSelectedWorkspaceId(e.target.value)}
            disabled={workspaceOptions.length === 0}
            className="orcia-ds-select"
          >
            {workspaceOptions.length === 0 ? (
              <option value="">{packsCopy.noWorkspaceOption}</option>
            ) : (
              workspaceOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))
            )}
          </select>

          <button
            type="button"
            data-testid="export-workspace-pack-zip-btn"
            onClick={() => void handleExportWorkspaceZip(selectedPackId)}
            className="orcia-ds-btn-primary"
          >
            {packsCopy.exportWorkspaceBtn}
          </button>
        </div>
      </div>

      {errorMessage ? (
        <OrciaAlertBanner tone="crimson" role="alert" testId="packs-registry-error-banner">
          {errorMessage}
        </OrciaAlertBanner>
      ) : null}

      {statusMessage ? (
        <div
          role="status"
          data-testid="packs-registry-status-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            borderColor: "var(--color-gate-emerald)",
            color: "var(--color-text-primary)",
          }}
        >
          {statusMessage}
          {exportedArchiveName ? (
            <span
              data-testid="exported-pack-zip-filename"
              style={{ marginLeft: "8px", fontFamily: "var(--font-mono)", fontWeight: 700 }}
            >
              [{exportedArchiveName}]
            </span>
          ) : null}
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "16px",
        }}
      >
        {packs.map((pack) => (
          <PackCardItem
            key={pack.id}
            pack={pack}
            isFr={isFr}
            onExportZip={(packId) => {
              setSelectedPackId(packId);
              void handleExportPackBundleZip(packId);
            }}
          />
        ))}
      </div>

      <ProcessStudioAndPackAuthoringSection />
    </section>
  );
}

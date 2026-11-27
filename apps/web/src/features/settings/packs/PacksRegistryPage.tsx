import { OrciaAlertBanner, OrciaPageHeader, StatusBadge } from "@orcia/ui";
import React from "react";
import { useI18n } from "../../../i18n";
import { ProcessStudioAndPackAuthoringSection } from "../../processes/ProcessStudioAndPackAuthoringSection";
import { DeclarativePacksRegistrySection } from "./DeclarativePacksRegistrySection";
import { usePacksRegistryHealthchecks } from "./usePacksRegistryHealthchecks";

export function PacksRegistryPage() {
  const { dictionary, locale } = useI18n();
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
    setStatusMessage,
    setErrorMessage,
    exportedArchiveName,
    workspaceOptions,
    reloadPacksFromServer,
    handleRefreshHealthchecks,
    handleExportWorkspaceZip,
    handleExportPackBundleZip,
  } = usePacksRegistryHealthchecks(locale);

  const alertSlot =
    errorMessage || statusMessage ? (
      <>
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" role="alert" testId="packs-registry-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}
        {statusMessage ? (
          <OrciaAlertBanner tone="emerald" role="status" testId="packs-registry-status-banner">
            <span>{statusMessage}</span>
            {exportedArchiveName ? (
              <span
                data-testid="exported-pack-zip-filename"
                style={{ marginLeft: "8px", fontFamily: "var(--font-mono)", fontWeight: 700 }}
              >
                [{exportedArchiveName}]
              </span>
            ) : null}
          </OrciaAlertBanner>
        ) : null}
      </>
    ) : undefined;

  return (
    <section data-testid="packs-registry-v2-page" className="orcia-ds-page">
      <OrciaPageHeader
        testId="packs-registry-page-header"
        icon="pack"
        title={packsCopy.title}
        subtitle={packsCopy.subtitle}
        contextBadge={<StatusBadge label={packsCopy.declarativeBadge} tone="emerald" />}
        secondaryActions={
          <>
            <button
              type="button"
              data-testid="refresh-pack-connectors-health-btn"
              onClick={handleRefreshHealthchecks}
              disabled={isLoading}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
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
          </>
        }
        primaryAction={
          <button
            type="button"
            data-testid="export-workspace-pack-zip-btn"
            onClick={() => void handleExportWorkspaceZip(selectedPackId)}
            className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
          >
            {packsCopy.exportWorkspaceBtn}
          </button>
        }
        alertSlot={alertSlot}
      />

      <DeclarativePacksRegistrySection
        packs={packs}
        selectedWorkspaceId={selectedWorkspaceId}
        onRefreshPacks={reloadPacksFromServer}
        onExportPackZip={(packId) => {
          setSelectedPackId(packId);
          void handleExportPackBundleZip(packId);
        }}
        onStatusMessage={setStatusMessage}
        onErrorMessage={setErrorMessage}
      />

      <ProcessStudioAndPackAuthoringSection />
    </section>
  );
}

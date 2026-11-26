import {
  createOrciaApiClient,
  type InstalledBusinessPackItemResponse,
} from "@orcia/api-client";
import {
  OrciaAlertBanner,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type {
  ConfiguredOrgUnit,
  ConfiguredPackItem,
} from "../components/platformSetupStore";
import { DICTIONARIES, resolveLocaleForFlag } from "../i18n";
import { DeclarativePacksRegistrySection } from "../features/settings/packs/DeclarativePacksRegistrySection";
import { usePacksRegistryHealthchecks } from "../features/settings/packs/usePacksRegistryHealthchecks";
import { formatRfc9457ErrorToBanner } from "../lib/formatRfc9457ErrorToBanner";
import { SettingsPacksCatalogCard } from "./SettingsPacksCatalogCard";

export interface SettingsPacksSectionProps {
  readonly isFr: boolean;
  readonly packs: readonly ConfiguredPackItem[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly registerPack: (input: ConfiguredPackItem) => void;
  readonly removePack: (packKey: string, scopePath?: string) => void;
  readonly openHelpSection: (sectionId: string) => void;
}

const selectStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function SettingsPacksSection({
  isFr,
  packs,
  orgUnits,
  workspaces,
  registerPack,
  removePack,
}: SettingsPacksSectionProps) {
  const locale = resolveLocaleForFlag(isFr);
  const copy = DICTIONARIES[locale].routesAndWizards.settingsPacks;
  const [installedPacks, setInstalledPacks] = useState<
    readonly InstalledBusinessPackItemResponse[]
  >([]);
  const [selectedScopePath, setSelectedScopePath] = useState<string>("GLOBAL");
  const [packsLoadError, setPacksLoadError] = useState<string | null>(null);
  const registry = usePacksRegistryHealthchecks(locale);

  useEffect(() => {
    let cancelled = false;
    const client = createOrciaApiClient({ baseUrl: "", locale });
    void client
      .listInstalledBusinessPacks()
      .then((res) => {
        if (!cancelled && Array.isArray(res.packs) && res.packs.length > 0) {
          setInstalledPacks(res.packs);
          setPacksLoadError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setPacksLoadError(
            formatRfc9457ErrorToBanner(err, locale, copy.catalogErrorContext).fullText,
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [locale, copy.catalogErrorContext]);

  const scopeOptions: readonly { readonly value: string; readonly label: string }[] = [
    { value: "GLOBAL", label: copy.entirePlatformLabel },
    ...orgUnits.map((unit) => ({
      value: unit.slug,
      label: `${unit.level === "BU" ? copy.divisionLabel : copy.teamLabel} · ${unit.name}`,
    })),
    ...workspaces
      .filter((ws) => !orgUnits.some((u) => u.name === ws.name))
      .map((ws) => ({
        value: ws.workspaceId,
        label: `${copy.workspaceLabel} · ${ws.name}`,
      })),
  ];

  const formatScopeLabel = (scopePath: string): string => {
    if (scopePath === "GLOBAL") return copy.entirePlatformLabel;
    const foundOption = scopeOptions.find((opt) => opt.value === scopePath);
    return foundOption ? foundOption.label : scopePath;
  };

  const selectedScopeLabel = formatScopeLabel(selectedScopePath);

  return (
    <section
      data-testid="settings-packs-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {packsLoadError && (
        <OrciaAlertBanner tone="crimson" role="alert" testId="settings-packs-error-banner">
          {packsLoadError}
        </OrciaAlertBanner>
      )}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <h2 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>{copy.catalogTitle}</h2>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px" }}>
          <label
            htmlFor="settings-pack-scope-select"
            style={{ fontSize: "13px", fontWeight: 600 }}
          >
            {copy.targetScopeLabel}
          </label>
          <select
            id="settings-pack-scope-select"
            data-testid="pack-scope-input"
            value={selectedScopePath}
            title={scopeOptions.find((o) => o.value === selectedScopePath)?.label ?? selectedScopePath}
            onChange={(e) => setSelectedScopePath(e.target.value)}
            style={{ ...selectStyle, minWidth: "220px" }}
          >
            {scopeOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div
        data-testid="installed-packs-catalog-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "12px",
        }}
      >
        {installedPacks.map((item) => (
          <SettingsPacksCatalogCard
            key={item.pack_key}
            item={item}
            locale={locale}
            copy={copy}
            packs={packs}
            selectedScopePath={selectedScopePath}
            selectedScopeLabel={selectedScopeLabel}
            formatScopeLabel={formatScopeLabel}
            registerPack={registerPack}
            removePack={removePack}
          />
        ))}
      </div>

      {packs.length === 0 && (
        <p
          data-testid="packs-empty-state"
          style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
        >
          {copy.emptyState}
        </p>
      )}

      <DeclarativePacksRegistrySection
        packs={registry.packs}
        selectedWorkspaceId={registry.selectedWorkspaceId}
        onSelectedWorkspaceChange={registry.setSelectedWorkspaceId}
        onRefreshPacks={registry.reloadPacksFromServer}
        onExportPackZip={(packId) => {
          registry.setSelectedPackId(packId);
          void registry.handleExportPackBundleZip(packId);
        }}
        onStatusMessage={registry.setStatusMessage}
        onErrorMessage={registry.setErrorMessage}
        statusMessage={registry.statusMessage}
        errorMessage={registry.errorMessage}
      />
    </section>
  );
}

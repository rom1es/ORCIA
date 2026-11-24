import type { InstalledBusinessPackItemResponse } from "@orcia/api-client";
import { StatusBadge } from "@orcia/ui";
import React from "react";
import type { ConfiguredPackItem } from "../components/platformSetupStore";
import { formatI18nTemplate, type SupportedWebLocale } from "../i18n";
import type { RoutesAndWizardsDictionary } from "../i18n/locales/routes_and_wizards_labels";

type SettingsPacksCopy = RoutesAndWizardsDictionary["settingsPacks"];

const primaryBtnStyle: React.CSSProperties = {
  padding: "7px 14px",
  borderRadius: "var(--radius-sm)",
  border: "none",
  backgroundColor: "var(--color-primary-cobalt)",
  color: "var(--color-primary-foreground)",
  fontWeight: 600,
  cursor: "pointer",
};

const secondaryBtnStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
};

const PACK_TITLE_FIELD: Readonly<Record<SupportedWebLocale, "title" | "title_en">> = {
  fr: "title",
  en: "title_en",
};

const PACK_DESC_FIELD: Readonly<Record<SupportedWebLocale, "description" | "description_en">> = {
  fr: "description",
  en: "description_en",
};

export interface SettingsPacksCatalogCardProps {
  readonly item: InstalledBusinessPackItemResponse;
  readonly locale: SupportedWebLocale;
  readonly copy: SettingsPacksCopy;
  readonly packs: readonly ConfiguredPackItem[];
  readonly selectedScopePath: string;
  readonly selectedScopeLabel: string;
  readonly formatScopeLabel: (scopePath: string) => string;
  readonly registerPack: (input: ConfiguredPackItem) => void;
  readonly removePack: (packKey: string, scopePath?: string) => void;
}

export function SettingsPacksCatalogCard({
  item,
  locale,
  copy,
  packs,
  selectedScopePath,
  selectedScopeLabel,
  formatScopeLabel,
  registerPack,
  removePack,
}: SettingsPacksCatalogCardProps): React.ReactElement {
  const activeScopesForPack = packs.filter((p) => p.packKey === item.pack_key);
  const isActiveGlobally = activeScopesForPack.some((p) => p.scopePath === "GLOBAL");
  const isActiveOnSelectedScope =
    isActiveGlobally || activeScopesForPack.some((p) => p.scopePath === selectedScopePath);
  const displayTitle = item[PACK_TITLE_FIELD[locale]];
  const displayDesc = item[PACK_DESC_FIELD[locale]];

  return (
    <article
      data-testid={`installed-pack-card-${item.pack_key}`}
      style={{
        padding: "14px",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--color-border)",
        backgroundColor: "var(--color-surface-card)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: "10px",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: "8px",
          }}
        >
          <strong style={{ fontSize: "14px" }}>{displayTitle}</strong>
          <StatusBadge label={`v${item.version}`} tone="cobalt" monospace />
        </div>
        <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
          {displayDesc}
        </span>

        {activeScopesForPack.length > 0 && (
          <div
            data-testid={`pack-card-active-scopes-${item.pack_key}`}
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "6px",
              paddingTop: "4px",
            }}
          >
            {activeScopesForPack.map((activeEntry) => (
              <StatusBadge
                key={`${activeEntry.packKey}:${activeEntry.scopePath}`}
                label={`${copy.activeBadgePrefix} · ${formatScopeLabel(activeEntry.scopePath)}`}
                tone="emerald"
              />
            ))}
            {isActiveGlobally && selectedScopePath !== "GLOBAL" && (
              <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                {copy.globalAlreadyCoveredNote}
              </span>
            )}
          </div>
        )}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
          paddingTop: "6px",
          borderTop: "1px solid var(--color-border)",
        }}
      >
        <span style={{ fontSize: "12px", fontWeight: 600 }}>
          {formatI18nTemplate(copy.countsTemplate, {
            workflowsCount: item.workflows_count,
            agentsCount: item.agents_count,
          })}
        </span>

        {isActiveOnSelectedScope ? (
          <button
            type="button"
            data-testid={`deactivate-pack-btn-${item.pack_key}`}
            onClick={() =>
              removePack(item.pack_key, isActiveGlobally ? "GLOBAL" : selectedScopePath)
            }
            style={secondaryBtnStyle}
          >
            {isActiveGlobally && selectedScopePath !== "GLOBAL"
              ? copy.disableGlobalCta
              : copy.disableScopeCta}
          </button>
        ) : (
          <button
            type="button"
            data-testid={`activate-pack-btn-${item.pack_key}`}
            onClick={() =>
              registerPack({
                packKey: item.pack_key,
                version: item.version,
                scopePath: selectedScopePath,
                status: "PUBLISHED",
              })
            }
            style={primaryBtnStyle}
          >
            {formatI18nTemplate(copy.enableOnScopeTemplate, { scopeLabel: selectedScopeLabel })}
          </button>
        )}
      </div>
    </article>
  );
}

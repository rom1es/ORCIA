import React, { useState } from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import { FederatedUriBadge } from "./FederatedUriBadge";
import type {
  UiCatalogExplorerItemView,
  UiCatalogExplorerLabels,
  UiCatalogVisibilityScope,
  UiFederatedScheme,
  UiPersonaKey,
  UiRunLockTripletView,
} from "./types";

const PROMOTION_ORDER: UiCatalogVisibilityScope[] = [
  "DRAFT",
  "SHARED_WORKSPACE",
  "SHARED_TEAM",
  "SHARED_BU",
  "PENDING_APPROVAL",
  "PUBLISHED_ORG",
];

const SCHEMES: Array<UiFederatedScheme | "ALL"> = [
  "ALL",
  "git",
  "nexus",
  "db",
  "confluence",
  "jira",
  "orcia",
];

export interface CatalogExplorerPanelProps {
  activePersona: UiPersonaKey;
  items: UiCatalogExplorerItemView[];
  runLockTriplets: UiRunLockTripletView[];
  labels: UiCatalogExplorerLabels;
}

function nextScopeFor(current: UiCatalogVisibilityScope): UiCatalogVisibilityScope | null {
  const idx = PROMOTION_ORDER.indexOf(current);
  return idx >= 0 && idx < PROMOTION_ORDER.length - 1 ? (PROMOTION_ORDER[idx + 1] ?? null) : null;
}

export function CatalogExplorerPanel({
  activePersona,
  items,
  runLockTriplets,
  labels,
}: CatalogExplorerPanelProps) {
  const [selectedScheme, setSelectedScheme] = useState<UiFederatedScheme | "ALL">("ALL");
  const [promotedScopes, setPromotedScopes] = useState<Record<string, UiCatalogVisibilityScope>>({});
  const [promotionBanner, setPromotionBanner] = useState<Record<string, string>>({});
  const [casBanner, setCasBanner] = useState<Record<string, string>>({});
  const [bmadImported, setBmadImported] = useState(false);

  const visibleItems = items.filter((item) =>
    selectedScheme === "ALL" ? true : item.scheme === selectedScheme,
  );

  function canPromoteItem(item: UiCatalogExplorerItemView): boolean {
    return (
      activePersona === "karim" ||
      activePersona === "claire" ||
      item.grantedPermissions.includes("EDIT") ||
      item.grantedPermissions.includes("ADMIN")
    );
  }

  function handlePromote(item: UiCatalogExplorerItemView) {
    const currentScope = promotedScopes[item.resourceId] ?? item.visibilityScope;
    const nextScope = nextScopeFor(currentScope);
    if (!nextScope) return;
    const isObserverBlocked =
      !canPromoteItem(item) ||
      (activePersona === "claire" && nextScope !== "PUBLISHED_ORG") ||
      (nextScope === "PUBLISHED_ORG" && activePersona !== "karim" && activePersona !== "claire");
    if (isObserverBlocked) {
      setPromotionBanner((prev) => ({
        ...prev,
        [item.resourceId]: labels.promoteDeniedObserverBanner,
      }));
      return;
    }
    setPromotedScopes((prev) => ({ ...prev, [item.resourceId]: nextScope }));
    setPromotionBanner((prev) => ({
      ...prev,
      [item.resourceId]: `${labels.promotedBannerPrefix} : ${currentScope} -> ${nextScope}`,
    }));
  }

  function handleResolveCas(item: UiCatalogExplorerItemView) {
    setCasBanner((prev) => ({
      ...prev,
      [item.resourceId]: `${labels.casResolvedBannerPrefix} : ${item.casKey} (cache_hit=true, 0.4ms < 50ms)`,
    }));
  }

  return (
    <section
      data-testid="catalog-explorer-panel"
      style={{
        backgroundColor: "var(--color-surface-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "16px" }}>{labels.panelTitle}</h2>
          <p style={{ margin: "4px 0 0 0", color: "var(--color-muted-foreground)" }}>
            {labels.panelSubtitle}
          </p>
        </div>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {SCHEMES.map((schemeKey) => {
            const active = selectedScheme === schemeKey;
            return (
              <button
                key={schemeKey}
                type="button"
                data-testid={`catalog-scheme-filter-${schemeKey}`}
                onClick={() => setSelectedScheme(schemeKey)}
                style={{
                  padding: "4px 10px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: active
                    ? "var(--color-primary-cobalt)"
                    : "var(--color-surface-bg)",
                  color: active ? "var(--color-primary-foreground)" : "var(--color-foreground)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--font-size-mono)",
                  cursor: "pointer",
                }}
              >
                {schemeKey === "ALL" ? labels.filterAllSchemesLabel : `${schemeKey}://`}
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ display: "grid", gap: "12px" }}>
        {visibleItems.map((item) => {
          const currentScope = promotedScopes[item.resourceId] ?? item.visibilityScope;
          const nextScope = nextScopeFor(currentScope);
          const canMutateScope = canPromoteItem(item);
          return (
            <div
              key={item.resourceId}
              data-testid={`catalog-item-card-${item.resourceId}`}
              style={{
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "12px",
                backgroundColor: "var(--color-surface-bg)",
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
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <strong>{item.title}</strong>
                <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                  <StatusBadge
                    testId={`catalog-scope-badge-${item.resourceId}`}
                    label={currentScope}
                    tone={currentScope === "PUBLISHED_ORG" ? "emerald" : "cobalt"}
                    monospace
                  />
                  <StatusBadge label={item.sourceFormat} tone="neutral" monospace />
                </div>
              </div>

              <FederatedUriBadge
                testId={`uri-badge-${item.resourceId}`}
                uri={item.uri}
                scheme={item.scheme}
                sha256Short={item.sha256Short}
                grantedPermissions={item.grantedPermissions}
                sourceMasked={item.sourceMasked}
                maskedSourceLabel={labels.maskedSourceBadgeLabel}
                openSourceLabel={labels.openSourceBadgeLabel}
              />

              <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>
                {item.description}
              </p>

              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                <button
                  type="button"
                  data-testid={`resolve-cas-btn-${item.resourceId}`}
                  onClick={() => handleResolveCas(item)}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-primary-cobalt)",
                    backgroundColor: "var(--color-surface-card)",
                    color: "var(--color-primary-cobalt)",
                    cursor: "pointer",
                  }}
                >
                  {labels.resolveCasButtonLabel}
                </button>
                {nextScope && (
                  <button
                    type="button"
                    data-testid={`promote-btn-${item.resourceId}`}
                    disabled={!canMutateScope}
                    onClick={() => handlePromote(item)}
                    style={{
                      padding: "4px 10px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-gate-emerald)",
                      backgroundColor: "var(--color-gate-emerald-bg)",
                      color: "var(--color-gate-emerald)",
                      cursor: canMutateScope ? "pointer" : "not-allowed",
                      opacity: canMutateScope ? 1 : 0.6,
                    }}
                  >
                    {`${labels.promoteScopeButtonLabel} -> ${nextScope}`}
                  </button>
                )}
              </div>

              {casBanner[item.resourceId] && (
                <div
                  data-testid={`resolve-cas-result-${item.resourceId}`}
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--font-size-mono)",
                    color: "var(--color-gate-emerald)",
                  }}
                >
                  {casBanner[item.resourceId]}
                </div>
              )}

              {promotionBanner[item.resourceId] && (
                <div
                  data-testid={`promote-result-${item.resourceId}`}
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--font-size-mono)",
                    color: promotionBanner[item.resourceId]?.includes("403")
                      ? "var(--color-stale-crimson)"
                      : "var(--color-gate-emerald)",
                  }}
                >
                  {promotionBanner[item.resourceId]}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div
        data-testid="four-layer-override-section"
        style={{
          borderTop: "1px solid var(--color-border)",
          paddingTop: "12px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <strong>{labels.overrideSectionTitle}</strong>
        <span style={{ color: "var(--color-muted-foreground)" }}>
          {labels.overrideSectionSubtitle}
        </span>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <StatusBadge label={labels.overrideLayers.base} tone="neutral" monospace />
          <StatusBadge label={labels.overrideLayers.teamParent} tone="cobalt" monospace />
          <StatusBadge label={labels.overrideLayers.teamSub} tone="cobalt" monospace />
          <StatusBadge label={labels.overrideLayers.workspace} tone="emerald" monospace />
          <StatusBadge label={labels.overrideLayers.user} tone="amber" monospace />
        </div>
        <div
          data-testid="run-lock-manifest-preview"
          style={{
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface-bg)",
            border: "1px solid var(--color-border)",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: "4px" }}>{labels.runLockTitle}</div>
          {runLockTriplets.map((t) => (
            <div key={t.alias} data-testid={`run-lock-triplet-${t.alias}`}>
              {`${t.alias} -> ${t.uri}@${t.resolvedVersion} (cas/${t.sha256Short})`}
            </div>
          ))}
        </div>
      </div>

      <div
        data-testid="bmad-adapter-section"
        style={{
          borderTop: "1px solid var(--color-border)",
          paddingTop: "12px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <strong>{labels.bmadAdapterTitle}</strong>
        <button
          type="button"
          data-testid="bmad-import-trigger-btn"
          onClick={() => setBmadImported(true)}
          style={{
            padding: "4px 10px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-primary-cobalt)",
            backgroundColor: "var(--color-primary-cobalt)",
            color: "var(--color-primary-foreground)",
            cursor: "pointer",
          }}
        >
          {labels.bmadImportButtonLabel}
        </button>
        {bmadImported && (
          <div
            data-testid="bmad-import-result"
            style={{
              width: "100%",
              fontFamily: "var(--font-mono)",
              fontSize: "var(--font-size-mono)",
              color: "var(--color-gate-emerald)",
            }}
          >
            {labels.bmadImportedBanner}
          </div>
        )}
      </div>
    </section>
  );
}

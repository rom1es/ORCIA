import {
  createOrciaApiClient,
  type InstalledBusinessPackItemResponse,
} from "@orcia/api-client";
import {
  ContextualInfoTriggerButton,
  StatusBadge,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type {
  ConfiguredOrgUnit,
  ConfiguredPackItem,
} from "../components/platformSetupStore";

export const BUILTIN_INSTALLED_BUSINESS_PACKS: readonly InstalledBusinessPackItemResponse[] = [
  {
    pack_key: "orcia-pack-sdlc",
    pack_slug: "sdlc",
    title: "Ingénierie Logicielle & Cycle de Vie Produit",
    title_en: "Software Engineering & Product Lifecycle",
    version: "0.1.0",
    domain_name: "INGÉNIERIE LOGICIELLE & PRODUIT",
    description:
      "Connecteurs Git, Jira, Confluence et Nexus, processus guidés de spécification et réalisation, revues croisées et suivi de cohérence documentaire.",
    description_en:
      "Git, Jira, Confluence, and Nexus connectors, guided specification and delivery processes, cross-checked reviews, and documentation consistency tracking.",
    workflows_count: 4,
    agents_count: 6,
    is_system_pack: true,
  },
  {
    pack_key: "orcia-pack-builder",
    pack_slug: "pack-builder",
    title: "Atelier de Création & Gouvernance de Packs Métiers",
    title_en: "Business Pack Authoring & Governance Studio",
    version: "0.1.0",
    domain_name: "GOUVERNANCE & MÉTHODOLOGIE",
    description:
      "Conception guidée de nouveaux Packs métiers, simulation d'impact avant évolution, certification des règles métiers et génération de fiches d'aide.",
    description_en:
      "Guided creation of new Business Packs, impact simulation before evolution, business rule certification, and help article generation.",
    workflows_count: 5,
    agents_count: 4,
    is_system_pack: true,
  },
];

export interface SettingsPacksSectionProps {
  readonly isFr: boolean;
  readonly packs: readonly ConfiguredPackItem[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly registerPack: (input: ConfiguredPackItem) => void;
  readonly removePack: (packKey: string, scopePath?: string) => void;
  readonly openHelpSection: (sectionId: string) => void;
}

export function SettingsPacksSection({
  isFr,
  packs,
  orgUnits,
  workspaces,
  registerPack,
  removePack,
  openHelpSection,
}: SettingsPacksSectionProps) {
  const [installedPacks, setInstalledPacks] = useState<
    readonly InstalledBusinessPackItemResponse[]
  >(BUILTIN_INSTALLED_BUSINESS_PACKS);
  const [selectedScopePath, setSelectedScopePath] = useState<string>("GLOBAL");

  useEffect(() => {
    let cancelled = false;
    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (isJsdom) {
      return;
    }
    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .listInstalledBusinessPacks()
      .then((res) => {
        if (!cancelled && Array.isArray(res.packs) && res.packs.length > 0) {
          setInstalledPacks(res.packs);
        }
      })
      .catch(() => {
        // Keep built-in installed packs catalog when offline
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const scopeOptions: readonly { readonly value: string; readonly label: string }[] = [
    {
      value: "GLOBAL",
      label: isFr ? "Plateforme entière" : "Entire Platform",
    },
    ...orgUnits.map((unit) => ({
      value: unit.slug,
      label: `${unit.level === "BU" ? (isFr ? "Direction" : "Division") : isFr ? "Espace" : "Team"} · ${unit.name}`,
    })),
    ...workspaces
      .filter((ws) => !orgUnits.some((u) => u.name === ws.name))
      .map((ws) => ({
        value: ws.workspaceId,
        label: `${isFr ? "Espace" : "Workspace"} · ${ws.name}`,
      })),
  ];

  const formatScopeLabel = (scopePath: string): string => {
    if (scopePath === "GLOBAL") {
      return isFr ? "Plateforme entière" : "Entire Platform";
    }
    const foundOption = scopeOptions.find((opt) => opt.value === scopePath);
    return foundOption ? foundOption.label : scopePath;
  };

  const selectedScopeLabel = formatScopeLabel(selectedScopePath);

  const selectStyle: React.CSSProperties = {
    padding: "7px 10px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--color-border)",
    backgroundColor: "var(--color-surface-card)",
    color: "var(--color-foreground)",
  };

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

  return (
    <section
      data-testid="settings-packs-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
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
          <h2 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>
            {isFr
              ? "Catalogue des Packs Métiers disponibles"
              : "Available Business Packs Catalog"}
          </h2>
          <ContextualInfoTriggerButton
            sectionId="packs-overview"
            label={
              isFr
                ? "Aide sur les Packs métiers prêts à l'emploi"
                : "Help on ready-to-use Business Packs"
            }
            onOpenHelpSection={openHelpSection}
          />
        </div>

        <div
          style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px" }}
        >
          <label
            htmlFor="settings-pack-scope-select"
            style={{ fontSize: "13px", fontWeight: 600 }}
          >
            {isFr ? "Périmètre cible :" : "Target scope:"}
          </label>
          <select
            id="settings-pack-scope-select"
            data-testid="pack-scope-input"
            value={selectedScopePath}
            onChange={(e) => setSelectedScopePath(e.target.value)}
            style={selectStyle}
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
        {installedPacks.map((item) => {
          const activeScopesForPack = packs.filter((p) => p.packKey === item.pack_key);
          const isActiveGlobally = activeScopesForPack.some(
            (p) => p.scopePath === "GLOBAL",
          );
          const isActiveOnSelectedScope =
            isActiveGlobally ||
            activeScopesForPack.some((p) => p.scopePath === selectedScopePath);
          const displayTitle = isFr ? item.title : item.title_en;
          const displayDesc = isFr ? item.description : item.description_en;

          return (
            <article
              key={item.pack_key}
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
                <span
                  style={{
                    fontSize: "12px",
                    color: "var(--color-muted-foreground)",
                  }}
                >
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
                        label={`${isFr ? "Actif" : "Active"} · ${formatScopeLabel(activeEntry.scopePath)}`}
                        tone="emerald"
                      />
                    ))}
                    {isActiveGlobally && selectedScopePath !== "GLOBAL" && (
                      <span
                        style={{
                          fontSize: "11px",
                          color: "var(--color-muted-foreground)",
                        }}
                      >
                        {isFr
                          ? "(couvre déjà toutes les Directions et Espaces)"
                          : "(already covers all Divisions and Workspaces)"}
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
                  {isFr
                    ? `${item.workflows_count} processus · ${item.agents_count} agents spécialisés`
                    : `${item.workflows_count} processes · ${item.agents_count} specialized agents`}
                </span>

                {isActiveOnSelectedScope ? (
                  <button
                    type="button"
                    data-testid={`deactivate-pack-btn-${item.pack_key}`}
                    onClick={() =>
                      removePack(
                        item.pack_key,
                        isActiveGlobally ? "GLOBAL" : selectedScopePath,
                      )
                    }
                    style={secondaryBtnStyle}
                  >
                    {isActiveGlobally && selectedScopePath !== "GLOBAL"
                      ? isFr
                        ? "Désactiver (Plateforme entière)"
                        : "Disable (Entire Platform)"
                      : isFr
                        ? "Désactiver sur ce périmètre"
                        : "Disable on this scope"}
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
                    {isFr
                      ? `Activer sur : ${selectedScopeLabel}`
                      : `Enable on: ${selectedScopeLabel}`}
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {packs.length === 0 ? (
        <p
          data-testid="packs-empty-state"
          style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
        >
          {isFr
            ? "Aucun Pack métier activé pour le moment. Choisissez un périmètre cible et cliquez sur le bouton d'activation d'une carte."
            : "No Business Pack enabled yet. Select a target scope and click a card's activation button."}
        </p>
      ) : (
        <div style={{ display: "grid", gap: "8px" }}>
          {packs.map((p) => {
            const matchedMeta = installedPacks.find((item) => item.pack_key === p.packKey);
            const displayTitle = matchedMeta
              ? isFr
                ? matchedMeta.title
                : matchedMeta.title_en
              : p.packKey;
            return (
              <div
                key={`${p.packKey}@${p.version}:${p.scopePath}`}
                data-testid={`pack-row-${p.packKey}`}
                style={{
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <strong>{displayTitle}</strong>
                  <StatusBadge label={`v${p.version}`} tone="cobalt" monospace />
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <StatusBadge
                    label={`${isFr ? "Actif" : "Active"} · ${formatScopeLabel(p.scopePath)}`}
                    tone="emerald"
                  />
                  <button
                    type="button"
                    data-testid={`remove-active-pack-btn-${p.packKey}-${p.scopePath}`}
                    onClick={() => removePack(p.packKey, p.scopePath)}
                    style={secondaryBtnStyle}
                  >
                    {isFr ? "Désactiver" : "Disable"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

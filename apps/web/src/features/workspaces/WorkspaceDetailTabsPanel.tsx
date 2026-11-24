import {
  OrciaIcon,
  type ControlCenterDatasourceItem,
  type ControlCenterWorkspaceGovItem,
  type UiOntologyConceptView,
  type UiOntologyLevel,
} from "@orcia/ui";
import React, { useState } from "react";
import type {
  ConfiguredOrgUnit,
  PlatformSetupContextValue,
} from "../../components/platformSetupStore";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../i18n";
import { WorkspaceGlossaryAndOntologyTab } from "./WorkspaceGlossaryAndOntologyTab";
import { WorkspaceSourcesRagTab } from "./WorkspaceSourcesRagTab";

export type WorkspaceDetailTabKey = "SOURCES" | "GLOSSARY" | "MEMBERS";

export interface WorkspaceDetailTabsPanelProps {
  readonly isFr: boolean;
  readonly initialTab?: string;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem;
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly onRegisterDatasource: PlatformSetupContextValue["registerDatasource"];
  readonly onAddOntologyConcept: (input: UiOntologyConceptView) => void;
  readonly onPromoteOntologyConcept: (
    conceptKey: string,
    targetLevel: UiOntologyLevel,
    targetScopeId?: string,
  ) => void;
  readonly onFeedback: (message: string) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function WorkspaceDetailTabsPanel({
  isFr,
  initialTab,
  activeWorkspace,
  datasources,
  ontologyConcepts,
  orgUnits,
  openHelpSection,
  onRegisterDatasource,
  onAddOntologyConcept,
  onPromoteOntologyConcept,
  onFeedback,
}: WorkspaceDetailTabsPanelProps): React.ReactElement {
  const tabsCopy = resolveDictionaryForFlag(isFr).featureWorkspaces.detailTabs;
  const [activeDetailTab, setActiveDetailTab] = useState<WorkspaceDetailTabKey>(
    (initialTab as WorkspaceDetailTabKey) || "SOURCES",
  );
  const [instructionsByWs, setInstructionsByWs] = useState<Record<string, string>>({});
  const [instructionsSavedWsId, setInstructionsSavedWsId] = useState<string | null>(null);

  return (
    <section
      data-testid="workspace-detail-tabs-panel"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
          borderBottom: "1px solid var(--color-border-subtle)",
          paddingBottom: "10px",
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: "15px" }}>
            {formatI18nTemplate(tabsCopy.selectedWorkspaceTemplate, {
              name: activeWorkspace.name,
            })}
          </h3>
          <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            {tabsCopy.subtitle}
          </span>
        </div>

        <nav role="tablist" className="orcia-ds-tabs">
          <button
            type="button"
            role="tab"
            data-testid="workspace-detail-tab-sources"
            aria-selected={activeDetailTab === "SOURCES"}
            onClick={() => setActiveDetailTab("SOURCES")}
            className="orcia-ds-tab"
          >
            <OrciaIcon name="books" /> {tabsCopy.tabSources}
          </button>
          <button
            type="button"
            role="tab"
            data-testid="workspace-detail-tab-glossary"
            aria-selected={activeDetailTab === "GLOSSARY"}
            onClick={() => setActiveDetailTab("GLOSSARY")}
            className="orcia-ds-tab"
          >
            <OrciaIcon name="bookOpen" /> {tabsCopy.tabGlossary}
          </button>
          <button
            type="button"
            role="tab"
            data-testid="workspace-detail-tab-members"
            aria-selected={activeDetailTab === "MEMBERS"}
            onClick={() => setActiveDetailTab("MEMBERS")}
            className="orcia-ds-tab"
          >
            <OrciaIcon name="team" /> {tabsCopy.tabMembers}
          </button>
        </nav>
      </div>

      {activeDetailTab === "SOURCES" && (
        <WorkspaceSourcesRagTab
          isFr={isFr}
          activeWorkspace={activeWorkspace}
          fallbackDatasources={datasources}
          openHelpSection={openHelpSection}
          onRegisterDatasource={onRegisterDatasource}
          onFeedback={onFeedback}
        />
      )}

      {activeDetailTab === "GLOSSARY" && (
        <WorkspaceGlossaryAndOntologyTab
          isFr={isFr}
          selectedWorkspace={activeWorkspace}
          orgUnits={orgUnits}
          ontologyConcepts={ontologyConcepts}
          openHelpSection={openHelpSection}
          onAddConcept={(concept) => {
            onAddOntologyConcept(concept);
            onFeedback(
              formatI18nTemplate(tabsCopy.termAddedTemplate, { term: concept.canonicalTerm }),
            );
          }}
          onPromoteConcept={(conceptKey, targetLevel, targetScopeId) => {
            onPromoteOntologyConcept(conceptKey, targetLevel, targetScopeId);
            onFeedback(tabsCopy.termPromoted);
          }}
        />
      )}

      {activeDetailTab === "MEMBERS" && (
        <div
          data-testid="workspace-detail-members-content"
          style={{ display: "flex", flexDirection: "column", gap: "10px" }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
            <div>
              <strong style={{ fontSize: "13px" }}>
                {formatI18nTemplate(tabsCopy.ownerTeamTemplate, {
                  owner: activeWorkspace.ownerOrgUnitName ?? tabsCopy.defaultPlatformOwnerName,
                })}
              </strong>
              <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "var(--color-muted-foreground)" }}>
                {tabsCopy.instructionsHint}
              </p>
            </div>
            {instructionsSavedWsId === activeWorkspace.workspaceId && (
              <span
                data-testid="workspace-instructions-saved-badge"
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "3px 8px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-action-primary-subtle)",
                  color: "var(--color-status-success)",
                }}
              >
                {tabsCopy.savedBadge}
              </span>
            )}
          </div>
          <textarea
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="workspace-instructions-textarea"
            rows={3}
            value={instructionsByWs[activeWorkspace.workspaceId] ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              setInstructionsByWs((prev) => ({ ...prev, [activeWorkspace.workspaceId]: val }));
              setInstructionsSavedWsId(activeWorkspace.workspaceId);
            }}
            placeholder={tabsCopy.instructionsPlaceholder}
            style={{ ...inputStyle, width: "100%", fontFamily: "var(--font-sans)" }}
          />
        </div>
      )}
    </section>
  );
}

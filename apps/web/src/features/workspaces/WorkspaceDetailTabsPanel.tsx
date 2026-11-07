import {
  ContextualInfoTriggerButton,
  DisabledButtonAlertIndicator,
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
import { WorkspaceGlossaryAndOntologyTab } from "./WorkspaceGlossaryAndOntologyTab";

export type WorkspaceDetailTabKey = "SOURCES" | "GLOSSARY" | "MEMBERS";

export interface WorkspaceDetailTabsPanelProps {
  readonly isFr: boolean;
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
  const [activeDetailTab, setActiveDetailTab] = useState<WorkspaceDetailTabKey>("SOURCES");
  const [dsAlias, setDsAlias] = useState("");
  const [dsScheme, setDsScheme] = useState<"git" | "confluence" | "jira" | "db">("git");
  const [dsUri, setDsUri] = useState("");
  const [dsIdentity, setDsIdentity] = useState<"passthrough" | "service_account">("passthrough");
  const [instructionsByWs, setInstructionsByWs] = useState<Record<string, string>>({});
  const [instructionsSavedWsId, setInstructionsSavedWsId] = useState<string | null>(null);

  const isDsSubmitDisabled = !dsAlias.trim() || !dsUri.trim();
  const dsSubmitDisabledReason = isFr
    ? "Renseignez le nom et l'adresse (URL/URI) de la source documentaire pour la connecter."
    : "Enter the source name and URL/URI to connect it.";

  const attachedSources = datasources.filter((d) => d.workspaceName === activeWorkspace.name);

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
            {isFr ? `Espace sélectionné : ${activeWorkspace.name}` : `Selected Workspace: ${activeWorkspace.name}`}
          </h3>
          <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            {isFr
              ? "Gérez les sources documentaires, le glossaire métier et les consignes de cet espace au même endroit."
              : "Manage document sources, business glossary, and instructions for this workspace in one place."}
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
            {isFr ? "📚 Sources & Documents de l'Espace" : "📚 Workspace Sources & Documents"}
          </button>
          <button
            type="button"
            role="tab"
            data-testid="workspace-detail-tab-glossary"
            aria-selected={activeDetailTab === "GLOSSARY"}
            onClick={() => setActiveDetailTab("GLOSSARY")}
            className="orcia-ds-tab"
          >
            {isFr ? "📖 Glossaire & Règles Métiers (Ontologie)" : "📖 Business Glossary & Rules (Ontology)"}
          </button>
          <button
            type="button"
            role="tab"
            data-testid="workspace-detail-tab-members"
            aria-selected={activeDetailTab === "MEMBERS"}
            onClick={() => setActiveDetailTab("MEMBERS")}
            className="orcia-ds-tab"
          >
            {isFr ? "👥 Membres, Accès & Consignes" : "👥 Members, Access & Instructions"}
          </button>
        </nav>
      </div>

      {activeDetailTab === "SOURCES" && (
        <div
          data-testid="workspace-detail-sources-content"
          style={{ display: "flex", flexDirection: "column", gap: "12px" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <strong style={{ fontSize: "14px" }}>
              {isFr ? `Connecter une source documentaire à « ${activeWorkspace.name} »` : `Connect a document source to "${activeWorkspace.name}"`}
            </strong>
            <ContextualInfoTriggerButton
              sectionId="workspace-sources"
              label={isFr ? "Comprendre comment rattacher des sources documentaires" : "Understand how to attach document sources"}
              onOpenHelpSection={openHelpSection}
            />
          </div>

          <form
            data-testid="workspace-inline-add-datasource-form"
            autoComplete="off"
            data-lpignore="true"
            data-form-type="other"
            onSubmit={(e) => {
              e.preventDefault();
              if (!dsAlias.trim() || !dsUri.trim()) return;
              onRegisterDatasource({
                workspaceName: activeWorkspace.name,
                alias: dsAlias.trim(),
                scheme: dsScheme,
                uri: dsUri.trim(),
                executionIdentity: dsIdentity,
                freshnessTtlDays: 30,
              });
              setDsAlias("");
              setDsUri("");
              onFeedback(
                isFr
                  ? `✅ Source « ${dsAlias.trim()} » rattachée à l'espace « ${activeWorkspace.name} ».`
                  : `✅ Source "${dsAlias.trim()}" attached to workspace "${activeWorkspace.name}".`,
              );
            }}
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "8px",
              alignItems: "center",
              padding: "10px 12px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-bg-elevated)",
            }}
          >
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="workspace-inline-ds-alias-input"
              value={dsAlias}
              onChange={(e) => setDsAlias(e.target.value)}
              placeholder={isFr ? "Nom de la source (ex: Wiki Produit)..." : "Source name..."}
              style={{ ...inputStyle, minWidth: "170px" }}
            />
            <select
              data-testid="workspace-inline-ds-scheme-select"
              value={dsScheme}
              onChange={(e) => setDsScheme(e.target.value as "git" | "confluence" | "jira" | "db")}
              style={inputStyle}
            >
              <option value="git">{isFr ? "Dépôt Git" : "Git Repository"}</option>
              <option value="confluence">{isFr ? "Espace Confluence" : "Confluence Space"}</option>
              <option value="jira">{isFr ? "Projet Jira" : "Jira Project"}</option>
              <option value="db">{isFr ? "Base documentaire" : "Document Database"}</option>
            </select>
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="workspace-inline-ds-uri-input"
              value={dsUri}
              onChange={(e) => setDsUri(e.target.value)}
              placeholder={isFr ? "Adresse URL / URI (ex: https://confluence.entreprise.fr/...)..." : "Source URL / URI..."}
              style={{ ...inputStyle, flex: 1, minWidth: "220px" }}
            />
            <select
              data-testid="workspace-inline-ds-identity-select"
              value={dsIdentity}
              onChange={(e) => setDsIdentity(e.target.value as "passthrough" | "service_account")}
              style={inputStyle}
            >
              <option value="passthrough">{isFr ? "Compte personnel de chaque membre" : "Member personal account"}</option>
              <option value="service_account">{isFr ? "Compte partagé d'équipe" : "Shared team account"}</option>
            </select>
            <button
              type="submit"
              data-testid="workspace-inline-ds-submit-btn"
              disabled={isDsSubmitDisabled}
              title={isDsSubmitDisabled ? dsSubmitDisabledReason : undefined}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "7px 14px",
                borderRadius: "var(--radius-sm)",
                border: "none",
                backgroundColor: "var(--color-primary-cobalt)",
                color: "var(--color-primary-foreground)",
                fontWeight: 600,
                opacity: isDsSubmitDisabled ? 0.6 : 1,
                cursor: isDsSubmitDisabled ? "not-allowed" : "pointer",
              }}
            >
              <span>{isFr ? "+ Connecter la source" : "+ Connect source"}</span>
              <DisabledButtonAlertIndicator
                disabled={isDsSubmitDisabled}
                reason={dsSubmitDisabledReason}
                testIdSuffix="workspace-inline-ds-submit-btn"
              />
            </button>
          </form>

          {attachedSources.length === 0 ? (
            <p data-testid="workspace-detail-sources-empty" style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}>
              {isFr ? "Aucune source documentaire n'est encore rattachée à cet Espace." : "No document source is attached to this Workspace yet."}
            </p>
          ) : (
            <div style={{ display: "grid", gap: "8px" }}>
              {attachedSources.map((ds) => (
                <div
                  key={ds.id}
                  data-testid={`workspace-detail-source-row-${ds.id}`}
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
                  <div>
                    <strong>{ds.alias}</strong>{" "}
                    <a
                      href={ds.uri}
                      target="_blank"
                      rel="noreferrer"
                      style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-action-primary)" }}
                    >
                      {ds.uri}
                    </a>
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
                    {ds.executionIdentity === "passthrough"
                      ? isFr ? "Compte personnel" : "Personal account"
                      : isFr ? "Compte partagé d'équipe" : "Shared team account"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
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
            onFeedback(isFr ? `✅ Terme « ${concept.canonicalTerm} » ajouté au glossaire.` : `✅ Term "${concept.canonicalTerm}" added to the glossary.`);
          }}
          onPromoteConcept={(conceptKey, targetLevel, targetScopeId) => {
            onPromoteOntologyConcept(conceptKey, targetLevel, targetScopeId);
            onFeedback(isFr ? "✅ Terme promu au niveau supérieur du glossaire." : "✅ Term promoted to the upper glossary level.");
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
                {isFr
                  ? `Équipe propriétaire (Facturation IA) : ${activeWorkspace.ownerOrgUnitName ?? "Plateforme Globale ORCIA"}`
                  : `Owner Team (AI Billing): ${activeWorkspace.ownerOrgUnitName ?? "Global Platform ORCIA"}`}
              </strong>
              <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "var(--color-muted-foreground)" }}>
                {isFr
                  ? "Définissez les consignes par défaut que Mon Assistant et vos Agents respecteront dans cet Espace."
                  : "Define the default instructions that My Assistant and your Agents will follow in this Workspace."}
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
                {isFr ? "✓ Enregistré" : "✓ Saved"}
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
            placeholder={isFr ? "Consignes spécifiques à cet espace..." : "Workspace-specific instructions..."}
            style={{ ...inputStyle, width: "100%", fontFamily: "var(--font-sans)" }}
          />
        </div>
      )}
    </section>
  );
}

import {
  ContextualInfoTriggerButton,
  DisabledButtonAlertIndicator,
  getOrciaIconGlyph,
  OrciaIcon,
  type ControlCenterWorkspaceGovItem,
  type UiOntologyConceptView,
  type UiOntologyLevel,
} from "@orcia/ui";
import React, { useState } from "react";
import type { ConfiguredOrgUnit } from "../../components/platformSetupStore";

export interface WorkspaceGlossaryAndOntologyTabProps {
  readonly isFr: boolean;
  readonly selectedWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly onAddConcept: (input: UiOntologyConceptView) => void;
  readonly onPromoteConcept: (
    conceptKey: string,
    targetLevel: UiOntologyLevel,
    targetScopeId?: string,
  ) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function WorkspaceGlossaryAndOntologyTab({
  isFr,
  selectedWorkspace,
  orgUnits,
  ontologyConcepts,
  openHelpSection,
  onAddConcept,
  onPromoteConcept,
}: WorkspaceGlossaryAndOntologyTabProps): React.ReactElement {
  const [termName, setTermName] = useState("");
  const [termDefinition, setTermDefinition] = useState("");
  const [selectedScopeTier, setSelectedScopeTier] = useState<
    "WORKSPACE" | "TEAM" | "BU" | "ENTERPRISE"
  >(selectedWorkspace ? "WORKSPACE" : "ENTERPRISE");
  const [promotedKeys, setPromotedKeys] = useState<readonly string[]>([]);

  const wsName =
    selectedWorkspace?.name ?? (isFr ? "Plateforme Globale ORCIA" : "Global Platform ORCIA");
  const wsId = selectedWorkspace?.workspaceId ?? "scope-global";

  const ownerTeamUnit = orgUnits.find(
    (u) => u.id === selectedWorkspace?.ownerOrgUnitId || u.name === selectedWorkspace?.ownerOrgUnitName,
  );
  const parentBuUnit = ownerTeamUnit
    ? orgUnits.find((u) => u.id === ownerTeamUnit.parentId && u.level === "BU")
    : orgUnits.find((u) => u.level === "BU");

  const teamLabel =
    selectedWorkspace?.ownerOrgUnitName ?? ownerTeamUnit?.name ?? (isFr ? "Équipe" : "Team");
  const buLabel = parentBuUnit?.name ?? "BU";

  const isSubmitDisabled = !termName.trim();
  const submitDisabledReason = isFr
    ? "Saisissez l'intitulé du terme ou de la règle métier pour l'ajouter au glossaire."
    : "Enter the business term or rule name to add it to the glossary.";

  const handleCreateConcept = (e: React.FormEvent) => {
    e.preventDefault();
    if (!termName.trim()) return;
    const mappedLevel: UiOntologyLevel =
      selectedScopeTier === "ENTERPRISE"
        ? "1_ENTERPRISE"
        : selectedScopeTier === "BU"
          ? "2_DOMAIN"
          : selectedScopeTier === "TEAM"
            ? "3_TEAM"
            : "3_WORKSPACE";
    const resolvedScopeId =
      selectedScopeTier === "ENTERPRISE"
        ? "scope-global"
        : selectedScopeTier === "BU"
          ? (parentBuUnit?.id ?? "scope-bu")
          : selectedScopeTier === "TEAM"
            ? (selectedWorkspace?.ownerOrgUnitId ?? ownerTeamUnit?.id ?? "scope-team")
            : wsId;

    const cleanDef = termDefinition.trim() || termName.trim();
    const conceptKey = termName.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

    onAddConcept({
      conceptKey: conceptKey || `concept-${ontologyConcepts.length + 1}`,
      canonicalTerm: termName.trim(),
      level: mappedLevel,
      scopeId: resolvedScopeId,
      definitionText: cleanDef,
      immutable: mappedLevel === "1_ENTERPRISE",
      synonyms: [],
      profileTranslations: {
        EXECUTIVE: cleanDef,
        PM_PO: cleanDef,
        ARCHITECT: cleanDef,
        TECH_LEAD: cleanDef,
        DEVELOPER: cleanDef,
        SECOPS: cleanDef,
      },
      impactedTemplates: [],
      impactedWorkflows: [],
      impactedRuns: [],
    });
    setTermName("");
    setTermDefinition("");
  };

  const handlePromote = (concept: UiOntologyConceptView) => {
    if (concept.level === "3_WORKSPACE" || concept.level === "4_RUN_EPHEMERAL") {
      onPromoteConcept(
        concept.conceptKey,
        "2_DOMAIN",
        parentBuUnit?.id ?? selectedWorkspace?.ownerOrgUnitId ?? "scope-bu",
      );
    } else if (concept.level === "3_TEAM" || concept.level === "2_DOMAIN") {
      onPromoteConcept(concept.conceptKey, "1_ENTERPRISE", "scope-global");
    }
    setPromotedKeys((prev) => (prev.includes(concept.conceptKey) ? prev : [...prev, concept.conceptKey]));
  };

  const enterpriseIcon = getOrciaIconGlyph("organizationBu");
  const divisionIcon = getOrciaIconGlyph("divisionLandmark");
  const teamIcon = getOrciaIconGlyph("team");
  const workspaceIcon = getOrciaIconGlyph("workspaceFolder");

  const cascadeTiers = [
    {
      tierId: "enterprise",
      badge: isFr ? `${enterpriseIcon} Entreprise (Global)` : `${enterpriseIcon} Enterprise (Global)`,
      subtitle: isFr ? "Socle commun de l'organisation" : "Organization shared foundation",
      items: ontologyConcepts.filter((c) => c.level === "1_ENTERPRISE"),
    },
    {
      tierId: "domain",
      badge: isFr ? `${divisionIcon} Direction (${buLabel})` : `${divisionIcon} Division (${buLabel})`,
      subtitle: isFr ? "Vocabulaire et règles de votre Direction" : "Division vocabulary & rules",
      items: ontologyConcepts.filter((c) => c.level === "2_DOMAIN"),
    },
    {
      tierId: "team",
      badge: isFr ? `${teamIcon} Équipe (${teamLabel})` : `${teamIcon} Team (${teamLabel})`,
      subtitle: isFr ? "Termes partagés par l'équipe" : "Team shared terms",
      items: ontologyConcepts.filter((c) => c.level === "3_TEAM"),
    },
    {
      tierId: "workspace",
      badge: isFr ? `${workspaceIcon} Cet Espace (${wsName})` : `${workspaceIcon} This Workspace (${wsName})`,
      subtitle: isFr ? "Termes spécifiques à cet espace" : "Workspace-specific terms",
      items: ontologyConcepts.filter((c) => c.level === "3_WORKSPACE" || c.level === "4_RUN_EPHEMERAL"),
    },
  ];

  const getLevelBadgeLabel = (level: UiOntologyLevel): string => {
    if (level === "1_ENTERPRISE") return isFr ? `${enterpriseIcon} Entreprise (Global)` : `${enterpriseIcon} Enterprise`;
    if (level === "2_DOMAIN") return isFr ? `${divisionIcon} Direction (${buLabel})` : `${divisionIcon} Division (${buLabel})`;
    if (level === "3_TEAM") return isFr ? `${teamIcon} Équipe (${teamLabel})` : `${teamIcon} Team (${teamLabel})`;
    return isFr ? `${workspaceIcon} Cet Espace (${wsName})` : `${workspaceIcon} This Workspace (${wsName})`;
  };

  return (
    <div
      data-testid="workspace-glossary-and-ontology-tab"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      <div
        data-testid="glossary-inheritance-cascade-bar"
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <strong style={{ fontSize: "14px" }}>
            <OrciaIcon name="bookOpen" />{" "}
            {isFr ? `Glossaire & Règles Métiers applicables à « ${wsName} »` : `Business Glossary & Rules applicable to "${wsName}"`}
          </strong>
          <ContextualInfoTriggerButton
            sectionId="glossary-rules"
            label={isFr ? "Comprendre l'héritage du glossaire et la promotion en 1 clic" : "Understand glossary inheritance"}
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <span
          data-testid="workspace-glossary-cascade-summary"
          style={{
            fontSize: "11px",
            padding: "3px 8px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-bg-elevated)",
            border: "1px solid var(--color-border-subtle)",
            color: "var(--color-text-secondary)",
          }}
        >
          {`${enterpriseIcon} Entreprise (Global) ➔ ${divisionIcon} Direction (${buLabel}) ➔ ${teamIcon} Équipe (${teamLabel}) ➔ ${workspaceIcon} Cet Espace (${wsName})`}
        </span>
      </div>

      <form
        data-testid="workspace-inline-add-glossary-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        onSubmit={handleCreateConcept}
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
          data-testid="workspace-glossary-term-input"
          value={termName}
          onChange={(e) => setTermName(e.target.value)}
          placeholder={isFr ? "Nouveau terme ou règle métier (ex: Délai de franchise)..." : "New business term or rule..."}
          style={{ ...inputStyle, flex: 1, minWidth: "180px" }}
        />
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="workspace-glossary-definition-input"
          value={termDefinition}
          onChange={(e) => setTermDefinition(e.target.value)}
          placeholder={isFr ? "Définition claire ou consigne à respecter par les agents..." : "Clear definition or rule..."}
          style={{ ...inputStyle, flex: 2, minWidth: "220px" }}
        />
        <select
          data-testid="workspace-glossary-scope-select"
          aria-label={isFr ? "Portée d'application du terme" : "Term application scope"}
          value={selectedScopeTier}
          onChange={(e) => setSelectedScopeTier(e.target.value as "WORKSPACE" | "TEAM" | "BU" | "ENTERPRISE")}
          style={inputStyle}
        >
          <option value="WORKSPACE">{isFr ? `${workspaceIcon} Cet Espace (${wsName})` : `${workspaceIcon} This Workspace (${wsName})`}</option>
          <option value="TEAM">{isFr ? `${teamIcon} Mon Équipe (${teamLabel})` : `${teamIcon} My Team (${teamLabel})`}</option>
          <option value="BU">{isFr ? `${divisionIcon} Direction (${buLabel})` : `${divisionIcon} Division (${buLabel})`}</option>
          <option value="ENTERPRISE">{isFr ? `${enterpriseIcon} Entreprise (Global)` : `${enterpriseIcon} Enterprise (Global)`}</option>
        </select>
        <button
          type="submit"
          data-testid="workspace-glossary-submit-btn"
          disabled={isSubmitDisabled}
          title={isSubmitDisabled ? submitDisabledReason : undefined}
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
            opacity: isSubmitDisabled ? 0.6 : 1,
            cursor: isSubmitDisabled ? "not-allowed" : "pointer",
          }}
        >
          <span>{isFr ? "+ Ajouter au glossaire" : "+ Add to glossary"}</span>
          <DisabledButtonAlertIndicator
            disabled={isSubmitDisabled}
            reason={submitDisabledReason}
            testIdSuffix="workspace-glossary-submit-btn"
          />
        </button>
      </form>

      <div
        data-testid="workspace-glossary-cascade-grid"
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "10px" }}
      >
        {cascadeTiers.map((tier) => (
          <div
            key={tier.tierId}
            data-testid={`workspace-glossary-tier-${tier.tierId}`}
            style={{
              padding: "10px 12px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-card)",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong style={{ fontSize: "12px" }}>{tier.badge}</strong>
              <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>{tier.items.length}</span>
            </div>
            <p style={{ margin: 0, fontSize: "11px", color: "var(--color-muted-foreground)" }}>{tier.subtitle}</p>
            {tier.items.length === 0 ? (
              <p
                data-testid={`workspace-glossary-empty-${tier.tierId}`}
                style={{ margin: 0, fontSize: "11px", color: "var(--color-muted-foreground)" }}
              >
                {isFr ? "Aucun terme défini à ce niveau." : "No term defined at this level."}
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {tier.items.map((concept) => {
                  const isPromoted = promotedKeys.includes(concept.conceptKey);
                  const canPromote = concept.level !== "1_ENTERPRISE";
                  return (
                    <div
                      key={concept.conceptKey}
                      data-testid={`glossary-concept-card-${concept.conceptKey}`}
                      style={{
                        padding: "8px 10px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border-subtle)",
                        backgroundColor: "var(--color-bg-elevated)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "4px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                        <strong style={{ fontSize: "12px" }}>{concept.canonicalTerm}</strong>
                        <span data-testid={`glossary-concept-level-badge-${concept.conceptKey}`} style={{ fontSize: "10px", color: "var(--color-text-secondary)" }}>
                          {getLevelBadgeLabel(concept.level)}
                        </span>
                      </div>
                      <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>{concept.definitionText}</span>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        {isPromoted && (
                          <span
                            data-testid={`promoted-glossary-badge-${concept.conceptKey}`}
                            style={{
                              fontSize: "10px",
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: "var(--radius-sm)",
                              backgroundColor: "var(--color-action-primary-subtle)",
                              color: "var(--color-status-success)",
                            }}
                          >
                            <OrciaIcon name="check" /> {isFr ? "Promu" : "Promoted"}
                          </span>
                        )}
                        {canPromote && (
                          <button
                            type="button"
                            data-testid={`promote-glossary-concept-btn-${concept.conceptKey}`}
                            onClick={() => handlePromote(concept)}
                            style={{
                              padding: "2px 8px",
                              fontSize: "11px",
                              fontWeight: 600,
                              borderRadius: "var(--radius-sm)",
                              border: "1px solid var(--color-border)",
                              backgroundColor: "var(--color-surface-card)",
                              color: "var(--color-action-primary)",
                              cursor: "pointer",
                            }}
                          >
                            <OrciaIcon name="promoteUp" />{" "}
                            {concept.level === "3_WORKSPACE"
                              ? isFr ? "Partager à la Direction / Équipe" : "Share with Division / Team"
                              : isFr ? "Promouvoir à l'Organisation" : "Promote to Organization"}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

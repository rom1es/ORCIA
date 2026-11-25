import {
  DisabledButtonAlertIndicator,
  getOrciaIconGlyph,
  OrciaAlertBanner,
  OrciaIcon,
  type ControlCenterWorkspaceGovItem,
  type UiOntologyConceptView,
  type UiOntologyLevel,
} from "@orcia/ui";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchOntologyConceptsFromApi,
  fetchOntologyPromotionsFromApi,
  proposeOntologyPromotionToApi,
  slugifyScopedConceptKey,
  upsertOntologyConceptToApi,
  type WritableScopeOptionItem,
} from "../../components/ontologyApiBridge";
import type { ConfiguredOrgUnit } from "../../components/platformSetupStore";
import { formatI18nTemplate, normalizeWebLocale, useI18n } from "../../i18n";
import {
  type GlossaryScopeTier,
  resolveGlossaryScopeId,
  WorkspaceGlossaryCascadeGrid,
} from "./WorkspaceGlossaryCascadeGrid";
import type { WorkspaceFeedbackInput } from "./workspaceFeedbackTypes";

export interface WorkspaceGlossaryAndOntologyTabProps {
  readonly isFr: boolean;
  readonly selectedWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly refreshNonce?: number;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onAddConcept: (input: UiOntologyConceptView) => void;
  readonly onPromoteConcept: (
    conceptKey: string,
    targetLevel: UiOntologyLevel,
    targetScopeId?: string,
  ) => void;
  readonly onPromotionsChanged?: () => void;
  readonly onFeedback?: (feedback: WorkspaceFeedbackInput) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function WorkspaceGlossaryAndOntologyTab({
  selectedWorkspace,
  orgUnits,
  ontologyConcepts,
  refreshNonce = 0,
  onAddConcept,
  onPromotionsChanged,
  onFeedback,
}: WorkspaceGlossaryAndOntologyTabProps): React.ReactElement {
  const { dictionary, locale } = useI18n();
  const copy = dictionary.ontologyGlossary;
  const glossaryTabCopy = dictionary.featureWorkspaces.glossaryTab;
  const typedLocale = normalizeWebLocale(locale);

  const onFeedbackRef = useRef(onFeedback);
  onFeedbackRef.current = onFeedback;
  const [termName, setTermName] = useState("");
  const [termDefinition, setTermDefinition] = useState("");
  const [selectedScopeTier, setSelectedScopeTier] = useState<GlossaryScopeTier>(
    selectedWorkspace ? "WORKSPACE" : "ENTERPRISE",
  );
  const [serverConcepts, setServerConcepts] = useState<readonly UiOntologyConceptView[]>([]);
  const [pendingConceptKeys, setPendingConceptKeys] = useState<readonly string[]>([]);
  const [writableLevels, setWritableLevels] = useState<readonly UiOntologyLevel[] | null>(null);
  const [writableScopes, setWritableScopes] = useState<readonly WritableScopeOptionItem[]>([]);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const reportError = useCallback((message: string) => {
    if (onFeedbackRef.current) {
      setErrorBanner(null);
      onFeedbackRef.current({ tone: "crimson", message });
    } else {
      setErrorBanner(message);
    }
  }, []);

  const loadFromServer = useCallback(async () => {
    try {
      const [cRes, pRes] = await Promise.all([
        fetchOntologyConceptsFromApi(typedLocale),
        fetchOntologyPromotionsFromApi(typedLocale),
      ]);
      setServerConcepts(cRes.concepts);
      setWritableLevels(cRes.writableLevels);
      setWritableScopes(cRes.writableScopes);
      setPendingConceptKeys(
        pRes.proposals.filter((p) => p.status === "PENDING_REVIEW").map((p) => p.concept_key),
      );
    } catch (err: unknown) {
      reportError(err instanceof Error ? err.message : copy.errorFallback);
    }
  }, [typedLocale, copy.errorFallback, reportError]);

  useEffect(() => {
    void loadFromServer();
  }, [loadFromServer, refreshNonce]);

  const wsName = selectedWorkspace?.name ?? copy.workspaceGlossaryDefaultPlatformName;
  const wsId = selectedWorkspace?.workspaceId ?? "scope-global";
  const ownerTeamUnit = orgUnits.find(
    (u) => u.id === selectedWorkspace?.ownerOrgUnitId || u.name === selectedWorkspace?.ownerOrgUnitName,
  );
  const parentBuUnit = ownerTeamUnit
    ? orgUnits.find((u) => u.id === ownerTeamUnit.parentId && u.level === "BU")
    : orgUnits.find((u) => u.level === "BU");
  const teamLabel = selectedWorkspace?.ownerOrgUnitName ?? ownerTeamUnit?.name ?? "";
  const buLabel = parentBuUnit?.name ?? "BU";

  const displayedConcepts = serverConcepts.length > 0 ? serverConcepts : ontologyConcepts;
  const canTier = (lvl: UiOntologyLevel) =>
    writableLevels === null ||
    writableLevels.includes(lvl) ||
    (lvl === "4_WORKSPACE" && writableLevels.includes("3_WORKSPACE"));

  const handleCreateConcept = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!termName.trim()) return;
    setErrorBanner(null);
    const mappedLevel: UiOntologyLevel =
      selectedScopeTier === "ENTERPRISE"
        ? "1_ENTERPRISE"
        : selectedScopeTier === "BU"
          ? "2_DOMAIN"
          : selectedScopeTier === "TEAM"
            ? "3_TEAM"
            : "4_WORKSPACE";
    const resolvedScopeId = resolveGlossaryScopeId({
      selectedScopeTier,
      writableScopes,
      parentBuUnit,
      preferredTeamId: selectedWorkspace?.ownerOrgUnitId ?? ownerTeamUnit?.id,
      hasSelectedWorkspace: Boolean(selectedWorkspace),
      wsId,
    });
    if (!resolvedScopeId) {
      reportError(copy.errorFallback);
      return;
    }
    const cleanDef = termDefinition.trim() || termName.trim();
    const conceptKey = slugifyScopedConceptKey(termName, mappedLevel, resolvedScopeId);
    const payload: UiOntologyConceptView = {
      conceptKey,
      canonicalTerm: termName.trim(),
      level: mappedLevel,
      scopeId: resolvedScopeId,
      definitionText: cleanDef,
      immutable: mappedLevel === "1_ENTERPRISE",
      synonyms: [],
      profileTranslations: {
        EXECUTIVE: cleanDef,
        PM_BUSINESS: cleanDef,
        ARCHITECT: cleanDef,
        TECH_LEAD: cleanDef,
        DEVELOPER: cleanDef,
        SECOPS: cleanDef,
      },
      impactedTemplates: [],
      impactedWorkflows: [],
      impactedRuns: [],
    };
    try {
      await upsertOntologyConceptToApi(typedLocale, payload);
      onAddConcept(payload);
      setTermName("");
      setTermDefinition("");
      await loadFromServer();
    } catch (err: unknown) {
      reportError(err instanceof Error ? err.message : copy.errorFallback);
    }
  };

  const handlePromote = async (concept: UiOntologyConceptView) => {
    setErrorBanner(null);
    const fallbackTargetLevel: UiOntologyLevel =
      concept.level === "4_WORKSPACE" || concept.level === "3_WORKSPACE"
        ? selectedWorkspace?.ownerOrgUnitId || ownerTeamUnit?.id
          ? "3_TEAM"
          : "2_DOMAIN"
        : concept.level === "3_TEAM"
          ? "2_DOMAIN"
          : "1_ENTERPRISE";
    const targetLevel = concept.nextPromotionLevel ?? fallbackTargetLevel;
    try {
      await proposeOntologyPromotionToApi(typedLocale, {
        concept_key: concept.conceptKey,
        target_level: targetLevel,
        target_scope_id: concept.nextPromotionScopeId ?? undefined,
      });
      await loadFromServer();
      onPromotionsChanged?.();
    } catch (err: unknown) {
      reportError(err instanceof Error ? err.message : copy.errorFallback);
    }
  };

  const enterpriseIcon = getOrciaIconGlyph("organizationBu");
  const divisionIcon = getOrciaIconGlyph("divisionLandmark");
  const teamIcon = getOrciaIconGlyph("team");
  const workspaceIcon = getOrciaIconGlyph("workspaceFolder");
  const isSubmitDisabled = !termName.trim();

  const domainText = formatI18nTemplate(glossaryTabCopy.domainBadgeTemplate, { name: buLabel });
  const teamText = formatI18nTemplate(glossaryTabCopy.teamBadgeTemplate, { name: teamLabel });
  const wsText = formatI18nTemplate(glossaryTabCopy.workspaceBadgeTemplate, { name: wsName });

  const cascadeTiers = [
    { tierId: "enterprise", badge: `${enterpriseIcon} ${copy.workspaceGlossaryEnterpriseTitle}`, subtitle: copy.workspaceGlossaryEnterpriseSub, items: displayedConcepts.filter((c) => c.level === "1_ENTERPRISE") },
    { tierId: "domain", badge: `${divisionIcon} ${domainText}`, subtitle: copy.workspaceGlossaryDomainSub, items: displayedConcepts.filter((c) => c.level === "2_DOMAIN") },
    { tierId: "team", badge: `${teamIcon} ${teamText}`, subtitle: copy.workspaceGlossaryTeamSub, items: displayedConcepts.filter((c) => c.level === "3_TEAM") },
    {
      tierId: "workspace",
      badge: `${workspaceIcon} ${wsText}`,
      subtitle: copy.workspaceGlossaryWorkspaceSub,
      items: displayedConcepts.filter((c) => c.level === "4_WORKSPACE" || c.level === "3_WORKSPACE" || c.level === "4_RUN_EPHEMERAL"),
    },
  ];

  const getLevelBadgeLabel = (level: UiOntologyLevel): string => {
    if (level === "1_ENTERPRISE") return `${enterpriseIcon} ${copy.workspaceGlossaryEnterpriseTitle}`;
    if (level === "2_DOMAIN") return `${divisionIcon} ${domainText}`;
    if (level === "3_TEAM") return `${teamIcon} ${teamText}`;
    return `${workspaceIcon} ${wsText}`;
  };

  return (
    <div data-testid="workspace-glossary-and-ontology-tab" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {!onFeedback && errorBanner && (
        <OrciaAlertBanner tone="crimson" testId="workspace-glossary-error-banner">
          {errorBanner}
        </OrciaAlertBanner>
      )}
      <div data-testid="glossary-inheritance-cascade-bar" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <strong style={{ fontSize: "14px" }}>
            <OrciaIcon name="bookOpen" /> {`${copy.workspaceGlossaryTitlePrefix} « ${wsName} »`}
          </strong>
        </div>
        <span data-testid="workspace-glossary-cascade-summary" style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "var(--radius-sm)", backgroundColor: "var(--color-bg-elevated)", border: "1px solid var(--color-border-subtle)", color: "var(--color-text-secondary)" }}>
          {`${enterpriseIcon} ${copy.workspaceGlossaryEnterpriseTitle} ➔ ${divisionIcon} ${domainText} ➔ ${teamIcon} ${teamText} ➔ ${workspaceIcon} ${wsText}`}
        </span>
      </div>

      <form
        data-testid="workspace-inline-add-glossary-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        onSubmit={(e) => void handleCreateConcept(e)}
        style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center", padding: "10px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", backgroundColor: "var(--color-bg-elevated)" }}
      >
        <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="workspace-glossary-term-input" value={termName} onChange={(e) => setTermName(e.target.value)} placeholder={copy.workspaceGlossaryTermPlaceholder} style={{ ...inputStyle, flex: 1, minWidth: "180px" }} />
        <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="workspace-glossary-definition-input" value={termDefinition} onChange={(e) => setTermDefinition(e.target.value)} placeholder={copy.workspaceGlossaryDefPlaceholder} style={{ ...inputStyle, flex: 2, minWidth: "220px" }} />
        <select
          data-testid="workspace-glossary-scope-select"
          aria-label={copy.workspaceGlossaryScopeLabel}
          value={selectedScopeTier}
          onChange={(e) => setSelectedScopeTier(e.target.value as "WORKSPACE" | "TEAM" | "BU" | "ENTERPRISE")}
          style={inputStyle}
        >
          {canTier("4_WORKSPACE") && <option value="WORKSPACE">{`${workspaceIcon} ${wsText}`}</option>}
          {canTier("3_TEAM") && <option value="TEAM">{`${teamIcon} ${teamText}`}</option>}
          {canTier("2_DOMAIN") && <option value="BU">{`${divisionIcon} ${domainText}`}</option>}
          {canTier("1_ENTERPRISE") && <option value="ENTERPRISE">{`${enterpriseIcon} ${copy.workspaceGlossaryEnterpriseTitle}`}</option>}
        </select>
        <button
          type="submit"
          data-testid="workspace-glossary-submit-btn"
          disabled={isSubmitDisabled}
          title={isSubmitDisabled ? copy.workspaceGlossarySubmitDisabledReason : undefined}
          className="orcia-ds-btn orcia-ds-btn-primary"
        >
          <span>{copy.workspaceGlossarySubmitLabel}</span>
          <DisabledButtonAlertIndicator disabled={isSubmitDisabled} reason={copy.workspaceGlossarySubmitDisabledReason} testIdSuffix="workspace-glossary-submit-btn" />
        </button>
      </form>

      <WorkspaceGlossaryCascadeGrid
        cascadeTiers={cascadeTiers}
        pendingConceptKeys={pendingConceptKeys}
        copy={copy}
        getLevelBadgeLabel={getLevelBadgeLabel}
        onPromote={(concept) => void handlePromote(concept)}
      />
    </div>
  );
}

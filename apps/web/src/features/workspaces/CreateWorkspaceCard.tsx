import {
  ContextualInfoTriggerButton,
  DisabledButtonAlertIndicator,
  type ProductLifecyclePhaseType,
  type WorkspaceVisibilityMode,
} from "@orcia/ui";
import React, { useState } from "react";
import type { ConfiguredOrgUnit } from "../../components/platformSetupStore";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../i18n";

export interface CreateWorkspaceCardProps {
  readonly isFr: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly activeScopeName: string;
  readonly activeScopeCategoryLabel: string;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onNavigateToSettings: () => void;
  readonly onCreateWorkspace: (input: {
    name: string;
    slug: string;
    visibilityMode: WorkspaceVisibilityMode;
    lifecyclePhase: ProductLifecyclePhaseType;
    ownerOrgUnitId?: string;
  }) => void | Promise<unknown>;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function CreateWorkspaceCard({
  isFr,
  orgUnits,
  activeScopeName,
  activeScopeCategoryLabel,
  openHelpSection,
  onNavigateToSettings,
  onCreateWorkspace,
}: CreateWorkspaceCardProps): React.ReactElement {
  const cardCopy = resolveDictionaryForFlag(isFr).featureWorkspaces.createCard;
  const [wsName, setWsName] = useState("");
  const [wsSlug, setWsSlug] = useState("");
  const [wsVisibility, setWsVisibility] = useState<WorkspaceVisibilityMode>("STANDARD");
  const [wsPhase, setWsPhase] = useState<ProductLifecyclePhaseType>("BUILD");
  const [selectedTeamId, setSelectedTeamId] = useState<string>("");

  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const effectiveOwnerTeamId =
    selectedTeamId || teamUnits[0]?.id || orgUnits[orgUnits.length - 1]?.id || "";
  const isSubmitDisabled = !wsName.trim();
  const submitDisabledReason =
    teamUnits.length === 0 ? cardCopy.disabledReasonNoTeam : cardCopy.disabledReasonWithTeam;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!wsName.trim()) return;
    await onCreateWorkspace({
      name: wsName.trim(),
      slug: wsSlug.trim() || wsName.trim().toLowerCase().replace(/\s+/g, "-"),
      visibilityMode: wsVisibility,
      lifecyclePhase: wsPhase,
      ...(effectiveOwnerTeamId ? { ownerOrgUnitId: effectiveOwnerTeamId } : {}),
    });
    setWsName("");
    setWsSlug("");
  };

  return (
    <section
      data-testid="create-workspace-panel"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
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
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <h2 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>{cardCopy.title}</h2>
          <ContextualInfoTriggerButton
            sectionId="workspace-sources"
            label={cardCopy.helpTriggerLabel}
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <span
          data-testid="workspace-active-scope-banner"
          style={{
            fontSize: "12px",
            fontWeight: 600,
            padding: "4px 10px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
          }}
        >
          {activeScopeCategoryLabel} : {activeScopeName}
        </span>
      </div>

      {teamUnits.length === 0 && (
        <div
          data-testid="workspace-no-billing-team-warning"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            fontSize: "12px",
          }}
        >
          <span>{cardCopy.noTeamBannerText}</span>
          <button
            type="button"
            data-testid="workspace-go-create-team-btn"
            onClick={onNavigateToSettings}
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface)",
              color: "var(--color-foreground)",
              fontWeight: 600,
              fontSize: "11px",
              cursor: "pointer",
            }}
          >
            {cardCopy.createTeamBtn}
          </button>
        </div>
      )}

      <form
        data-testid="create-workspace-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        onSubmit={handleSubmit}
        style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}
      >
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="workspace-name-input"
          value={wsName}
          onChange={(e) => setWsName(e.target.value)}
          placeholder={cardCopy.namePlaceholder}
          style={{ ...inputStyle, flex: 1, minWidth: "200px" }}
        />
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="workspace-slug-input"
          value={wsSlug}
          onChange={(e) => setWsSlug(e.target.value)}
          placeholder={cardCopy.slugPlaceholder}
          style={inputStyle}
        />
        <select
          data-testid="workspace-owner-team-select"
          aria-label={cardCopy.ownerTeamAriaLabel}
          value={effectiveOwnerTeamId}
          onChange={(e) => setSelectedTeamId(e.target.value)}
          style={inputStyle}
        >
          {teamUnits.length === 0 ? (
            <option value="">{cardCopy.defaultBillingTeamOption}</option>
          ) : (
            teamUnits.map((team) => (
              <option key={team.id} value={team.id}>
                {formatI18nTemplate(cardCopy.billingTeamOptionTemplate, { name: team.name })}
              </option>
            ))
          )}
        </select>
        <select
          data-testid="workspace-visibility-select"
          value={wsVisibility}
          onChange={(e) => setWsVisibility(e.target.value as WorkspaceVisibilityMode)}
          style={inputStyle}
        >
          <option value="STANDARD">{cardCopy.visibilityTeamStandard}</option>
          <option value="PRIVATE_USER">{cardCopy.visibilityPrivatePersonal}</option>
          <option value="CONFIDENTIAL_RESTRICTED">{cardCopy.visibilityConfidential}</option>
        </select>
        <select
          data-testid="workspace-phase-select"
          value={wsPhase}
          onChange={(e) => setWsPhase(e.target.value as ProductLifecyclePhaseType)}
          style={inputStyle}
        >
          <option value="BUILD">{cardCopy.phaseBuild}</option>
          <option value="RUN">{cardCopy.phaseRun}</option>
          <option value="MIGRATION">{cardCopy.phaseMigration}</option>
        </select>
        <button
          type="submit"
          data-testid="create-workspace-submit-btn"
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
          <span>{cardCopy.submitBtn}</span>
          <DisabledButtonAlertIndicator
            disabled={isSubmitDisabled}
            reason={submitDisabledReason}
            testIdSuffix="create-workspace-submit-btn"
          />
        </button>
      </form>
    </section>
  );
}

import {
  OrciaAlertBanner,
  OrciaButton,
  OrciaDialog,
  OrciaSearchableSelect,
  OrciaUserPillsSelect,
  resolvePendingKnownUserId,
  type KnownUserOption,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { AdminAndStudioDictionarySection } from "../../../i18n/locales/admin_and_studio_labels";
import { getEligibleParentBuUnits } from "./orgTreeHelpers";
import { isKnownUserIdentifier } from "./orgUnitsApiBridge";
import { useKnownOrgUsersSearch } from "./useKnownOrgUsersSearch";
import { useParentOrgSearch } from "./useParentOrgSearch";

export interface CreateOrgUnitFormValues {
  readonly kind: "BU" | "TEAM";
  readonly name: string;
  readonly slug: string;
  readonly parentId: string;
  readonly billingEnabled: boolean;
  readonly leadUserId: string;
  readonly leadUserIds?: readonly string[];
  readonly ontologyLeadUserIds?: readonly string[];
}

export interface CreateOrgUnitModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly canMutate: boolean;
  readonly canCreateAtRoot?: boolean;
  readonly creatableParentUnits?: readonly ConfiguredOrgUnit[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly knownUsers?: readonly KnownUserOption[];
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"]["createModal"];
  readonly unknownUserErrorLabel?: string;
  readonly errorMessage: string | null;
  readonly isSubmitting: boolean;
  readonly onSubmit: (values: CreateOrgUnitFormValues) => void;
}

export function CreateOrgUnitModal({
  open,
  onOpenChange,
  canMutate,
  canCreateAtRoot = true,
  creatableParentUnits,
  orgUnits,
  knownUsers = [],
  labels,
  unknownUserErrorLabel,
  errorMessage,
  isSubmitting,
  onSubmit,
}: CreateOrgUnitModalProps): React.ReactElement {
  const effectiveParentPool = creatableParentUnits ?? orgUnits;
  const buUnits = getEligibleParentBuUnits(effectiveParentPool);
  const firstBuId = buUnits[0]?.id ?? "scope-global";

  const {
    options: rawParentOptions,
    handleSearchQueryChange: onParentSearchChange,
    resetSearch: resetParentSearch,
  } = useParentOrgSearch({
    initialUnits: effectiveParentPool,
    rootParentOptionLabel: labels.rootParentOption,
    parentBuOptionPrefix: labels.parentBuOptionPrefix,
  });
  const parentOptions = canCreateAtRoot
    ? rawParentOptions
    : rawParentOptions.filter((opt) => opt.value !== "scope-global");

  const leadSearch = useKnownOrgUsersSearch({ initialKnownUsers: knownUsers });
  const ontoSearch = useKnownOrgUsersSearch({ initialKnownUsers: knownUsers });
  const [kind, setKind] = useState<"BU" | "TEAM">("BU");
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [parentId, setParentId] = useState(() => (canCreateAtRoot ? "scope-global" : firstBuId));
  const [billingEnabled, setBillingEnabled] = useState(true);
  const [leadUserIds, setLeadUserIds] = useState<readonly string[]>([]);
  const [leadDraft, setLeadDraft] = useState("");
  const [ontologyLeadUserIds, setOntologyLeadUserIds] = useState<readonly string[]>([]);
  const [ontologyLeadDraft, setOntologyLeadDraft] = useState("");
  const [leadValidationError, setLeadValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setKind("BU");
      setName("");
      setSlug("");
      setParentId(canCreateAtRoot ? "scope-global" : firstBuId);
      setBillingEnabled(true);
      setLeadUserIds([]);
      setLeadDraft("");
      setOntologyLeadUserIds([]);
      setOntologyLeadDraft("");
      setLeadValidationError(null);
      resetParentSearch();
    }
  }, [open, canCreateAtRoot, firstBuId]);

  const handleKindChange = (nextKind: "BU" | "TEAM") => {
    setKind(nextKind);
    setParentId(
      nextKind === "TEAM" && buUnits.length > 0
        ? firstBuId
        : canCreateAtRoot
          ? "scope-global"
          : firstBuId,
    );
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canMutate || !name.trim() || isSubmitting) return;
    const allKnownUsers = [...leadSearch.knownUsers, ...ontoSearch.knownUsers, ...knownUsers];
    const pendingId = resolvePendingKnownUserId(leadDraft, allKnownUsers);
    const finalLeads = pendingId && !leadUserIds.some((id) => id.toLowerCase() === pendingId.toLowerCase())
      ? [...leadUserIds, pendingId]
      : leadUserIds;
    const pendingOntoId = resolvePendingKnownUserId(ontologyLeadDraft, allKnownUsers);
    const finalOntoLeads =
      kind === "BU"
        ? pendingOntoId && !ontologyLeadUserIds.some((id) => id.toLowerCase() === pendingOntoId.toLowerCase())
          ? [...ontologyLeadUserIds, pendingOntoId]
          : ontologyLeadUserIds
        : [];
    const invalidLead = [...finalLeads, ...finalOntoLeads].find(
      (lid) => !isKnownUserIdentifier(lid, allKnownUsers),
    );
    if (invalidLead) {
      setLeadValidationError(
        unknownUserErrorLabel ||
          "L'identifiant saisi ne correspond à aucun utilisateur actif et connu de la plateforme.",
      );
      return;
    }
    onSubmit({
      kind,
      name: name.trim(),
      slug: slug.trim(),
      parentId,
      billingEnabled,
      leadUserId: finalLeads[0] ?? "",
      leadUserIds: finalLeads,
      ontologyLeadUserIds: finalOntoLeads,
    });
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={labels.title}
      description={labels.description}
      testId="create-org-unit-modal"
      closeLabel={labels.cancelButton}
    >
      <form
        data-testid="create-org-unit-form"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        onSubmit={handleFormSubmit}
        style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="create-org-unit-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-level-select" className="orcia-ds-label">{labels.kindLabel}</label>
          <select
            id="org-unit-level-select"
            data-testid="org-unit-level-select"
            disabled={!canMutate || isSubmitting}
            value={kind}
            onChange={(e) => handleKindChange(e.target.value as "BU" | "TEAM")}
            className="orcia-ds-select"
            style={{ width: "100%" }}
          >
            <option value="BU">{labels.kindBuOption}</option>
            <option value="TEAM">{labels.kindTeamOption}</option>
          </select>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-name-input" className="orcia-ds-label">{labels.nameLabel}</label>
          <input
            id="org-unit-name-input"
            name="org_unit_title"
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="org-unit-name-input"
            disabled={!canMutate || isSubmitting}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={kind === "BU" ? labels.nameBuPlaceholder : labels.nameTeamPlaceholder}
            className="orcia-ds-input"
            style={{ width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-slug-input" className="orcia-ds-label">{labels.slugLabel}</label>
          <input
            id="org-unit-slug-input"
            name="org_unit_short_code"
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="org-unit-slug-input"
            disabled={!canMutate || isSubmitting}
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder={labels.slugPlaceholder}
            className="orcia-ds-input"
            style={{ width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-parent-select" className="orcia-ds-label">{labels.parentLabel}</label>
          <OrciaSearchableSelect
            id="org-unit-parent-select"
            testId="org-unit-parent-select"
            disabled={!canMutate || isSubmitting}
            value={parentId}
            onChange={setParentId}
            options={parentOptions}
            maxDisplayedItems={10}
            searchPlaceholder={labels.parentSearchPlaceholder}
            noMatchLabel={labels.parentNoMatchLabel}
            truncatedHintTemplate={(hidden) => `+${hidden} ${labels.parentTruncatedHint}`}
            onSearchQueryChange={onParentSearchChange}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-lead-input" className="orcia-ds-label">{labels.leadLabel}</label>
          <OrciaUserPillsSelect
            inputId="org-unit-lead-input"
            inputTestId="org-unit-lead-input"
            disabled={!canMutate || isSubmitting}
            selectedUserIds={leadUserIds}
            onChange={setLeadUserIds}
            draftQuery={leadDraft}
            onDraftQueryChange={(val) => { setLeadDraft(val); setLeadValidationError(null); }}
            knownUsers={leadSearch.knownUsers}
            placeholder={labels.leadPlaceholder}
          />
          {leadValidationError ? (
            <div data-testid="org-unit-unknown-user-error" style={{ fontSize: "12px", color: "var(--color-status-error)", marginTop: "2px" }}>
              {leadValidationError}
            </div>
          ) : null}
        </div>

        {kind === "BU" ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label htmlFor="org-unit-ontology-lead-input" className="orcia-ds-label">
              {labels.ontologyLeadLabel}
            </label>
            <OrciaUserPillsSelect
              inputId="org-unit-ontology-lead-input"
              inputTestId="org-unit-ontology-lead-input"
              disabled={!canMutate || isSubmitting}
              selectedUserIds={ontologyLeadUserIds}
              onChange={setOntologyLeadUserIds}
              draftQuery={ontologyLeadDraft}
              onDraftQueryChange={(val) => {
                setOntologyLeadDraft(val);
                setLeadValidationError(null);
              }}
              knownUsers={ontoSearch.knownUsers}
              placeholder={labels.ontologyLeadPlaceholder}
            />
          </div>
        ) : null}

        <label style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontSize: "13px", fontWeight: 600, cursor: canMutate ? "pointer" : "not-allowed" }}>
          <input
            type="checkbox"
            name="org_unit_billing_enabled"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="org-unit-billing-checkbox"
            disabled={!canMutate || isSubmitting}
            checked={billingEnabled}
            onChange={(e) => setBillingEnabled(e.target.checked)}
          />
          <span>{labels.billingCheckboxLabel}</span>
        </label>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
          <OrciaButton variant="secondary" testId="cancel-create-org-unit-btn" onClick={() => onOpenChange(false)}>
            {labels.cancelButton}
          </OrciaButton>
          <OrciaButton type="submit" variant="primary" testId="create-org-unit-btn" disabled={!canMutate || !name.trim() || isSubmitting}>
            {labels.submitButton}
          </OrciaButton>
        </div>
      </form>
    </OrciaDialog>
  );
}

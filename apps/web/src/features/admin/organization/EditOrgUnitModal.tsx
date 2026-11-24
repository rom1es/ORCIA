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
import { isKnownUserIdentifier } from "./orgUnitsApiBridge";
import { useKnownOrgUsersSearch } from "./useKnownOrgUsersSearch";
import { useParentOrgSearch } from "./useParentOrgSearch";

import type { OrgUnitServerCapabilities } from "./orgUnitsApiBridge";

export interface EditOrgUnitFormValues {
  readonly name: string;
  readonly parentId: string;
  readonly billingEnabled: boolean;
  readonly leadUserId?: string | null;
  readonly leadUserIds?: readonly string[];
  readonly ontologyLeadUserIds?: readonly string[];
}

export interface EditOrgUnitModalProps {
  readonly unit: ConfiguredOrgUnit | null;
  readonly unitCapabilities?: OrgUnitServerCapabilities;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly canMutate: boolean;
  readonly allowParentAndBillingEdit?: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly knownUsers?: readonly KnownUserOption[];
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"]["editModal"];
  readonly parentPrefixLabel: string;
  readonly unknownUserErrorLabel?: string;
  readonly errorMessage: string | null;
  readonly isSubmitting: boolean;
  readonly onSave: (orgUnitId: string, values: EditOrgUnitFormValues) => void;
}

export function EditOrgUnitModal({
  unit,
  unitCapabilities,
  open,
  onOpenChange,
  canMutate,
  allowParentAndBillingEdit = true,
  orgUnits,
  knownUsers = [],
  labels,
  parentPrefixLabel,
  unknownUserErrorLabel,
  errorMessage,
  isSubmitting,
  onSave,
}: EditOrgUnitModalProps): React.ReactElement {
  const {
    options: parentOptions,
    handleSearchQueryChange: onParentSearchChange,
    resetSearch: resetParentSearch,
  } = useParentOrgSearch({
    initialUnits: orgUnits,
    editingUnitId: unit?.id,
    rootParentOptionLabel: labels.rootParentOption,
    parentBuOptionPrefix: parentPrefixLabel,
  });

  const leadSearch = useKnownOrgUsersSearch({ initialKnownUsers: knownUsers });
  const ontoSearch = useKnownOrgUsersSearch({ initialKnownUsers: knownUsers });
  const [name, setName] = useState("");
  const [parentId, setParentId] = useState("scope-global");
  const [billingEnabled, setBillingEnabled] = useState(true);
  const [leadUserIds, setLeadUserIds] = useState<readonly string[]>([]);
  const [leadDraft, setLeadDraft] = useState("");
  const [ontologyLeadUserIds, setOntologyLeadUserIds] = useState<readonly string[]>([]);
  const [ontologyLeadDraft, setOntologyLeadDraft] = useState("");
  const [leadValidationError, setLeadValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (unit && open) {
      setName(unit.name);
      setParentId(unit.parentId || "scope-global");
      setBillingEnabled(unit.billingEnabled !== false);
      const initialLeads = Array.isArray(unit.leadUserIds) && unit.leadUserIds.length > 0
        ? unit.leadUserIds
        : (unit.leadUserId ? [unit.leadUserId] : []);
      setLeadUserIds(initialLeads);
      setLeadDraft("");
      setOntologyLeadUserIds(
        unit.level === "BU" && Array.isArray(unit.ontologyLeadUserIds)
          ? unit.ontologyLeadUserIds
          : [],
      );
      setOntologyLeadDraft("");
      setLeadValidationError(null);
      resetParentSearch();
    }
  }, [unit, open]);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!unit || !canMutate || !name.trim() || isSubmitting) return;
    const allKnownUsers = [...leadSearch.knownUsers, ...ontoSearch.knownUsers, ...knownUsers];
    const pendingId = resolvePendingKnownUserId(leadDraft, allKnownUsers);
    const finalLeads = pendingId && !leadUserIds.some((id) => id.toLowerCase() === pendingId.toLowerCase())
      ? [...leadUserIds, pendingId]
      : leadUserIds;
    const pendingOntoId = resolvePendingKnownUserId(ontologyLeadDraft, allKnownUsers);
    const finalOntoLeads =
      unit.level === "BU"
        ? pendingOntoId &&
          !ontologyLeadUserIds.some((id) => id.toLowerCase() === pendingOntoId.toLowerCase())
          ? [...ontologyLeadUserIds, pendingOntoId]
          : ontologyLeadUserIds
        : undefined;
    const invalidLead = [...finalLeads, ...(finalOntoLeads ?? [])].find(
      (lid) => !isKnownUserIdentifier(lid, allKnownUsers),
    );
    if (invalidLead) {
      setLeadValidationError(unknownUserErrorLabel ?? "");
      return;
    }
    onSave(unit.id, {
      name: name.trim(),
      parentId,
      billingEnabled,
      leadUserId: finalLeads[0] ?? null,
      leadUserIds: finalLeads,
      ontologyLeadUserIds: finalOntoLeads,
    });
  };

  return (
    <OrciaDialog
      open={open && unit !== null}
      onOpenChange={onOpenChange}
      title={labels.title}
      description={labels.description}
      testId="edit-org-unit-modal"
      closeLabel={labels.cancelButton}
      hideHeaderCloseButton
    >
      <form
        data-testid="edit-org-unit-form"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        onSubmit={handleFormSubmit}
        style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="edit-org-unit-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="edit-org-unit-name-input" className="orcia-ds-label">{labels.nameLabel}</label>
          <input
            id="edit-org-unit-name-input"
            name="org_unit_title"
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="edit-org-unit-name-input"
            disabled={!canMutate || isSubmitting}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="orcia-ds-input"
            style={{ width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="edit-org-unit-parent-select" className="orcia-ds-label">{labels.parentLabel}</label>
          <OrciaSearchableSelect
            id="edit-org-unit-parent-select"
            testId="edit-org-unit-parent-select"
            disabled={!canMutate || !allowParentAndBillingEdit || isSubmitting}
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
          <label htmlFor="edit-org-unit-lead-input" className="orcia-ds-label">{labels.leadLabel}</label>
          <OrciaUserPillsSelect
            inputId="edit-org-unit-lead-input"
            inputTestId="edit-org-unit-lead-input"
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

        {unit?.level === "BU" ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label htmlFor="edit-org-unit-ontology-lead-input" className="orcia-ds-label">
              {labels.ontologyLeadLabel}
            </label>
            <OrciaUserPillsSelect
              inputId="edit-org-unit-ontology-lead-input"
              inputTestId="edit-org-unit-ontology-lead-input"
              disabled={
                !canMutate ||
                isSubmitting ||
                (unitCapabilities ? !unitCapabilities.canManageOntologyLeads : false)
              }
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

        <label style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontSize: "13px", fontWeight: 600, cursor: canMutate && allowParentAndBillingEdit ? "pointer" : "not-allowed" }}>
          <input
            type="checkbox"
            name="org_unit_billing_enabled"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="edit-org-unit-billing-checkbox"
            disabled={!canMutate || !allowParentAndBillingEdit || isSubmitting}
            checked={billingEnabled}
            onChange={(e) => setBillingEnabled(e.target.checked)}
          />
          <span>{labels.billingCheckboxLabel}</span>
        </label>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
          <OrciaButton variant="secondary" testId="cancel-edit-org-unit-btn" onClick={() => onOpenChange(false)}>
            {labels.cancelButton}
          </OrciaButton>
          <OrciaButton type="submit" variant="primary" testId="save-edit-org-unit-btn" disabled={!canMutate || !name.trim() || isSubmitting}>
            {labels.saveButton}
          </OrciaButton>
        </div>
      </form>
    </OrciaDialog>
  );
}

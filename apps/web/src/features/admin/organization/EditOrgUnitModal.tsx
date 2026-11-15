import {
  OrciaAlertBanner,
  OrciaButton,
  OrciaDialog,
  OrciaSearchableSelect,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { AdminAndStudioDictionarySection } from "../../../i18n/locales/admin_and_studio_labels";
import { useParentOrgSearch } from "./useParentOrgSearch";

export interface EditOrgUnitFormValues {
  readonly name: string;
  readonly parentId: string;
  readonly billingEnabled: boolean;
}

export interface EditOrgUnitModalProps {
  readonly unit: ConfiguredOrgUnit | null;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly canMutate: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"]["editModal"];
  readonly parentPrefixLabel: string;
  readonly errorMessage: string | null;
  readonly isSubmitting: boolean;
  readonly onSave: (orgUnitId: string, values: EditOrgUnitFormValues) => void;
}

export function EditOrgUnitModal({
  unit,
  open,
  onOpenChange,
  canMutate,
  orgUnits,
  labels,
  parentPrefixLabel,
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

  const [name, setName] = useState("");
  const [parentId, setParentId] = useState("scope-global");
  const [billingEnabled, setBillingEnabled] = useState(true);

  useEffect(() => {
    if (unit && open) {
      setName(unit.name);
      setParentId(unit.parentId || "scope-global");
      setBillingEnabled(unit.billingEnabled !== false);
      resetParentSearch();
    }
  }, [unit, open]);

  return (
    <OrciaDialog
      open={open && unit !== null}
      onOpenChange={onOpenChange}
      title={labels.title}
      description={labels.description}
      testId="edit-org-unit-modal"
      closeLabel={labels.cancelButton}
    >
      <form
        data-testid="edit-org-unit-form"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        onSubmit={(e) => {
          e.preventDefault();
          if (!unit || !canMutate || !name.trim() || isSubmitting) return;
          onSave(unit.id, {
            name: name.trim(),
            parentId,
            billingEnabled,
          });
        }}
        style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="edit-org-unit-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="edit-org-unit-name-input" className="orcia-ds-label">
            {labels.nameLabel}
          </label>
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
          <label htmlFor="edit-org-unit-parent-select" className="orcia-ds-label">
            {labels.parentLabel}
          </label>
          <OrciaSearchableSelect
            id="edit-org-unit-parent-select"
            testId="edit-org-unit-parent-select"
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

        <label
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "13px",
            fontWeight: 600,
            cursor: canMutate ? "pointer" : "not-allowed",
          }}
        >
          <input
            type="checkbox"
            name="org_unit_billing_enabled"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="edit-org-unit-billing-checkbox"
            disabled={!canMutate || isSubmitting}
            checked={billingEnabled}
            onChange={(e) => setBillingEnabled(e.target.checked)}
          />
          <span>{labels.billingCheckboxLabel}</span>
        </label>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
          <OrciaButton
            variant="secondary"
            testId="cancel-edit-org-unit-btn"
            onClick={() => onOpenChange(false)}
          >
            {labels.cancelButton}
          </OrciaButton>
          <OrciaButton
            type="submit"
            variant="primary"
            testId="save-edit-org-unit-btn"
            disabled={!canMutate || !name.trim() || isSubmitting}
          >
            {labels.saveButton}
          </OrciaButton>
        </div>
      </form>
    </OrciaDialog>
  );
}

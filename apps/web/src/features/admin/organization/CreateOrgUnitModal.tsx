import { OrciaAlertBanner, OrciaButton, OrciaDialog } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { AdminAndStudioDictionarySection } from "../../../i18n/locales/admin_and_studio_labels";
import { getEligibleParentBuUnits } from "./orgTreeHelpers";

export interface CreateOrgUnitFormValues {
  readonly kind: "BU" | "TEAM";
  readonly name: string;
  readonly slug: string;
  readonly parentId: string;
  readonly billingEnabled: boolean;
  readonly leadUserId: string;
}

export interface CreateOrgUnitModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly canMutate: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"]["createModal"];
  readonly errorMessage: string | null;
  readonly isSubmitting: boolean;
  readonly onSubmit: (values: CreateOrgUnitFormValues) => void;
}

export function CreateOrgUnitModal({
  open,
  onOpenChange,
  canMutate,
  orgUnits,
  labels,
  errorMessage,
  isSubmitting,
  onSubmit,
}: CreateOrgUnitModalProps): React.ReactElement {
  const buUnits = getEligibleParentBuUnits(orgUnits);
  const firstBuId = buUnits[0]?.id ?? "scope-global";

  const [kind, setKind] = useState<"BU" | "TEAM">("BU");
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [parentId, setParentId] = useState("scope-global");
  const [billingEnabled, setBillingEnabled] = useState(true);
  const [leadUserId, setLeadUserId] = useState("");

  useEffect(() => {
    if (open) {
      setKind("BU");
      setName("");
      setSlug("");
      setParentId("scope-global");
      setBillingEnabled(true);
      setLeadUserId("");
    }
  }, [open]);

  const handleKindChange = (nextKind: "BU" | "TEAM") => {
    setKind(nextKind);
    if (nextKind === "TEAM") {
      setParentId(buUnits.length > 0 ? firstBuId : "scope-global");
    } else {
      setParentId("scope-global");
    }
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
        onSubmit={(e) => {
          e.preventDefault();
          if (!canMutate || !name.trim() || isSubmitting) return;
          onSubmit({
            kind,
            name: name.trim(),
            slug: slug.trim(),
            parentId,
            billingEnabled,
            leadUserId: leadUserId.trim(),
          });
        }}
        style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="create-org-unit-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-level-select" className="orcia-ds-label">
            {labels.kindLabel}
          </label>
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
          <label htmlFor="org-unit-name-input" className="orcia-ds-label">
            {labels.nameLabel}
          </label>
          <input
            id="org-unit-name-input"
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
          <label htmlFor="org-unit-slug-input" className="orcia-ds-label">
            {labels.slugLabel}
          </label>
          <input
            id="org-unit-slug-input"
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
          <label htmlFor="org-unit-parent-select" className="orcia-ds-label">
            {labels.parentLabel}
          </label>
          <select
            id="org-unit-parent-select"
            data-testid="org-unit-parent-select"
            aria-label={labels.parentLabel}
            disabled={!canMutate || isSubmitting}
            value={parentId}
            onChange={(e) => setParentId(e.target.value)}
            className="orcia-ds-select"
            style={{ width: "100%" }}
          >
            <option value="scope-global">{labels.rootParentOption}</option>
            {buUnits.map((bu) => (
              <option key={bu.id} value={bu.id}>
                {`${labels.parentBuOptionPrefix} ${bu.name}`}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-lead-input" className="orcia-ds-label">
            {labels.leadLabel}
          </label>
          <input
            id="org-unit-lead-input"
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="org-unit-lead-input"
            disabled={!canMutate || isSubmitting}
            value={leadUserId}
            onChange={(e) => setLeadUserId(e.target.value)}
            placeholder={labels.leadPlaceholder}
            className="orcia-ds-input"
            style={{ width: "100%" }}
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
          <OrciaButton
            variant="secondary"
            testId="cancel-create-org-unit-btn"
            onClick={() => onOpenChange(false)}
          >
            {labels.cancelButton}
          </OrciaButton>
          <OrciaButton
            type="submit"
            variant="primary"
            testId="create-org-unit-btn"
            disabled={!canMutate || !name.trim() || isSubmitting}
          >
            {labels.submitButton}
          </OrciaButton>
        </div>
      </form>
    </OrciaDialog>
  );
}

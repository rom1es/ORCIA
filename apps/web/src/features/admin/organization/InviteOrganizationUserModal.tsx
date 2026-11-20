import {
  OrciaAlertBanner,
  OrciaButton,
  OrciaDialog,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { OrganizationInviteModalLabels } from "../../../i18n/locales/organization_modals_labels";

export type OrgInviteAssignmentRole =
  | "CONTRIBUTOR"
  | "TEAM_MEMBER"
  | "OBSERVER"
  | "TEAM_LEAD"
  | "BU_LEAD"
  | "ONTOLOGY_LEAD";

export interface InviteOrganizationUserFormValues {
  readonly targetOrgUnitId: string;
  readonly email: string;
  readonly displayName: string;
  readonly assignmentRole: OrgInviteAssignmentRole;
}

export interface InviteOrganizationUserModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly invitableUnits: readonly ConfiguredOrgUnit[];
  readonly initialTargetUnitId?: string | null;
  readonly labels: OrganizationInviteModalLabels;
  readonly errorMessage: string | null;
  readonly isSubmitting: boolean;
  readonly onSubmit: (values: InviteOrganizationUserFormValues) => void;
}

export function InviteOrganizationUserModal({
  open,
  onOpenChange,
  invitableUnits,
  initialTargetUnitId,
  labels,
  errorMessage,
  isSubmitting,
  onSubmit,
}: InviteOrganizationUserModalProps): React.ReactElement {
  const [targetOrgUnitId, setTargetOrgUnitId] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [displayName, setDisplayName] = useState<string>("");
  const [assignmentRole, setAssignmentRole] = useState<OrgInviteAssignmentRole>("CONTRIBUTOR");

  useEffect(() => {
    if (!open) return;
    const defaultUnit =
      (initialTargetUnitId && invitableUnits.find((u) => u.id === initialTargetUnitId)) ||
      invitableUnits[0];
    const nextUnitId = defaultUnit?.id ?? "";
    setTargetOrgUnitId(nextUnitId);
    setEmail("");
    setDisplayName("");
    setAssignmentRole(defaultUnit?.level === "BU" ? "BU_LEAD" : "CONTRIBUTOR");
  }, [open, initialTargetUnitId, invitableUnits]);

  const selectedUnit = invitableUnits.find((u) => u.id === targetOrgUnitId) ?? invitableUnits[0];
  const isBu = selectedUnit?.level === "BU";

  const availableRoles: readonly { readonly value: OrgInviteAssignmentRole; readonly label: string }[] = isBu
    ? [
        { value: "BU_LEAD", label: labels.roleOptions.BU_LEAD },
        { value: "ONTOLOGY_LEAD", label: labels.roleOptions.ONTOLOGY_LEAD },
      ]
    : [
        { value: "CONTRIBUTOR", label: labels.roleOptions.TEAM_MEMBER },
        { value: "TEAM_LEAD", label: labels.roleOptions.TEAM_LEAD },
        { value: "OBSERVER", label: labels.roleOptions.OBSERVER },
      ];

  const handleUnitChange = (nextUnitId: string) => {
    setTargetOrgUnitId(nextUnitId);
    const nextUnit = invitableUnits.find((u) => u.id === nextUnitId);
    if (nextUnit?.level === "BU") {
      if (assignmentRole !== "BU_LEAD" && assignmentRole !== "ONTOLOGY_LEAD") {
        setAssignmentRole("BU_LEAD");
      }
    } else if (assignmentRole === "BU_LEAD" || assignmentRole === "ONTOLOGY_LEAD") {
      setAssignmentRole("CONTRIBUTOR");
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetOrgUnitId || !email.trim() || !displayName.trim() || isSubmitting) return;
    onSubmit({
      targetOrgUnitId,
      email: email.trim(),
      displayName: displayName.trim(),
      assignmentRole,
    });
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={labels.title}
      description={labels.description}
      testId="invite-org-user-modal"
      closeLabel={labels.cancelButton}
      hideHeaderCloseButton
    >
      <form
        data-testid="invite-org-user-form"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        onSubmit={handleSubmit}
        style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="invite-org-user-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="invite-org-unit-select" className="orcia-ds-label">
            {labels.targetUnitLabel}
          </label>
          <select
            id="invite-org-unit-select"
            data-testid="invite-org-unit-select"
            className="orcia-ds-select"
            disabled={isSubmitting || invitableUnits.length === 0}
            value={targetOrgUnitId}
            onChange={(e) => handleUnitChange(e.target.value)}
            style={{ width: "100%" }}
          >
            {invitableUnits.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name} ({unit.level})
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="invite-org-user-display-name" className="orcia-ds-label">
            {labels.displayNameLabel}
          </label>
          <input
            id="invite-org-user-display-name"
            name="org_invited_display_name"
            data-testid="invite-org-user-display-name"
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            className="orcia-ds-input"
            disabled={isSubmitting}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder={labels.displayNamePlaceholder}
            style={{ width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="invite-org-user-email" className="orcia-ds-label">
            {labels.emailLabel}
          </label>
          <input
            id="invite-org-user-email"
            name="org_invited_contact_ref"
            data-testid="invite-org-user-email"
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            className="orcia-ds-input"
            disabled={isSubmitting}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={labels.emailPlaceholder}
            style={{ width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="invite-org-user-role-select" className="orcia-ds-label">
            {labels.roleLabel}
          </label>
          <select
            id="invite-org-user-role-select"
            data-testid="invite-org-user-role-select"
            className="orcia-ds-select"
            disabled={isSubmitting}
            value={assignmentRole}
            onChange={(e) => setAssignmentRole(e.target.value as OrgInviteAssignmentRole)}
            style={{ width: "100%" }}
          >
            {availableRoles.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <OrciaAlertBanner tone="cobalt" testId="invite-org-user-security-hint">
          {labels.securityHint}
        </OrciaAlertBanner>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
          <OrciaButton
            variant="secondary"
            testId="cancel-invite-org-user-btn"
            onClick={() => onOpenChange(false)}
          >
            {labels.cancelButton}
          </OrciaButton>
          <OrciaButton
            type="submit"
            variant="primary"
            testId="submit-invite-org-user-btn"
            disabled={!targetOrgUnitId || !email.trim() || !displayName.trim() || isSubmitting}
          >
            {labels.submitButton}
          </OrciaButton>
        </div>
      </form>
    </OrciaDialog>
  );
}

import {
  OrciaAlertBanner,
  OrciaButton,
  OrciaDialog,
  OrciaKnownUserCombobox,
  StatusBadge,
  type KnownUserOption,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { AdminAndStudioDictionarySection } from "../../../i18n/locales/admin_and_studio_labels";
import { isKnownUserIdentifier } from "./orgUnitsApiBridge";

export interface ManageOrgUnitMembersModalProps {
  readonly unit: ConfiguredOrgUnit | null;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly canMutate: boolean;
  readonly knownUsers?: readonly KnownUserOption[];
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"]["membersModal"];
  readonly unknownUserErrorLabel?: string;
  readonly errorMessage: string | null;
  readonly isSubmitting: boolean;
  readonly onSave: (
    orgUnitId: string,
    values: { readonly leadUserId: string | null; readonly memberUserIds: readonly string[] },
  ) => void;
}

export function ManageOrgUnitMembersModal({
  unit,
  open,
  onOpenChange,
  canMutate,
  knownUsers = [],
  labels,
  unknownUserErrorLabel,
  errorMessage,
  isSubmitting,
  onSave,
}: ManageOrgUnitMembersModalProps): React.ReactElement {
  const [leadUserId, setLeadUserId] = useState("");
  const [memberUserIds, setMemberUserIds] = useState<readonly string[]>([]);
  const [newMemberDraft, setNewMemberDraft] = useState("");
  const [leadValidationError, setLeadValidationError] = useState<string | null>(null);
  const [memberValidationError, setMemberValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (unit && open) {
      setLeadUserId(unit.leadUserId ?? "");
      setMemberUserIds(unit.memberUserIds ?? []);
      setNewMemberDraft("");
      setLeadValidationError(null);
      setMemberValidationError(null);
    }
  }, [unit, open]);

  const handleAddMember = () => {
    const trimmed = newMemberDraft.trim();
    if (!trimmed) return;
    if (!isKnownUserIdentifier(trimmed, knownUsers)) {
      setMemberValidationError(
        unknownUserErrorLabel ||
          "L'identifiant saisi ne correspond à aucun utilisateur actif et connu de la plateforme.",
      );
      return;
    }
    const resolvedUser = knownUsers.find(
      (u) =>
        u.principalId.toLowerCase() === trimmed.toLowerCase() ||
        (u.email && u.email.toLowerCase() === trimmed.toLowerCase()),
    );
    const canonicalId = resolvedUser ? resolvedUser.principalId : trimmed;
    if (!memberUserIds.includes(canonicalId)) {
      setMemberUserIds([...memberUserIds, canonicalId]);
    }
    setNewMemberDraft("");
    setMemberValidationError(null);
  };

  const handleRemoveMember = (targetMember: string) => {
    setMemberUserIds(memberUserIds.filter((m) => m !== targetMember));
  };

  return (
    <OrciaDialog
      open={open && unit !== null}
      onOpenChange={onOpenChange}
      title={unit ? `${labels.titlePrefix} ${unit.name}` : labels.titlePrefix}
      description={labels.description}
      testId="manage-org-unit-members-modal"
      closeLabel={labels.cancelButton}
    >
      <form
        data-testid="manage-org-unit-members-form"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        onSubmit={(e) => {
          e.preventDefault();
          if (!unit || !canMutate || isSubmitting) return;
          const trimmedLead = leadUserId.trim();
          if (trimmedLead && !isKnownUserIdentifier(trimmedLead, knownUsers)) {
            setLeadValidationError(
              unknownUserErrorLabel ||
                "L'identifiant saisi ne correspond à aucun utilisateur actif et connu de la plateforme.",
            );
            return;
          }
          const pendingMember = newMemberDraft.trim();
          let finalMembers = [...memberUserIds];
          if (pendingMember) {
            if (!isKnownUserIdentifier(pendingMember, knownUsers)) {
              setMemberValidationError(
                unknownUserErrorLabel ||
                  "L'identifiant saisi ne correspond à aucun utilisateur actif et connu de la plateforme.",
              );
              return;
            }
            const resolvedUser = knownUsers.find(
              (u) =>
                u.principalId.toLowerCase() === pendingMember.toLowerCase() ||
                (u.email && u.email.toLowerCase() === pendingMember.toLowerCase()),
            );
            const canonicalId = resolvedUser ? resolvedUser.principalId : pendingMember;
            if (!finalMembers.includes(canonicalId)) {
              finalMembers.push(canonicalId);
            }
          }
          const resolvedLeadUser = knownUsers.find(
            (u) =>
              u.principalId.toLowerCase() === trimmedLead.toLowerCase() ||
              (u.email && u.email.toLowerCase() === trimmedLead.toLowerCase()),
          );
          const canonicalLead = resolvedLeadUser
            ? resolvedLeadUser.principalId
            : trimmedLead || null;
          onSave(unit.id, {
            leadUserId: canonicalLead,
            memberUserIds: finalMembers,
          });
        }}
        style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="manage-org-unit-members-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-members-lead-input" className="orcia-ds-label">
            {labels.leadLabel}
          </label>
          <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            {unit?.level === "BU" ? labels.leadBuHint : labels.leadTeamHint}
          </span>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <OrciaKnownUserCombobox
              inputId="org-unit-members-lead-input"
              inputTestId="org-unit-members-lead-input"
              disabled={!canMutate || isSubmitting}
              value={leadUserId}
              onChange={(val) => {
                setLeadUserId(val);
                setLeadValidationError(null);
              }}
              knownUsers={knownUsers}
              placeholder={labels.leadPlaceholder}
              style={{ flex: 1 }}
            />
            {leadUserId.trim().length > 0 ? (
              <OrciaButton
                variant="secondary"
                testId="org-unit-clear-lead-btn"
                disabled={!canMutate || isSubmitting}
                onClick={() => {
                  setLeadUserId("");
                  setLeadValidationError(null);
                }}
              >
                {labels.clearLeadButton}
              </OrciaButton>
            ) : null}
          </div>
          {leadValidationError ? (
            <div
              data-testid="org-unit-unknown-user-error"
              style={{
                fontSize: "12px",
                color: "var(--color-status-error)",
                marginTop: "2px",
              }}
            >
              {leadValidationError}
            </div>
          ) : null}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-add-member-input" className="orcia-ds-label">
            {labels.addMemberLabel}
          </label>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <OrciaKnownUserCombobox
              inputId="org-unit-add-member-input"
              inputTestId="org-unit-add-member-input"
              disabled={!canMutate || isSubmitting}
              value={newMemberDraft}
              onChange={(val) => {
                setNewMemberDraft(val);
                setMemberValidationError(null);
              }}
              knownUsers={knownUsers}
              excludedPrincipalIds={memberUserIds}
              placeholder={labels.addMemberPlaceholder}
              style={{ flex: 1 }}
            />
            <OrciaButton
              variant="secondary"
              testId="org-unit-add-member-btn"
              disabled={!canMutate || !newMemberDraft.trim() || isSubmitting}
              onClick={handleAddMember}
            >
              {labels.addMemberButton}
            </OrciaButton>
          </div>
          {memberValidationError ? (
            <div
              data-testid="org-unit-unknown-user-error"
              style={{
                fontSize: "12px",
                color: "var(--color-status-error)",
                marginTop: "2px",
              }}
            >
              {memberValidationError}
            </div>
          ) : null}
        </div>

        <div
          data-testid="org-unit-members-list"
          style={{ display: "flex", flexDirection: "column", gap: "6px" }}
        >
          <span className="orcia-ds-label">
            {`${labels.membersListTitle} (${memberUserIds.length})`}
          </span>
          {memberUserIds.length === 0 ? (
            <p
              data-testid="org-unit-members-empty"
              style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}
            >
              {labels.emptyMembersText}
            </p>
          ) : (
            memberUserIds.map((memberId) => {
              const known = knownUsers.find(
                (u) =>
                  u.principalId.toLowerCase() === memberId.toLowerCase() ||
                  (u.email && u.email.toLowerCase() === memberId.toLowerCase()),
              );
              const labelText =
                known && known.displayName && known.displayName !== memberId
                  ? `${known.displayName} (${memberId})`
                  : memberId;
              return (
                <div
                  key={memberId}
                  data-testid={`org-unit-member-item-${memberId}`}
                  className="orcia-ds-row"
                  style={{ justifyContent: "space-between" }}
                >
                  <StatusBadge label={labelText} tone="cobalt" />
                  <OrciaButton
                    variant="danger"
                    testId={`org-unit-remove-member-btn-${memberId}`}
                    disabled={!canMutate || isSubmitting}
                    onClick={() => handleRemoveMember(memberId)}
                  >
                    {labels.removeMemberButton}
                  </OrciaButton>
                </div>
              );
            })
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
          <OrciaButton
            variant="secondary"
            testId="cancel-org-unit-members-btn"
            onClick={() => onOpenChange(false)}
          >
            {labels.cancelButton}
          </OrciaButton>
          <OrciaButton
            type="submit"
            variant="primary"
            testId="save-org-unit-members-btn"
            disabled={!canMutate || isSubmitting}
          >
            {labels.saveButton}
          </OrciaButton>
        </div>
      </form>
    </OrciaDialog>
  );
}

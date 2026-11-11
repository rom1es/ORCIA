import { OrciaAlertBanner, OrciaButton, OrciaDialog, StatusBadge } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { AdminAndStudioDictionarySection } from "../../../i18n/locales/admin_and_studio_labels";

export interface ManageOrgUnitMembersModalProps {
  readonly unit: ConfiguredOrgUnit | null;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly canMutate: boolean;
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"]["membersModal"];
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
  labels,
  errorMessage,
  isSubmitting,
  onSave,
}: ManageOrgUnitMembersModalProps): React.ReactElement {
  const [leadUserId, setLeadUserId] = useState("");
  const [memberUserIds, setMemberUserIds] = useState<readonly string[]>([]);
  const [newMemberDraft, setNewMemberDraft] = useState("");

  useEffect(() => {
    if (unit && open) {
      setLeadUserId(unit.leadUserId ?? "");
      setMemberUserIds(unit.memberUserIds ?? []);
      setNewMemberDraft("");
    }
  }, [unit, open]);

  const handleAddMember = () => {
    const trimmed = newMemberDraft.trim();
    if (!trimmed) return;
    if (!memberUserIds.includes(trimmed)) {
      setMemberUserIds([...memberUserIds, trimmed]);
    }
    setNewMemberDraft("");
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
          const pendingMember = newMemberDraft.trim();
          const finalMembers =
            pendingMember && !memberUserIds.includes(pendingMember)
              ? [...memberUserIds, pendingMember]
              : memberUserIds;
          onSave(unit.id, {
            leadUserId: leadUserId.trim() || null,
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
            <input
              id="org-unit-members-lead-input"
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="org-unit-members-lead-input"
              disabled={!canMutate || isSubmitting}
              value={leadUserId}
              onChange={(e) => setLeadUserId(e.target.value)}
              placeholder={labels.leadPlaceholder}
              className="orcia-ds-input"
              style={{ flex: 1 }}
            />
            {leadUserId.trim().length > 0 ? (
              <OrciaButton
                variant="secondary"
                testId="org-unit-clear-lead-btn"
                disabled={!canMutate || isSubmitting}
                onClick={() => setLeadUserId("")}
              >
                {labels.clearLeadButton}
              </OrciaButton>
            ) : null}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-add-member-input" className="orcia-ds-label">
            {labels.addMemberLabel}
          </label>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <input
              id="org-unit-add-member-input"
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="org-unit-add-member-input"
              disabled={!canMutate || isSubmitting}
              value={newMemberDraft}
              onChange={(e) => setNewMemberDraft(e.target.value)}
              placeholder={labels.addMemberPlaceholder}
              className="orcia-ds-input"
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
            memberUserIds.map((memberId) => (
              <div
                key={memberId}
                data-testid={`org-unit-member-item-${memberId}`}
                className="orcia-ds-row"
                style={{ justifyContent: "space-between" }}
              >
                <StatusBadge label={memberId} tone="cobalt" />
                <OrciaButton
                  variant="danger"
                  testId={`org-unit-remove-member-btn-${memberId}`}
                  disabled={!canMutate || isSubmitting}
                  onClick={() => handleRemoveMember(memberId)}
                >
                  {labels.removeMemberButton}
                </OrciaButton>
              </div>
            ))
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

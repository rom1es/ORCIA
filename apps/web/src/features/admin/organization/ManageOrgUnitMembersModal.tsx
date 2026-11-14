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
import type { OrganizationMembersModalLabels } from "../../../i18n/locales/organization_modals_labels";
import { OrgUnitInlineCreateMemberModal } from "./OrgUnitInlineCreateMemberModal";
import { isKnownUserIdentifier } from "./orgUnitsApiBridge";
import { useKnownOrgUsersSearch } from "./useKnownOrgUsersSearch";

export interface ManageOrgUnitMembersModalProps {
  readonly unit: ConfiguredOrgUnit | null;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly canMutate: boolean;
  readonly knownUsers?: readonly KnownUserOption[];
  readonly labels: OrganizationMembersModalLabels;
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
  const usersSearch = useKnownOrgUsersSearch({ initialKnownUsers: knownUsers });
  const [leadUserId, setLeadUserId] = useState("");
  const [memberUserIds, setMemberUserIds] = useState<readonly string[]>([]);
  const [newMemberDraft, setNewMemberDraft] = useState("");
  const [leadValidationError, setLeadValidationError] = useState<string | null>(null);
  const [memberValidationError, setMemberValidationError] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [inlineCreateOpen, setInlineCreateOpen] = useState(false);

  useEffect(() => {
    if (unit && open) {
      setLeadUserId(unit.leadUserId ?? "");
      setMemberUserIds(unit.memberUserIds ?? []);
      setNewMemberDraft("");
      setLeadValidationError(null);
      setMemberValidationError(null);
      setFeedbackMessage(null);
      setInlineCreateOpen(false);
    }
  }, [unit, open]);

  const allAvailableUsers = [...usersSearch.knownUsers, ...knownUsers];
  const defaultUnknownError =
    unknownUserErrorLabel || "L'identifiant saisi ne correspond à aucun utilisateur actif et connu.";

  const handleAddMember = () => {
    const trimmed = newMemberDraft.trim();
    if (!trimmed) return;
    if (!isKnownUserIdentifier(trimmed, allAvailableUsers)) {
      setMemberValidationError(defaultUnknownError);
      return;
    }
    const resolved = allAvailableUsers.find(
      (u) =>
        u.principalId.toLowerCase() === trimmed.toLowerCase() ||
        (u.email && u.email.toLowerCase() === trimmed.toLowerCase()),
    );
    const canonicalId = resolved ? resolved.principalId : trimmed;
    if (!memberUserIds.includes(canonicalId)) setMemberUserIds([...memberUserIds, canonicalId]);
    setNewMemberDraft("");
    setMemberValidationError(null);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!unit || !canMutate || isSubmitting) return;
    const trimmedLead = leadUserId.trim();
    if (trimmedLead && !isKnownUserIdentifier(trimmedLead, allAvailableUsers)) {
      setLeadValidationError(defaultUnknownError);
      return;
    }
    const pending = newMemberDraft.trim();
    const finalMembers = [...memberUserIds];
    if (pending) {
      if (!isKnownUserIdentifier(pending, allAvailableUsers)) {
        setMemberValidationError(defaultUnknownError);
        return;
      }
      const res = allAvailableUsers.find(
        (u) =>
          u.principalId.toLowerCase() === pending.toLowerCase() ||
          (u.email && u.email.toLowerCase() === pending.toLowerCase()),
      );
      const canon = res ? res.principalId : pending;
      if (!finalMembers.includes(canon)) finalMembers.push(canon);
    }
    const resLead = allAvailableUsers.find(
      (u) =>
        u.principalId.toLowerCase() === trimmedLead.toLowerCase() ||
        (u.email && u.email.toLowerCase() === trimmedLead.toLowerCase()),
    );
    onSave(unit.id, {
      leadUserId: resLead ? resLead.principalId : trimmedLead || null,
      memberUserIds: finalMembers,
    });
  };

  return (
    <>
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
          data-form-type="other"
          data-1p-ignore="true"
          data-bwignore="true"
          onSubmit={handleFormSubmit}
          style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}
        >
          {errorMessage ? (
            <OrciaAlertBanner tone="crimson" testId="manage-org-unit-members-error-banner">
              {errorMessage}
            </OrciaAlertBanner>
          ) : null}
          {feedbackMessage ? (
            <OrciaAlertBanner tone="emerald" testId="org-unit-new-member-feedback">
              {feedbackMessage}
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
                onChange={(val) => { setLeadUserId(val); setLeadValidationError(null); }}
                onSearchQueryChange={usersSearch.onSearchQueryChange}
                knownUsers={usersSearch.knownUsers}
                maxDisplayedItems={10}
                hasMoreMatches={usersSearch.hasMore}
                truncatedHint={labels.memberTruncatedHint}
                placeholder={labels.leadPlaceholder}
                style={{ flex: 1 }}
              />
              {leadUserId.trim().length > 0 ? (
                <OrciaButton
                  variant="secondary"
                  testId="org-unit-clear-lead-btn"
                  disabled={!canMutate || isSubmitting}
                  onClick={() => { setLeadUserId(""); setLeadValidationError(null); }}
                >
                  {labels.clearLeadButton}
                </OrciaButton>
              ) : null}
            </div>
            {leadValidationError ? (
              <div data-testid="org-unit-unknown-user-error" style={{ fontSize: "12px", color: "var(--color-status-error)" }}>
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
                onChange={(val) => { setNewMemberDraft(val); setMemberValidationError(null); }}
                onSearchQueryChange={usersSearch.onSearchQueryChange}
                knownUsers={usersSearch.knownUsers}
                excludedPrincipalIds={memberUserIds}
                maxDisplayedItems={10}
                hasMoreMatches={usersSearch.hasMore}
                truncatedHint={labels.memberTruncatedHint}
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
              <OrciaButton
                variant="secondary"
                testId="org-unit-new-member-btn"
                disabled={!canMutate || isSubmitting}
                onClick={() => setInlineCreateOpen(true)}
              >
                {labels.newMemberButtonLabel || "+ Nouveau membre"}
              </OrciaButton>
            </div>
            {memberValidationError ? (
              <div data-testid="org-unit-unknown-user-error" style={{ fontSize: "12px", color: "var(--color-status-error)" }}>
                {memberValidationError}
              </div>
            ) : null}
          </div>

          <div data-testid="org-unit-members-list" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span className="orcia-ds-label">{`${labels.membersListTitle} (${memberUserIds.length})`}</span>
            {memberUserIds.length === 0 ? (
              <p data-testid="org-unit-members-empty" style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}>
                {labels.emptyMembersText}
              </p>
            ) : (
              memberUserIds.map((mId) => {
                const u = allAvailableUsers.find(
                  (x) => x.principalId.toLowerCase() === mId.toLowerCase() || (x.email && x.email.toLowerCase() === mId.toLowerCase()),
                );
                const txt = u && u.displayName && u.displayName !== mId ? `${u.displayName} (${mId})` : mId;
                return (
                  <div key={mId} data-testid={`org-unit-member-item-${mId}`} className="orcia-ds-row" style={{ justifyContent: "space-between" }}>
                    <StatusBadge label={txt} tone="cobalt" />
                    <OrciaButton
                      variant="danger"
                      testId={`org-unit-remove-member-btn-${mId}`}
                      disabled={!canMutate || isSubmitting}
                      onClick={() => setMemberUserIds(memberUserIds.filter((m) => m !== mId))}
                    >
                      {labels.removeMemberButton}
                    </OrciaButton>
                  </div>
                );
              })
            )}
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
            <OrciaButton variant="secondary" testId="cancel-org-unit-members-btn" onClick={() => onOpenChange(false)}>
              {labels.cancelButton}
            </OrciaButton>
            <OrciaButton type="submit" variant="primary" testId="save-org-unit-members-btn" disabled={!canMutate || isSubmitting}>
              {labels.saveButton}
            </OrciaButton>
          </div>
        </form>
      </OrciaDialog>

      {unit && inlineCreateOpen ? (
        <OrgUnitInlineCreateMemberModal
          unit={unit}
          open={inlineCreateOpen}
          onOpenChange={setInlineCreateOpen}
          canMutate={canMutate}
          draftInput={newMemberDraft}
          onMemberCreated={(newUser) => {
            usersSearch.addKnownUserLocally(newUser);
            if (!memberUserIds.includes(newUser.principalId)) {
              setMemberUserIds([...memberUserIds, newUser.principalId]);
            }
            setNewMemberDraft("");
            setMemberValidationError(null);
            setFeedbackMessage(labels.newMemberCreatedFeedback || "Nouveau membre créé et rattaché avec succès.");
          }}
        />
      ) : null}
    </>
  );
}

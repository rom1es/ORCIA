import React from "react";
import { useI18n } from "../../../i18n";
import { FormInput, modalInputStyle } from "./WorkspaceSourceAttachCodegraphFields";

export interface WorkspaceSourceAttachSyncFieldsProps {
  readonly targetScope: string;
  readonly targetRef: string;
  readonly syncMode: "POLLING_24H" | "WEBHOOK_PUSH";
  readonly syncIdentityMode: "SERVICE_ACCOUNT" | "TEAM_REFERENT_USER";
  readonly referentUserId: string;
  readonly serviceAccountId: string;
  readonly copy: {
    readonly targetScopeLabel: string;
    readonly targetRefLabel: string;
    readonly syncModeLabel: string;
    readonly ragIdentityLabel: string;
    readonly ragServiceAccount: string;
    readonly ragReferentUser: string;
    readonly referentUserIdLabel: string;
    readonly serviceAccountIdLabel: string;
  };
  readonly onTargetScopeChange: (val: string) => void;
  readonly onTargetRefChange: (val: string) => void;
  readonly onSyncModeChange: (val: "POLLING_24H" | "WEBHOOK_PUSH") => void;
  readonly onSyncIdentityModeChange: (val: "SERVICE_ACCOUNT" | "TEAM_REFERENT_USER") => void;
  readonly onReferentUserIdChange: (val: string) => void;
  readonly onServiceAccountIdChange: (val: string) => void;
}

export function WorkspaceSourceAttachSyncFields({
  targetScope,
  targetRef,
  syncMode,
  syncIdentityMode,
  referentUserId,
  serviceAccountId,
  copy,
  onTargetScopeChange,
  onTargetRefChange,
  onSyncModeChange,
  onSyncIdentityModeChange,
  onReferentUserIdChange,
  onServiceAccountIdChange,
}: WorkspaceSourceAttachSyncFieldsProps): React.ReactElement {
  const { dictionary } = useI18n();
  const sourcesCopy = dictionary.featureWorkspaces.sources;
  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.targetScopeLabel}</label>
          <FormInput
            testId="modal-source-target-scope-input"
            type="text"
            value={targetScope}
            onChange={(e) => onTargetScopeChange(e.target.value)}
          />
        </div>
        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.targetRefLabel}</label>
          <FormInput
            testId="modal-source-target-ref-input"
            type="text"
            value={targetRef}
            onChange={(e) => onTargetRefChange(e.target.value)}
          />
        </div>
        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.syncModeLabel}</label>
          <select
            data-testid="modal-source-sync-mode-select"
            value={syncMode}
            onChange={(e) =>
              onSyncModeChange(e.target.value as "POLLING_24H" | "WEBHOOK_PUSH")
            }
            style={modalInputStyle}
          >
            <option value="POLLING_24H">{sourcesCopy.syncPolling24h}</option>
            <option value="WEBHOOK_PUSH">{sourcesCopy.syncWebhookPush}</option>
          </select>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.ragIdentityLabel}</label>
          <select
            data-testid="modal-source-rag-identity-select"
            value={syncIdentityMode}
            onChange={(e) =>
              onSyncIdentityModeChange(
                e.target.value as "SERVICE_ACCOUNT" | "TEAM_REFERENT_USER",
              )
            }
            style={modalInputStyle}
          >
            <option value="SERVICE_ACCOUNT">{copy.ragServiceAccount}</option>
            <option value="TEAM_REFERENT_USER">{copy.ragReferentUser}</option>
          </select>
        </div>
        <div>
          {syncIdentityMode === "TEAM_REFERENT_USER" ? (
            <>
              <label style={{ fontSize: "11px", fontWeight: 600 }}>
                {copy.referentUserIdLabel}
              </label>
              <FormInput
                testId="modal-source-referent-user-input"
                type="text"
                value={referentUserId}
                onChange={(e) => onReferentUserIdChange(e.target.value)}
              />
            </>
          ) : (
            <>
              <label style={{ fontSize: "11px", fontWeight: 600 }}>
                {copy.serviceAccountIdLabel}
              </label>
              <FormInput
                testId="modal-source-service-account-input"
                type="text"
                value={serviceAccountId}
                onChange={(e) => onServiceAccountIdChange(e.target.value)}
              />
            </>
          )}
        </div>
      </div>
    </>
  );
}

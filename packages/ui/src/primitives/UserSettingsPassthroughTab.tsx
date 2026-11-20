import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import type {
  UiUserPassthroughConnectorView,
  UserAccountDropdownAndSettingsLabels,
} from "./UserAccountDropdownTypes";

export interface UserSettingsPassthroughTabProps {
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly passthroughConnectors?: readonly UiUserPassthroughConnectorView[];
  readonly onSavePassthroughToken?: (
    connectorId: string,
    externalLogin: string,
    secretValue: string,
  ) => void | Promise<void>;
  readonly onRevokePassthroughToken?: (connectorId: string) => void | Promise<void>;
}

export function UserSettingsPassthroughTab({
  labels,
  passthroughConnectors,
  onSavePassthroughToken,
  onRevokePassthroughToken,
}: UserSettingsPassthroughTabProps): React.ReactElement {
  const [editingConnectorId, setEditingConnectorId] = useState<string | null>(null);
  const [draftLogin, setDraftLogin] = useState<string>("");
  const [draftToken, setDraftToken] = useState<string>("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleStartEdit = (conn: UiUserPassthroughConnectorView) => {
    setEditingConnectorId(conn.connectorId);
    setDraftLogin(conn.externalAuthorLogin || "");
    setDraftToken("");
    setStatusMessage(null);
  };

  const handleSave = async (connectorId: string) => {
    if (!draftToken.trim()) return;
    try {
      await onSavePassthroughToken?.(connectorId, draftLogin.trim(), draftToken.trim());
      setEditingConnectorId(null);
      setDraftToken("");
      setStatusMessage(labels.passthroughTokenSavedMessage);
    } catch (err: unknown) {
      if (typeof console !== "undefined") {
        console.debug("[orcia:passthrough.save]", err instanceof Error ? err.message : String(err));
      }
      setStatusMessage(labels.passthroughTokenSaveError);
    }
  };

  const handleRevoke = async (connectorId: string) => {
    try {
      await onRevokePassthroughToken?.(connectorId);
      setStatusMessage(labels.passthroughTokenRevokedMessage);
    } catch (err: unknown) {
      if (typeof console !== "undefined") {
        console.debug("[orcia:passthrough.revoke]", err instanceof Error ? err.message : String(err));
      }
      setStatusMessage(labels.passthroughTokenRevokeError);
    }
  };

  return (
    <div data-testid="user-settings-panel-PASSTHROUGH_SOURCES" className="space-y-3">
      <div className="rounded-lg border border-surface-border bg-surface-card p-3 space-y-1">
        <div className="font-semibold text-text-primary text-xs flex items-center gap-1.5">
          <OrciaIcon name="plug" size={14} />
          <span>{labels.passthroughAttributionTitle}</span>
        </div>
        <p className="text-text-secondary text-[11px]">{labels.passthroughAttributionSubtitle}</p>
      </div>

      {statusMessage && (
        <div
          data-testid="passthrough-status-banner"
          className="p-2 rounded text-xs bg-brand-primary/10 text-brand-primary border border-brand-primary/20"
        >
          {statusMessage}
        </div>
      )}

      {passthroughConnectors && passthroughConnectors.length > 0 ? (
        <div className="space-y-2">
          {passthroughConnectors.map((conn) => {
            const isEditing = editingConnectorId === conn.connectorId;
            return (
              <div
                key={conn.connectorId}
                data-testid={`user-passthrough-card-${conn.connectorId}`}
                className="p-3 rounded-lg border border-surface-border bg-surface-primary space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <strong className="text-xs text-text-primary">{conn.connectorName}</strong>
                    <div className="text-[10px] text-text-secondary font-mono">{conn.baseUrl}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {conn.connected ? (
                      <span
                        data-testid={`passthrough-connected-badge-${conn.connectorId}`}
                        className="px-2 py-0.5 rounded text-[10px] font-mono bg-status-success/10 text-status-success border border-status-success/20 flex items-center gap-1"
                      >
                        <OrciaIcon name="checkFilled" size={10} />
                        <span>{conn.secretStatus.fingerprint || "sha256:active"}</span>
                      </span>
                    ) : (
                      <span
                        data-testid={`passthrough-disconnected-badge-${conn.connectorId}`}
                        className="px-2 py-0.5 rounded text-[10px] text-text-secondary bg-surface-secondary border border-surface-border"
                      >
                        {labels.passthroughNotConnectedLabel}
                      </span>
                    )}
                  </div>
                </div>

                {isEditing ? (
                  <form
                    data-testid={`passthrough-edit-form-${conn.connectorId}`}
                    autoComplete="off"
                    data-lpignore="true"
                    data-form-type="other"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void handleSave(conn.connectorId);
                    }}
                    className="pt-2 border-t border-surface-border space-y-2"
                  >
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        autoComplete="off"
                        data-lpignore="true"
                        data-1p-ignore="true"
                        data-bwignore="true"
                        data-form-type="other"
                        data-testid={`passthrough-login-input-${conn.connectorId}`}
                        value={draftLogin}
                        onChange={(e) => setDraftLogin(e.target.value)}
                        placeholder={labels.passthroughLoginPlaceholder}
                        className="px-2 py-1 rounded text-xs border border-surface-border bg-surface-card text-text-primary"
                      />
                      <input
                        type="text"
                        autoComplete="off"
                        data-lpignore="true"
                        data-1p-ignore="true"
                        data-bwignore="true"
                        data-form-type="other"
                        data-testid={`passthrough-token-input-${conn.connectorId}`}
                        value={draftToken}
                        onChange={(e) => setDraftToken(e.target.value)}
                        placeholder={labels.passthroughTokenPlaceholder}
                        style={{ WebkitTextSecurity: "disc" } as React.CSSProperties}
                        className="px-2 py-1 rounded text-xs border border-surface-border bg-surface-card text-text-primary font-mono"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="submit"
                        data-testid={`passthrough-save-btn-${conn.connectorId}`}
                        disabled={!draftToken.trim()}
                        className="px-2.5 py-1 rounded text-xs bg-brand-primary text-surface-elevated font-medium disabled:opacity-50"
                      >
                        {labels.passthroughSaveTokenCta}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingConnectorId(null)}
                        className="px-2.5 py-1 rounded text-xs border border-surface-border text-text-secondary"
                      >
                        {labels.passthroughCancelCta}
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-text-secondary">
                      {conn.externalAuthorLogin
                        ? `@${conn.externalAuthorLogin}`
                        : labels.passthroughNoLoginLabel}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        data-testid={`passthrough-configure-btn-${conn.connectorId}`}
                        onClick={() => handleStartEdit(conn)}
                        className="px-2 py-1 rounded text-xs border border-surface-border bg-surface-secondary text-text-primary hover:bg-surface-card"
                      >
                        {conn.connected
                          ? labels.passthroughReplaceTokenCta
                          : labels.passthroughConnectTokenCta}
                      </button>
                      {conn.connected && (
                        <button
                          type="button"
                          data-testid={`passthrough-revoke-btn-${conn.connectorId}`}
                          onClick={() => void handleRevoke(conn.connectorId)}
                          className="px-2 py-1 rounded text-xs orcia-ds-btn-danger text-status-danger"
                        >
                          {labels.passthroughRevokeTokenCta}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div
          data-testid="passthrough-empty-connectors-state"
          className="p-3 rounded-lg border border-surface-border bg-surface-primary space-y-2"
        >
          <p className="text-text-secondary text-xs">{labels.passthroughEmptyConnectorsMessage}</p>
          <button
            type="button"
            data-testid="passthrough-test-token-btn"
            disabled
            className="px-2.5 py-1 rounded bg-brand-primary text-surface-elevated font-medium text-xs opacity-50 cursor-not-allowed"
          >
            {labels.testPassthroughTokenCta}
          </button>
        </div>
      )}
    </div>
  );
}

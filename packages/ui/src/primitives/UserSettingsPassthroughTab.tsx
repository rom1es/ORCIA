import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import type {
  UiLocalePreference,
  UiUserPassthroughConnectorView,
  UserAccountDropdownAndSettingsLabels,
} from "./UserAccountDropdownTypes";

export interface UserSettingsPassthroughTabProps {
  readonly locale?: UiLocalePreference;
  readonly passthroughTested: boolean;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly passthroughConnectors?: readonly UiUserPassthroughConnectorView[];
  readonly onTestPassthrough: () => void;
  readonly onSavePassthroughToken?: (
    connectorId: string,
    externalLogin: string,
    secretValue: string,
  ) => void | Promise<void>;
  readonly onRevokePassthroughToken?: (connectorId: string) => void | Promise<void>;
}

export function UserSettingsPassthroughTab({
  locale = "fr",
  passthroughTested,
  labels,
  passthroughConnectors,
  onTestPassthrough,
  onSavePassthroughToken,
  onRevokePassthroughToken,
}: UserSettingsPassthroughTabProps): React.ReactElement {
  const isFr = locale !== "en";
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
      setStatusMessage(isFr ? "Jeton personnel enregistré avec succès." : "Personal token saved successfully.");
    } catch {
      setStatusMessage(isFr ? "Erreur lors de l'enregistrement du jeton." : "Error saving token.");
    }
  };

  const handleRevoke = async (connectorId: string) => {
    try {
      await onRevokePassthroughToken?.(connectorId);
      setStatusMessage(isFr ? "Jeton révoqué." : "Token revoked.");
    } catch {
      setStatusMessage(isFr ? "Erreur lors de la révocation du jeton." : "Error revoking token.");
    }
  };

  return (
    <div data-testid="user-settings-panel-PASSTHROUGH_SOURCES" className="space-y-3">
      <div className="rounded-lg border border-surface-border bg-surface-card p-3 space-y-1">
        <div className="font-semibold text-text-primary text-xs flex items-center gap-1.5">
          <OrciaIcon name="plug" size={14} />
          <span>{isFr ? "Attribution nominative des actions d'outils" : "Nominative Action Attribution"}</span>
        </div>
        <p className="text-text-secondary text-[11px]">
          {isFr
            ? "Renseignez vos identifiants personnels une seule fois au niveau du socle pour que vos actions Jira, GitLab ou Confluence soient signées en votre nom propre."
            : "Set up your personal credentials once at platform level so your Jira, GitLab, or Confluence actions are signed under your personal name."}
        </p>
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
                        {isFr ? "Non connecté" : "Not connected"}
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
                        placeholder={isFr ? "Identifiant (@login)" : "Login (@username)"}
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
                        placeholder={isFr ? "Jeton d'accès (PAT/Secret)" : "Personal Access Token"}
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
                        {isFr ? "Enregistrer mon jeton" : "Save token"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingConnectorId(null)}
                        className="px-2.5 py-1 rounded text-xs border border-surface-border text-text-secondary"
                      >
                        {isFr ? "Annuler" : "Cancel"}
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-text-secondary">
                      {conn.externalAuthorLogin ? `@${conn.externalAuthorLogin}` : (isFr ? "Aucun identifiant associé" : "No login attached")}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        data-testid={`passthrough-configure-btn-${conn.connectorId}`}
                        onClick={() => handleStartEdit(conn)}
                        className="px-2 py-1 rounded text-xs border border-surface-border bg-surface-secondary text-text-primary hover:bg-surface-card"
                      >
                        {conn.connected ? (isFr ? "Remplacer le jeton" : "Replace token") : (isFr ? "Connecter mon jeton" : "Connect token")}
                      </button>
                      {conn.connected && (
                        <button
                          type="button"
                          data-testid={`passthrough-revoke-btn-${conn.connectorId}`}
                          onClick={() => void handleRevoke(conn.connectorId)}
                          className="px-2 py-1 rounded text-xs orcia-ds-btn-danger text-status-danger"
                        >
                          {isFr ? "Révoquer" : "Revoke"}
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
        <div className="p-3 rounded-lg border border-surface-border bg-surface-primary space-y-2">
          <p className="text-text-secondary text-xs">
            {isFr
              ? "Testez la connectivité Passthrough de vos connecteurs."
              : "Test passthrough connectivity for your connectors."}
          </p>
          <button
            type="button"
            data-testid="passthrough-test-token-btn"
            onClick={onTestPassthrough}
            className="px-2.5 py-1 rounded bg-brand-primary text-surface-elevated font-medium text-xs"
          >
            {labels.testPassthroughTokenCta}
          </button>
          {passthroughTested && (
            <span
              data-testid="passthrough-test-ok-badge"
              className="ml-2 text-status-success font-mono text-xs"
            >
              <OrciaIcon name="checkFilled" /> {isFr ? "Connectivité vérifiée" : "Connectivity verified"}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

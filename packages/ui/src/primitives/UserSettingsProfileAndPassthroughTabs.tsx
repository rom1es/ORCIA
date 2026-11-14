import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import type {
  UiLocalePreference,
  UiUserAccountProfileView,
  UiUserPassthroughConnectorView,
  UserAccountDropdownAndSettingsLabels,
} from "./UserAccountDropdownTypes";

export interface UserSettingsProfileAndPassthroughTabsProps {
  readonly userEmail: string;
  readonly userRole: string;
  readonly locale?: UiLocalePreference;
  readonly passthroughTested: boolean;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly accountProfile?: UiUserAccountProfileView;
  readonly passthroughConnectors?: readonly UiUserPassthroughConnectorView[];
  readonly onTestPassthrough: () => void;
  readonly onSavePassthroughToken?: (
    connectorId: string,
    externalLogin: string,
    secretValue: string,
  ) => void | Promise<void>;
  readonly onRevokePassthroughToken?: (connectorId: string) => void | Promise<void>;
}

export function UserSettingsProfileTab({
  userEmail,
  userRole,
  locale = "fr",
  accountProfile,
}: {
  readonly userEmail: string;
  readonly userRole: string;
  readonly locale?: UiLocalePreference;
  readonly accountProfile?: UiUserAccountProfileView;
}): React.ReactElement {
  const isFr = locale !== "en";
  const displayEmail = accountProfile?.email || userEmail;
  const displayName = accountProfile?.displayName || userEmail.split("@")[0] || "";
  const roles = accountProfile?.roles && accountProfile.roles.length > 0 ? accountProfile.roles : [userRole];
  const teams = accountProfile?.teams || [];
  const billingUnits = accountProfile?.billingOrgUnits || [];

  return (
    <div data-testid="user-settings-panel-PROFILE_SECURITY" className="space-y-4">
      <div className="rounded-lg border border-surface-border bg-surface-card p-3 space-y-2">
        <div className="font-semibold text-text-primary text-xs flex items-center gap-1.5">
          <OrciaIcon name="user" size={14} />
          <span>{isFr ? "Identité & Rôles Actifs" : "Identity & Active Roles"}</span>
        </div>
        <p className="text-text-secondary text-xs">
          <strong>{displayName}</strong> &lt;{displayEmail}&gt;
        </p>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {roles.map((r) => (
            <span
              key={r}
              data-testid={`user-role-badge-${r}`}
              className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-brand-primary/10 text-brand-primary border border-brand-primary/20"
            >
              {r}
            </span>
          ))}
        </div>
      </div>

      <div
        data-testid="user-account-finops-teams-section"
        className="rounded-lg border border-surface-border bg-surface-card p-3 space-y-2"
      >
        <div className="font-semibold text-text-primary text-xs flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <OrciaIcon name="team" size={14} />
            <span>{isFr ? "Mes équipes & rattachements FinOps" : "My Teams & FinOps Allocations"}</span>
          </span>
          <span className="text-[10px] text-text-secondary font-normal">
            {isFr ? "Lecture seule gouvernée" : "Governed read-only"}
          </span>
        </div>

        {teams.length === 0 ? (
          <p className="text-text-secondary text-xs italic">
            {isFr
              ? "Aucune équipe opérationnelle explicitement rattachée."
              : "No operational team explicitly assigned."}
          </p>
        ) : (
          <div className="space-y-1.5 pt-1">
            {teams.map((t) => (
              <div
                key={t.id}
                data-testid={`user-team-row-${t.slug}`}
                className="flex items-center justify-between p-2 rounded bg-surface-primary/50 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium text-text-primary">{t.name}</span>
                  <span className="text-[10px] font-mono text-text-secondary">({t.slug})</span>
                  {t.isLead && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/30">
                      Lead
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[11px]">
                  {t.billingEnabled ? (
                    <span className="text-status-success font-medium flex items-center gap-1">
                      <OrciaIcon name="checkFilled" size={12} /> {isFr ? "Facturation active" : "Billing active"}
                    </span>
                  ) : (
                    <span className="text-text-secondary">{isFr ? "Sans facturation" : "No billing"}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {billingUnits.length > 0 && (
          <div className="pt-2 border-t border-surface-border text-[11px] text-text-secondary">
            <span>{isFr ? "Unités de facturation associées : " : "Associated billing units: "}</span>
            <span className="font-medium text-text-primary">
              {billingUnits.map((u) => u.name).join(", ")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export function UserSettingsPassthroughTab({
  locale = "fr",
  passthroughTested,
  labels,
  passthroughConnectors,
  onTestPassthrough,
  onSavePassthroughToken,
  onRevokePassthroughToken,
}: {
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
}): React.ReactElement {
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

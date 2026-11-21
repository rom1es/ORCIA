import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaAlertBanner } from "./DesignSystemControls";
import type {
  CreateMcpTokenDraftInput,
  UiMcpTargetKind,
  UiPersonalMcpTokenItem,
  UserAccountDropdownAndSettingsLabels,
} from "./UserAccountDropdownTypes";

export interface UserSettingsMcpTokensTabProps {
  readonly mcpTokens: readonly UiPersonalMcpTokenItem[];
  readonly lastIssuedPlaintext: string | null;
  readonly isSubmitting?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly onCreateMcpToken: (input: CreateMcpTokenDraftInput) => void | Promise<void>;
  readonly onRevokeMcpToken: (tokenId: string) => void | Promise<void>;
  readonly onDirtyChange?: (dirty: boolean) => void;
}

export function UserSettingsMcpTokensTab({
  mcpTokens,
  lastIssuedPlaintext,
  isSubmitting = false,
  errorMessage = null,
  labels,
  onCreateMcpToken,
  onRevokeMcpToken,
  onDirtyChange,
}: UserSettingsMcpTokensTabProps): React.ReactElement {
  const [label, setLabel] = useState<string>("");
  const [targetKind, setTargetKind] = useState<UiMcpTargetKind>("SPACE");
  const [targetSlug, setTargetSlug] = useState<string>("");
  const [expiresInDays, setExpiresInDays] = useState<30 | 90>(30);
  const [rpmLimit, setRpmLimit] = useState<number>(60);
  const [copiedPlaintext, setCopiedPlaintext] = useState<boolean>(false);

  useEffect(() => {
    if (lastIssuedPlaintext === null) {
      setCopiedPlaintext(false);
    }
  }, [lastIssuedPlaintext]);

  const handleSubmit = async (): Promise<void> => {
    const cleanSlug = targetSlug.trim();
    const cleanLabel =
      label.trim() ||
      (cleanSlug
        ? `Clé d'accès éditeur — ${cleanSlug}`
        : "Clé personnelle d'éditeur");
    onDirtyChange?.(false);
    await onCreateMcpToken({
      label: cleanLabel,
      targetKind,
      targetSlug: cleanSlug,
      expiresInDays,
      rpmLimit,
    });
    setLabel("");
    setTargetSlug("");
    setCopiedPlaintext(false);
    onDirtyChange?.(false);
  };

  const handleCopyPlaintext = async (): Promise<void> => {
    if (!lastIssuedPlaintext) return;
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(lastIssuedPlaintext);
    }
    setCopiedPlaintext(true);
  };

  return (
    <div data-testid="user-settings-panel-IDE_MCP_KEYS" className="space-y-3">
      {errorMessage && (
        <OrciaAlertBanner tone="crimson" testId="mcp-tokens-error-banner">
          {errorMessage}
        </OrciaAlertBanner>
      )}

      <div className="grid grid-cols-2 gap-2">
        <label className="col-span-2 flex flex-col gap-1 text-xs">
          <span style={{ color: "var(--color-text-secondary)" }}>
            {labels.mcpTokenLabelField}
          </span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="mcp-token-label-input"
            value={label}
            onChange={(e) => {
              setLabel(e.target.value);
              onDirtyChange?.(e.target.value.trim().length > 0 || targetSlug.trim().length > 0);
            }}
            placeholder={labels.mcpTokenLabelPlaceholder}
            className="orcia-ds-input"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span style={{ color: "var(--color-text-secondary)" }}>
            {labels.mcpTargetKindLabel}
          </span>
          <select
            data-testid="mcp-target-kind-select"
            value={targetKind}
            onChange={(e) => {
              setTargetKind(e.target.value as UiMcpTargetKind);
              onDirtyChange?.(true);
            }}
            className="orcia-ds-select"
          >
            <option value="SPACE">{labels.targetWholeSpaceLabel}</option>
            <option value="AGENT">{labels.targetSingleAgentLabel}</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span style={{ color: "var(--color-text-secondary)" }}>
            {labels.mcpTargetSlugLabel}
          </span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="mcp-target-slug-input"
            value={targetSlug}
            onChange={(e) => {
              setTargetSlug(e.target.value);
              onDirtyChange?.(e.target.value.trim().length > 0);
            }}
            placeholder={labels.mcpTargetSlugPlaceholder}
            className="orcia-ds-input font-mono"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span style={{ color: "var(--color-text-secondary)" }}>
            {labels.mcpExpiryLabel}
          </span>
          <select
            data-testid="mcp-expiry-days-select"
            value={expiresInDays}
            onChange={(e) => {
              setExpiresInDays(Number(e.target.value) as 30 | 90);
              onDirtyChange?.(true);
            }}
            className="orcia-ds-select"
          >
            <option value={30}>{labels.mcpExpiry30Label}</option>
            <option value={90}>{labels.mcpExpiry90Label}</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span style={{ color: "var(--color-text-secondary)" }}>
            {labels.mcpRpmLimitLabel}
          </span>
          <input
            type="number"
            min={1}
            max={600}
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="mcp-rpm-limit-input"
            value={rpmLimit}
            onChange={(e) => {
              setRpmLimit(Number(e.target.value));
              onDirtyChange?.(true);
            }}
            className="orcia-ds-input font-mono"
          />
        </label>
      </div>

      <button
        type="button"
        data-testid="mcp-generate-token-btn"
        disabled={isSubmitting}
        onClick={() => void handleSubmit()}
        className="orcia-ds-btn orcia-ds-btn-primary"
      >
        <OrciaIcon name="keyLock" size={14} />
        <span>{labels.generateMcpTokenCta}</span>
      </button>

      {lastIssuedPlaintext !== null && (
        <div
          data-testid="mcp-issued-plaintext-banner"
          className="rounded-lg border p-2.5 space-y-1.5 text-xs"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            borderColor: "var(--color-gate-emerald)",
            color: "var(--color-text-primary)",
          }}
        >
          <div className="font-semibold">{labels.issuedPlaintextWarning}</div>
          <div className="flex items-center justify-between gap-2">
            <code data-testid="mcp-issued-plaintext-value" className="font-mono text-[11px] break-all">
              {lastIssuedPlaintext}
            </code>
            <button
              type="button"
              data-testid="mcp-copy-plaintext-btn"
              onClick={() => void handleCopyPlaintext()}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm shrink-0"
            >
              <OrciaIcon name={copiedPlaintext ? "check" : "copy"} size={13} />
              <span>
                {copiedPlaintext ? labels.copiedPlaintextLabel : labels.copyPlaintextCta}
              </span>
            </button>
          </div>
        </div>
      )}

      <div data-testid="mcp-tokens-list" className="space-y-2">
        {mcpTokens.length === 0 ? (
          <p className="text-xs italic" style={{ color: "var(--color-text-secondary)" }}>
            {labels.emptyMcpTokensLabel}
          </p>
        ) : (
          mcpTokens.map((tok) => (
            <div
              key={tok.tokenId}
              data-testid={`mcp-token-row-${tok.tokenId}`}
              className="rounded-lg border p-2.5 space-y-1.5"
              style={{
                borderColor: "var(--color-border-subtle)",
                backgroundColor: "var(--color-surface-card)",
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0 space-y-0.5">
                  <div className="truncate font-semibold text-xs">
                    {tok.label}
                  </div>
                  <div className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                    Identifiant : <span className="font-mono">{tok.tokenPrefix}</span>
                  </div>
                  <div className="truncate text-[11px] font-mono" style={{ color: "var(--color-text-secondary)" }}>
                    {tok.mcpEndpointUri}
                  </div>
                </div>
                {tok.revoked ? (
                  <span
                    data-testid={`mcp-token-revoked-badge-${tok.tokenId}`}
                    className="font-mono text-[11px] font-semibold"
                    style={{ color: "var(--color-stale-crimson)" }}
                  >
                    {labels.revokedBadgeLabel}
                  </span>
                ) : (
                  <button
                    type="button"
                    data-testid={`mcp-revoke-btn-${tok.tokenId}`}
                    onClick={() => void onRevokeMcpToken(tok.tokenId)}
                    className="orcia-ds-btn orcia-ds-btn-danger orcia-ds-btn-sm"
                  >
                    {labels.revokeMcpTokenCta}
                  </button>
                )}
              </div>
              <div className="text-[10px]" style={{ color: "var(--color-text-secondary)" }}>
                {labels.ideJsonReadyTitle}
              </div>
              <pre
                data-testid={`mcp-ide-snippet-${tok.tokenId}`}
                className="overflow-x-auto rounded p-2 font-mono text-[10px]"
                style={{ backgroundColor: "var(--color-bg-elevated)" }}
              >
                {tok.ideJsonSnippet}
              </pre>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";

export type UiProgressiveLlmTierMode =
  | "UNCONFIGURED"
  | "QUICK_TRIAL_SINGLE_FAMILY"
  | "FULL_ORTHOGONAL_AD10";

export interface UiAccostageMilestoneItem {
  readonly index: number;
  readonly key: string;
  readonly title: string;
  readonly completed: boolean;
  readonly targetRoute: string;
}

export interface ProgressiveDay0AccostageLabels {
  readonly bannerTitle: string;
  readonly welcomeWizardTitle: string;
  readonly step1AdminTitle: string;
  readonly step2LlmTitle: string;
  readonly step3SpaceTitle: string;
  readonly bootstrapTokenLabel: string;
  readonly bootstrapTokenPlaceholder: string;
  readonly bootstrapTokenDeniedBanner: string;
  readonly createFirstAdminCta: string;
  readonly addFirstModelCta: string;
  readonly addSecondModelFamilyCta: string;
  readonly singleFamilyAmberWarning: string;
  readonly dualFamilyAd10UnlockedBadge: string;
  readonly assistantTrialReadyBadge: string;
  readonly progressLabelPrefix?: string;
  readonly adminInitializedBadge?: string;
}

export interface ProgressiveDay0AccostageBannerProps {
  readonly completedCount: number;
  readonly totalCount?: number;
  readonly defaultCompact?: boolean;
  readonly orciaEnv?: "local" | "staging" | "production";
  readonly adminCreated?: boolean;
  readonly adminDisplayName?: string | null;
  readonly adminEmail?: string | null;
  readonly initialFamilies?: readonly string[];
  readonly milestones: readonly UiAccostageMilestoneItem[];
  readonly labels: ProgressiveDay0AccostageLabels;
  readonly onSubmitFirstAdmin?: (payload: {
    email: string;
    displayName: string;
    bootstrapToken: string;
  }) => boolean;
  readonly onRegisterModelFamily?: (familySlug: string) => void;
  readonly onNavigateMilestone?: (targetRoute: string) => void;
}

export function ProgressiveDay0AccostageBanner({
  completedCount,
  totalCount = 6,
  defaultCompact = false,
  orciaEnv = "local",
  adminCreated: serverAdminCreated = false,
  adminDisplayName,
  adminEmail: serverAdminEmail,
  initialFamilies = [],
  milestones,
  labels,
  onSubmitFirstAdmin,
  onRegisterModelFamily,
  onNavigateMilestone,
}: ProgressiveDay0AccostageBannerProps): React.ReactElement {
  const [families, setFamilies] = useState<readonly string[]>(initialFamilies);
  const [adminEmail, setAdminEmail] = useState<string>("");
  const [adminName] = useState<string>("");
  const [bootstrapToken, setBootstrapToken] = useState<string>("");
  const [tokenDenied, setTokenDenied] = useState<boolean>(false);
  const [localAdminCreated, setLocalAdminCreated] = useState<boolean>(false);
  const [isCompact, setIsCompact] = useState<boolean>(defaultCompact);

  useEffect(() => {
    setIsCompact(defaultCompact);
  }, [defaultCompact]);

  const effectiveAdminCreated = Boolean(serverAdminCreated || localAdminCreated);
  const distinctFamilies = Array.from(
    new Set(families.map((f) => f.trim().toLowerCase()).filter(Boolean)),
  );
  const llmTierMode: UiProgressiveLlmTierMode =
    distinctFamilies.length === 0
      ? "UNCONFIGURED"
      : distinctFamilies.length === 1
        ? "QUICK_TRIAL_SINGLE_FAMILY"
        : "FULL_ORTHOGONAL_AD10";

  const effectiveCompletedCount = Math.max(0, Math.min(totalCount, completedCount));
  const progressPrefix = labels.progressLabelPrefix ?? "Accostage";
  const adminInitializedLabel =
    labels.adminInitializedBadge ?? "Administrateur de plateforme initialisé";

  const handleAddFamily = (family: string): void => {
    setFamilies((prev) => Array.from(new Set([...prev, family])));
    onRegisterModelFamily?.(family);
  };

  const handleFirstAdminSubmit = (): void => {
    if (orciaEnv !== "local" && bootstrapToken.trim() === "") {
      setTokenDenied(true);
      return;
    }
    const ok =
      onSubmitFirstAdmin?.({
        email: adminEmail,
        displayName: adminName,
        bootstrapToken,
      }) ?? true;
    if (!ok) {
      setTokenDenied(true);
      return;
    }
    setTokenDenied(false);
    setLocalAdminCreated(true);
  };

  return (
    <section
      data-testid="progressive-day0-accostage-banner"
      data-compact={isCompact ? "true" : "false"}
      className="flex flex-col gap-3 rounded border p-3.5"
      style={{
        backgroundColor: "var(--color-bg-surface)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      {/* Top interactive Accostage X/6 header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xs font-semibold">{labels.bannerTitle}</h2>
          <span
            data-testid="accostage-progress-pill"
            className="rounded px-2 py-0.5 font-mono text-xs font-bold"
            style={{
              backgroundColor: "var(--color-action-primary-subtle)",
              color: "var(--color-sidebar-active-fg)",
            }}
          >
            {progressPrefix} {effectiveCompletedCount}/{totalCount}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {llmTierMode === "QUICK_TRIAL_SINGLE_FAMILY" && (
            <span
              data-testid="accostage-single-family-amber-badge"
              className="rounded border px-2.5 py-1 text-xs font-medium"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-state-warning)",
                color: "var(--color-state-warning)",
              }}
            >
              {labels.singleFamilyAmberWarning}
            </span>
          )}

          {llmTierMode === "FULL_ORTHOGONAL_AD10" && (
            <span
              data-testid="accostage-dual-family-ad10-badge"
              className="rounded border px-2.5 py-1 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-state-verified)",
                color: "var(--color-state-verified)",
              }}
            >
              {labels.dualFamilyAd10UnlockedBadge}
            </span>
          )}

          <button
            type="button"
            data-testid="accostage-compact-toggle-btn"
            aria-expanded={!isCompact}
            onClick={() => setIsCompact((prev) => !prev)}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            <OrciaIcon name={isCompact ? "chevronRight" : "chevronDown"} size={13} />
            <span>{isCompact ? "Déplier le guide" : "Réduire"}</span>
          </button>
        </div>
      </div>

      {/* 3-Step Welcome Setup Wizard (hidden when compacted on active Cockpit) */}
      {!isCompact && (
      <div
        data-testid="welcome-setup-3step-wizard"
        className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(240px,1.35fr)]"
      >
        {/* Step 1: First Admin (auto-checked & collapsed when PG18 admin exists) */}
        <div
          data-testid="welcome-setup-step1-card"
          data-completed={effectiveAdminCreated ? "true" : "false"}
          className="flex flex-col gap-2 rounded border p-3"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: effectiveAdminCreated
              ? "var(--color-state-verified)"
              : "var(--color-border-subtle)",
          }}
        >
          <div className="flex items-center justify-between gap-2 text-xs font-semibold">
            <span>{labels.step1AdminTitle}</span>
            {effectiveAdminCreated && (
              <span
                data-testid="welcome-setup-step1-checked-icon"
                style={{ color: "var(--color-state-verified)" }}
              >
                <OrciaIcon name="check" />
              </span>
            )}
          </div>

          {effectiveAdminCreated ? (
            <div
              data-testid="welcome-setup-admin-created-badge"
              className="flex flex-col gap-0.5 text-xs font-medium"
              style={{ color: "var(--color-state-verified)" }}
            >
              <span>
                {adminInitializedLabel} <OrciaIcon name="check" />
              </span>
              {(adminDisplayName || serverAdminEmail || adminEmail) && (
                <span
                  className="truncate text-[11px]"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {adminDisplayName || serverAdminEmail || adminEmail}
                </span>
              )}
            </div>
          ) : (
            <>
              <input
                type="email"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="welcome-setup-admin-email"
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                className="w-full min-w-0 rounded border px-2 py-1 text-xs"
                style={{
                  backgroundColor: "var(--color-bg-canvas)",
                  borderColor: "var(--color-border-subtle)",
                }}
              />
              {orciaEnv !== "local" && (
                <input
                  type="text"
                  spellCheck={false}
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  data-testid="welcome-setup-bootstrap-token-input"
                  value={bootstrapToken}
                  onChange={(e) => setBootstrapToken(e.target.value)}
                  placeholder={labels.bootstrapTokenPlaceholder}
                  aria-label={labels.bootstrapTokenLabel}
                  className="w-full min-w-0 rounded border px-2 py-1 font-mono text-xs orcia-masked-secret-input"
                  style={
                    {
                      backgroundColor: "var(--color-bg-canvas)",
                      borderColor: "var(--color-border-subtle)",
                      WebkitTextSecurity: "disc",
                    } as React.CSSProperties
                  }
                />
              )}
              <button
                type="button"
                data-testid="welcome-setup-submit-admin-btn"
                onClick={handleFirstAdminSubmit}
                className="rounded px-2.5 py-1 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-action-primary)",
                  color: "var(--color-bg-surface)",
                }}
              >
                {labels.createFirstAdminCta}
              </button>
              {tokenDenied && (
                <div
                  data-testid="welcome-setup-token-denied-banner"
                  className="text-xs font-semibold"
                  style={{ color: "var(--color-state-danger)" }}
                >
                  {labels.bootstrapTokenDeniedBanner}
                </div>
              )}
            </>
          )}
        </div>

        {/* Step 2: Progressive LLM Tier */}
        <div
          className="flex flex-col gap-2 rounded border p-3"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div className="text-xs font-semibold">{labels.step2LlmTitle}</div>
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              data-testid="welcome-setup-add-first-llm-btn"
              onClick={() => handleAddFamily("ollama-qwen")}
              className="rounded border px-2 py-1 text-xs font-medium"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              {labels.addFirstModelCta}
            </button>
            <button
              type="button"
              data-testid="welcome-setup-add-second-llm-btn"
              onClick={() => handleAddFamily("anthropic-claude")}
              className="rounded border px-2 py-1 text-xs font-medium"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              {labels.addSecondModelFamilyCta}
            </button>
          </div>
          {distinctFamilies.length >= 1 && (
            <div
              data-testid="welcome-setup-assistant-trial-ready"
              className="text-xs font-semibold"
              style={{ color: "var(--color-state-verified)" }}
            >
              {labels.assistantTrialReadyBadge}
            </div>
          )}
        </div>

        {/* Step 3: Milestones Navigation */}
        <div
          className="flex flex-col gap-1.5 rounded border p-3"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div className="text-xs font-semibold">{labels.step3SpaceTitle}</div>
          {milestones.map((m) => (
            <button
              key={m.key}
              type="button"
              data-testid={`accostage-milestone-${m.key}`}
              data-completed={m.completed ? "true" : "false"}
              onClick={() => onNavigateMilestone?.(m.targetRoute)}
              className="flex items-center justify-between gap-2 rounded px-2 py-1 text-left text-xs"
              style={{
                backgroundColor: "var(--color-bg-surface)",
              }}
            >
              <span className="min-w-0 whitespace-normal leading-snug">{m.title}</span>
              <OrciaIcon
                name={m.completed ? "check" : "arrowRight"}
                className="shrink-0 font-mono text-[11px]"
              />
            </button>
          ))}
        </div>
      </div>
      )}
    </section>
  );
}

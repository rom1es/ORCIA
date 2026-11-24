import { OrciaAlertBanner, OrciaSpinner } from "@orcia/ui";
import React from "react";
import { resolveDictionaryForFlag } from "../i18n";
import { LoginRouteComponent } from "./LoginScreenView";
import { TemporaryPasswordWarningBanner } from "./TemporaryPasswordWarningBanner";

export function ShellHydratingLoaderView({ isFr }: { readonly isFr: boolean }) {
  const copy = resolveDictionaryForFlag(isFr).shellChrome;
  return (
    <div
      data-testid="auth-hydrating-loader"
      className="flex h-full min-h-screen md:min-h-0 flex-col items-center justify-center gap-3 bg-[var(--color-bg-canvas)] text-[var(--color-text-secondary)]"
    >
      <div className="inline-flex items-center gap-2">
        <span
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-sm font-bold"
          style={{
            backgroundColor: "var(--color-action-primary)",
            color: "var(--color-bg-surface)",
          }}
        >
          O
        </span>
        <span
          className="text-base font-bold tracking-tight"
          style={{ color: "var(--color-text-primary)" }}
        >
          {copy.brandName}
        </span>
      </div>
      <div className="inline-flex items-center gap-2 text-sm font-medium">
        <OrciaSpinner size="sm" />
        <span>{copy.loadingSession}</span>
      </div>
    </div>
  );
}

export function ShellUnauthenticatedView({
  onReopenDay0Setup,
  reopenDay0SetupLabel,
}: {
  readonly onReopenDay0Setup?: () => void;
  readonly reopenDay0SetupLabel?: string;
} = {}) {
  return (
    <div
      data-testid="unauthenticated-shell-fallback"
      className="flex h-full min-h-screen md:min-h-0 flex-col items-center justify-center gap-4 overflow-y-auto bg-[var(--color-bg-canvas)] p-6"
    >
      <LoginRouteComponent />
      {onReopenDay0Setup && reopenDay0SetupLabel ? (
        <button
          type="button"
          data-testid="reopen-first-boot-admin-modal-btn"
          onClick={onReopenDay0Setup}
          className="orcia-ds-btn orcia-ds-btn-primary"
        >
          {reopenDay0SetupLabel}
        </button>
      ) : null}
    </div>
  );
}

export function ShellCentralWorkspaceBody({
  lastSyncError,
  mustChangePassword,
  isFr,
  onOpenAccountSecurity,
  children,
}: {
  readonly lastSyncError: string | null;
  readonly mustChangePassword: boolean;
  readonly isFr: boolean;
  readonly onOpenAccountSecurity: () => void;
  readonly children: React.ReactNode;
}) {
  return (
    <div className="flex h-full flex-col">
      {lastSyncError && (
        <div className="px-4 pt-3">
          <OrciaAlertBanner tone="crimson" role="alert" testId="platform-sync-error-banner">
            {lastSyncError}
          </OrciaAlertBanner>
        </div>
      )}
      {mustChangePassword && (
        <TemporaryPasswordWarningBanner isFr={isFr} onOpenSettings={onOpenAccountSecurity} />
      )}
      <div className="flex-1">{children}</div>
    </div>
  );
}

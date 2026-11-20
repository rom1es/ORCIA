import { OrciaAlertBanner } from "@orcia/ui";
import React from "react";
import { LoginRouteComponent } from "./LoginScreenView";
import { TemporaryPasswordWarningBanner } from "./TemporaryPasswordWarningBanner";

export function ShellHydratingLoaderView({ isFr }: { readonly isFr: boolean }) {
  return (
    <div
      data-testid="auth-hydrating-loader"
      className="flex min-h-screen items-center justify-center bg-[var(--color-bg-canvas)] text-[var(--color-text-secondary)]"
    >
      <span className="text-sm font-medium">
        {isFr ? "Chargement de la session..." : "Loading session..."}
      </span>
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
      className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[var(--color-bg-canvas)] p-6"
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

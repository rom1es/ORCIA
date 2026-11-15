import React from "react";
import { LoginRouteComponent } from "./LoginScreenView";

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

export function ShellUnauthenticatedView() {
  return (
    <div
      data-testid="unauthenticated-shell-fallback"
      className="flex min-h-screen flex-col items-center justify-center bg-[var(--color-bg-canvas)] p-6"
    >
      <LoginRouteComponent />
    </div>
  );
}

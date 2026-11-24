import React from "react";
import { DICTIONARIES, type SupportedWebLocale } from "../i18n";

interface RootErrorBoundaryState {
  readonly hasError: boolean;
  readonly errorDetail: string | null;
}

function resolveDocumentFallbackLocale(): SupportedWebLocale {
  if (typeof document !== "undefined" && document.documentElement.lang.toLowerCase().startsWith("en")) {
    return "en";
  }
  return "fr";
}

export class OrciaRootErrorBoundary extends React.Component<
  { readonly children: React.ReactNode },
  RootErrorBoundaryState
> {
  public override state: RootErrorBoundaryState = {
    hasError: false,
    errorDetail: null,
  };

  public static getDerivedStateFromError(error: unknown): RootErrorBoundaryState {
    return {
      hasError: true,
      errorDetail: error instanceof Error ? error.message : String(error),
    };
  }

  public override componentDidCatch(error: unknown, info: React.ErrorInfo): void {
    console.error("[ORCIA] Unhandled UI render error:", error, info.componentStack);
  }

  public override render(): React.ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }
    const copy = DICTIONARIES[resolveDocumentFallbackLocale()].shellChrome.rootErrorBoundary;
    return (
      <div
        data-testid="orcia-root-error-boundary"
        className="flex min-h-screen items-center justify-center p-6"
      >
        <div className="orcia-bento-card max-w-lg w-full space-y-4">
          <div role="alert" className="orcia-ds-alert orcia-ds-alert-error">
            <div className="orcia-ds-alert-content space-y-1">
              <div className="text-sm font-semibold">{copy.unexpectedError}</div>
              {this.state.errorDetail ? (
                <div className="text-xs">{this.state.errorDetail}</div>
              ) : null}
            </div>
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              data-testid="orcia-root-error-reload-btn"
              className="orcia-ds-btn orcia-ds-btn-primary"
              onClick={() => {
                if (typeof window !== "undefined") {
                  window.location.reload();
                }
              }}
            >
              {copy.reloadPage}
            </button>
          </div>
        </div>
      </div>
    );
  }
}

import React, { useCallback, useEffect, useRef, useState } from "react";
import { OrciaIcon } from "../components/icons";
import type { FourZoneDirectionCShellLabels } from "./FourZoneShellTypes";

export interface FourZoneHelpAsideColumnProps {
  readonly isMobile: boolean;
  readonly labels: Pick<
    FourZoneDirectionCShellLabels,
    | "helpColumnTitle"
    | "helpColumnExpectedTitle"
    | "helpColumnExpectedBody"
    | "helpColumnScrollMoreLabel"
  >;
  readonly helpColumnContent?: React.ReactNode;
  readonly onClose: () => void;
}

export function FourZoneHelpAsideColumn({
  isMobile,
  labels,
  helpColumnContent,
  onClose,
}: FourZoneHelpAsideColumnProps) {
  const asideRef = useRef<HTMLElement | null>(null);
  const [hasMoreBelow, setHasMoreBelow] = useState(false);

  const checkScrollOverflow = useCallback(() => {
    const el = asideRef.current;
    if (!el) return;
    const remaining = el.scrollHeight - el.clientHeight - el.scrollTop;
    setHasMoreBelow(el.scrollHeight > el.clientHeight + 4 && remaining > 8);
  }, []);

  useEffect(() => {
    checkScrollOverflow();
    const el = asideRef.current;
    if (!el) return;

    const ro =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(checkScrollOverflow) : null;
    ro?.observe(el);

    const mo =
      typeof MutationObserver !== "undefined"
        ? new MutationObserver(checkScrollOverflow)
        : null;
    mo?.observe(el, { childList: true, subtree: true, characterData: true });

    window.addEventListener("resize", checkScrollOverflow);
    return () => {
      ro?.disconnect();
      mo?.disconnect();
      window.removeEventListener("resize", checkScrollOverflow);
    };
  }, [checkScrollOverflow, helpColumnContent]);

  return (
    <aside
      ref={asideRef}
      data-testid="four-zone-contextual-help-column"
      onScroll={checkScrollOverflow}
      className={
        isMobile
          ? "fixed inset-x-0 top-[52px] bottom-[58px] z-40 overflow-y-auto border-t p-4"
          : "min-h-0 shrink-0 overflow-y-auto border-l p-4"
      }
      style={{
        width: isMobile ? "100%" : "340px",
        maxHeight: isMobile ? undefined : "calc(100vh - 52px)",
        overflowY: "auto",
        position: isMobile ? "fixed" : "sticky",
        top: "52px",
        backgroundColor: "var(--color-bg-surface)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold">{labels.helpColumnTitle}</h2>
        <button
          type="button"
          data-testid="contextual-help-close-btn"
          aria-label={labels.helpColumnTitle}
          onClick={onClose}
          className="text-xs"
        >
          <OrciaIcon name="close" />
        </button>
      </div>
      {helpColumnContent ? (
        <div
          className="mt-3"
          style={{ paddingBottom: hasMoreBelow ? "44px" : undefined }}
        >
          {helpColumnContent}
        </div>
      ) : (
        <p className="mt-3 text-xs" style={{ color: "var(--color-text-secondary)" }}>
          {labels.helpColumnExpectedBody}
        </p>
      )}
      {hasMoreBelow && (
        <div
          data-testid="contextual-help-scroll-indicator"
          aria-hidden="true"
          style={{
            position: "sticky",
            bottom: "-16px",
            marginLeft: "-16px",
            marginRight: "-16px",
            marginBottom: "-16px",
            zIndex: 10,
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              height: "14px",
              background: "linear-gradient(to bottom, transparent, var(--color-bg-surface))",
            }}
          />
          <div
            className="px-4 py-2 text-center text-[11px] font-medium"
            style={{
              backgroundColor: "var(--color-bg-surface)",
              color: "var(--color-text-secondary)",
              borderTop: "1px solid var(--color-border-subtle)",
            }}
          >
            {labels.helpColumnScrollMoreLabel ?? "↓"}
          </div>
        </div>
      )}
    </aside>
  );
}

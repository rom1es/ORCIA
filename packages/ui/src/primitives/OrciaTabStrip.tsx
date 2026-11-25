import React, { useRef } from "react";
import { OrciaIcon, type OrciaIconName } from "../components/icons";

export type OrciaTabStripVariant = "underline" | "segmented";

export interface OrciaTabStripItem<T extends string = string> {
  readonly key: T;
  readonly label: string;
  readonly count?: number;
  readonly icon?: OrciaIconName;
  readonly disabled?: boolean;
  readonly disabledReason?: string;
  readonly tooltip?: string;
  readonly testId?: string;
  readonly countTestId?: string;
}

export interface OrciaTabStripProps<T extends string = string> {
  readonly tabs: readonly OrciaTabStripItem<T>[];
  readonly activeTabId: T;
  readonly onSelectTab: (tabId: T) => void;
  /** Required accessible label for `role="tablist"` (provided via caller i18n dictionary). */
  readonly ariaLabel: string;
  readonly variant?: OrciaTabStripVariant;
  readonly trailingSlot?: React.ReactNode;
  readonly testId?: string;
  readonly testIdPrefix?: string;
  readonly className?: string;
}

/**
 * Canonical horizontal accessible tab strip (`UH-06`, `UH-07`).
 * Visually distinct from solid Cobalt primary CTAs and neutral filter/scope pills
 * via underline or neutral segmented active styling.
 */
export function OrciaTabStrip<T extends string = string>({
  tabs,
  activeTabId,
  onSelectTab,
  ariaLabel,
  variant,
  trailingSlot,
  testId,
  testIdPrefix = "orcia-tab-strip",
  className,
}: OrciaTabStripProps<T>): React.ReactElement {
  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const variantClass =
    variant === "segmented" ? "orcia-ds-tab-strip--segmented" : "orcia-ds-tab-strip--underline";
  const tabListClassName = ["orcia-ds-tab-strip", variantClass, className]
    .filter(Boolean)
    .join(" ");

  const moveSelection = (currentIndex: number, direction: 1 | -1 | "home" | "end") => {
    const enabledIndices = tabs
      .map((item, idx) => (!item.disabled ? idx : -1))
      .filter((idx) => idx >= 0);
    if (enabledIndices.length === 0) return;

    let targetIndex = enabledIndices[0]!;
    if (direction === "home") {
      targetIndex = enabledIndices[0]!;
    } else if (direction === "end") {
      targetIndex = enabledIndices[enabledIndices.length - 1]!;
    } else {
      const pos = enabledIndices.indexOf(currentIndex);
      const basePos = pos >= 0 ? pos : 0;
      const nextPos = (basePos + direction + enabledIndices.length) % enabledIndices.length;
      targetIndex = enabledIndices[nextPos]!;
    }

    const nextTab = tabs[targetIndex];
    if (!nextTab) return;
    buttonRefs.current[targetIndex]?.focus();
    if (nextTab.key !== activeTabId) {
      onSelectTab(nextTab.key);
    }
  };

  const handleKeyDown = (index: number, event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      moveSelection(index, 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveSelection(index, -1);
    } else if (event.key === "Home") {
      event.preventDefault();
      moveSelection(index, "home");
    } else if (event.key === "End") {
      event.preventDefault();
      moveSelection(index, "end");
    }
  };

  return (
    <div className="orcia-ds-tab-strip-row" data-testid={testId ? `${testId}-row` : undefined}>
      <div
        role="tablist"
        aria-label={ariaLabel}
        aria-orientation="horizontal"
        data-testid={testId}
        className={tabListClassName}
      >
        {tabs.map((tab, index) => {
          const isSelected = tab.key === activeTabId;
          const resolvedTitle = tab.disabled ? (tab.disabledReason ?? tab.tooltip) : tab.tooltip;
          return (
            <button
              key={tab.key}
              ref={(el) => {
                buttonRefs.current[index] = el;
              }}
              type="button"
              role="tab"
              aria-selected={isSelected}
              aria-disabled={tab.disabled ? "true" : undefined}
              disabled={Boolean(tab.disabled)}
              title={resolvedTitle}
              tabIndex={isSelected ? 0 : -1}
              data-testid={tab.testId ?? `${testIdPrefix}-${tab.key}`}
              className="orcia-ds-tab-strip-item"
              onClick={() => {
                if (!tab.disabled && tab.key !== activeTabId) {
                  onSelectTab(tab.key);
                }
              }}
              onKeyDown={(event) => handleKeyDown(index, event)}
            >
              {tab.icon ? <OrciaIcon name={tab.icon} size={14} /> : null}
              <span>{tab.label}</span>
              {typeof tab.count === "number" ? (
                <span
                  data-testid={tab.countTestId ?? `${testIdPrefix}-badge-${tab.key}`}
                  className="orcia-ds-tab-strip-badge"
                >
                  {tab.count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      {trailingSlot ? (
        <div data-testid={testId ? `${testId}-trailing` : undefined}>{trailingSlot}</div>
      ) : null}
    </div>
  );
}

import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { OrciaIcon } from "../components/icons";
import { normalizeComboboxSearchToken } from "./comboboxSearchUtils";
import { OrciaModelComboboxDropdown } from "./OrciaModelComboboxDropdown";
import type {
  DiscoveredModelOption,
  OrciaModelComboboxLabels,
  OrciaModelComboboxProps,
} from "./OrciaModelComboboxTypes";
import { OrciaSpinner } from "./OrciaSpinner";

export type {
  DiscoveredModelOption,
  OrciaModelComboboxLabels,
  OrciaModelComboboxProps,
};

export function OrciaModelCombobox({
  id,
  testId,
  value,
  onChange,
  models,
  targetUsage,
  isLoading = false,
  errorMessage,
  onRefresh,
  placeholder,
  disabled = false,
  labels,
  className = "orcia-ds-input",
  style,
  maxDisplayedItems = 15,
}: OrciaModelComboboxProps): React.ReactElement {
  const generatedId = useId();
  const effectiveId = id || `model-combobox-${generatedId}`;
  const listboxId = `${effectiveId}-listbox`;

  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  // 1. Filter models according to targetUsage compatibility
  const usageCompatibleModels = useMemo(() => {
    if (!targetUsage) return models;
    return models.filter((m) => {
      const hint = m.usageHint || "unknown";
      if (targetUsage === "chat" && hint === "embedding") return false;
      if (targetUsage === "embedding" && hint === "chat") return false;
      return true;
    });
  }, [models, targetUsage]);

  // 2. Filter models according to freeform search query
  const matchingModels = useMemo(() => {
    const query = normalizeComboboxSearchToken(value);
    if (!query) return usageCompatibleModels;
    return usageCompatibleModels.filter((m) => {
      const matchId = normalizeComboboxSearchToken(m.id).includes(query);
      const matchName = m.displayName
        ? normalizeComboboxSearchToken(m.displayName).includes(query)
        : false;
      const matchDesc = m.description
        ? normalizeComboboxSearchToken(m.description).includes(query)
        : false;
      return matchId || matchName || matchDesc;
    });
  }, [usageCompatibleModels, value]);

  const displayedModels = useMemo(
    () => matchingModels.slice(0, maxDisplayedItems),
    [matchingModels, maxDisplayedItems],
  );

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (modelId: string) => {
    onChange(modelId);
    setIsOpen(false);
    setHighlightedIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        setHighlightedIndex(displayedModels.length > 0 ? 0 : -1);
      } else if (displayedModels.length > 0) {
        setHighlightedIndex((prev) => (prev + 1) % displayedModels.length);
      }
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        setHighlightedIndex(displayedModels.length > 0 ? displayedModels.length - 1 : -1);
      } else if (displayedModels.length > 0) {
        setHighlightedIndex((prev) => (prev <= 0 ? displayedModels.length - 1 : prev - 1));
      }
      return;
    }

    if (e.key === "Enter") {
      if (isOpen && highlightedIndex >= 0 && displayedModels[highlightedIndex]) {
        e.preventDefault();
        handleSelect(displayedModels[highlightedIndex].id);
      }
      return;
    }

    if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
      setHighlightedIndex(-1);
    }
  };

  const activeDescendantId =
    isOpen && highlightedIndex >= 0 && displayedModels[highlightedIndex]
      ? `${effectiveId}-opt-${displayedModels[highlightedIndex].id}`
      : undefined;

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", width: "100%", ...style }}
      data-testid={`${testId}-container`}
    >
      <div style={{ position: "relative", display: "flex", alignItems: "center", width: "100%" }}>
        <input
          id={effectiveId}
          type="text"
          role="combobox"
          aria-expanded={isOpen}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={activeDescendantId}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="none"
          spellCheck={false}
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid={testId}
          disabled={disabled}
          value={value}
          placeholder={placeholder}
          className={className}
          style={{
            width: "100%",
            paddingRight: onRefresh ? "68px" : "36px",
          }}
          onChange={(e) => {
            onChange(e.target.value);
            if (!isOpen) setIsOpen(true);
            setHighlightedIndex(0);
          }}
          onFocus={() => {
            if (!disabled && usageCompatibleModels.length > 0) {
              setIsOpen(true);
              setHighlightedIndex(0);
            }
          }}
          onKeyDown={handleKeyDown}
        />

        <div
          style={{
            position: "absolute",
            right: "8px",
            display: "flex",
            alignItems: "center",
            gap: "4px",
          }}
        >
          {isLoading && (
            <span
              data-testid={`${testId}-loading-indicator`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "11px",
                color: "var(--color-muted-foreground)",
                marginRight: "4px",
              }}
            >
              <OrciaSpinner size="xs" />
              <span>{labels.loadingLabel}</span>
            </span>
          )}

          {onRefresh && (
            <button
              type="button"
              data-testid={`${testId}-refresh-btn`}
              aria-label={labels.refreshLabel}
              title={labels.refreshLabel}
              disabled={disabled || isLoading}
              onClick={() => onRefresh()}
              style={{
                background: "transparent",
                border: "none",
                cursor: disabled || isLoading ? "not-allowed" : "pointer",
                padding: "3px",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-muted-foreground)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <OrciaIcon name="regenerate" size={14} />
            </button>
          )}

          <button
            type="button"
            data-testid={`${testId}-toggle-btn`}
            aria-label={labels.toggleListAriaLabel}
            tabIndex={-1}
            disabled={disabled}
            onClick={() => {
              if (!disabled) {
                setIsOpen((prev) => !prev);
                setHighlightedIndex(0);
              }
            }}
            style={{
              background: "transparent",
              border: "none",
              cursor: disabled ? "not-allowed" : "pointer",
              padding: "3px",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--color-muted-foreground)",
            }}
          >
            <OrciaIcon name={isOpen ? "arrowUp" : "chevronDown"} size={14} />
          </button>
        </div>
      </div>

      {errorMessage && (
        <div
          data-testid={`${testId}-error-msg`}
          style={{
            marginTop: "4px",
            fontSize: "11px",
            color: "var(--color-status-danger)",
            display: "flex",
            alignItems: "center",
            gap: "4px",
          }}
        >
          <span>{errorMessage}</span>
        </div>
      )}

      {isOpen && !disabled && (
        <OrciaModelComboboxDropdown
          effectiveId={effectiveId}
          listboxId={listboxId}
          testId={testId}
          value={value}
          displayedModels={displayedModels}
          highlightedIndex={highlightedIndex}
          labels={labels}
          onSelect={handleSelect}
          onHighlight={setHighlightedIndex}
        />
      )}
    </div>
  );
}

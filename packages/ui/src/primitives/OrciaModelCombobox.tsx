import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { OrciaIcon } from "../components/icons";
import { normalizeComboboxSearchToken } from "./comboboxSearchUtils";
import { OrciaSpinner } from "./OrciaSpinner";

export interface DiscoveredModelOption {
  readonly id: string;
  readonly displayName?: string | null;
  readonly description?: string | null;
  readonly usageHint?: "chat" | "embedding" | "unknown";
  readonly ownedBy?: string | null;
}

export interface OrciaModelComboboxLabels {
  readonly noModelsFound: string;
  readonly refreshLabel: string;
  readonly loadingLabel: string;
  readonly freeformHint?: string;
  readonly chatBadge?: string;
  readonly embeddingBadge?: string;
}

export interface OrciaModelComboboxProps {
  readonly id?: string;
  readonly testId: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly models: readonly DiscoveredModelOption[];
  readonly targetUsage?: "chat" | "embedding";
  readonly isLoading?: boolean;
  readonly errorMessage?: string | null;
  readonly onRefresh?: () => void;
  readonly placeholder?: string;
  readonly disabled?: boolean;
  readonly labels: OrciaModelComboboxLabels;
  readonly className?: string;
  readonly style?: React.CSSProperties;
  readonly maxDisplayedItems?: number;
}

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
            aria-label="Toggle models list"
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
        <div
          id={listboxId}
          role="listbox"
          data-testid={`${testId}-suggestions`}
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            zIndex: 100,
            maxHeight: "240px",
            overflowY: "auto",
            backgroundColor: "var(--color-surface-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            boxShadow: "var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.15))",
            padding: "4px 0",
          }}
        >
          {displayedModels.length === 0 ? (
            <div
              data-testid={`${testId}-no-match`}
              style={{
                padding: "8px 12px",
                fontSize: "12px",
                color: "var(--color-muted-foreground)",
              }}
            >
              {labels.noModelsFound}
              {labels.freeformHint && (
                <div style={{ fontSize: "11px", marginTop: "2px", opacity: 0.8 }}>
                  {labels.freeformHint}
                </div>
              )}
            </div>
          ) : (
            displayedModels.map((model, idx) => {
              const isSelected = model.id.toLowerCase() === value.toLowerCase().trim();
              const isHighlighted = idx === highlightedIndex;
              return (
                <div
                  key={model.id}
                  id={`${effectiveId}-opt-${model.id}`}
                  role="option"
                  aria-selected={isSelected || isHighlighted}
                  data-testid={`${testId}-option-${model.id}`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleSelect(model.id);
                  }}
                  onMouseEnter={() => setHighlightedIndex(idx)}
                  style={{
                    padding: "7px 12px",
                    fontSize: "12px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "8px",
                    backgroundColor: isHighlighted
                      ? "var(--color-action-primary-subtle)"
                      : "transparent",
                    color: isHighlighted
                      ? "var(--color-primary-cobalt)"
                      : "var(--color-foreground)",
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                    <span
                      style={{
                        fontWeight: isSelected ? 600 : 500,
                        fontFamily: "var(--font-mono)",
                        fontSize: "12px",
                      }}
                    >
                      {model.id}
                    </span>
                    {model.displayName && model.displayName !== model.id && (
                      <span
                        style={{
                          fontSize: "11px",
                          color: "var(--color-muted-foreground)",
                        }}
                      >
                        {model.displayName}
                      </span>
                    )}
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    {model.usageHint === "chat" && labels.chatBadge && (
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 600,
                          padding: "1px 5px",
                          borderRadius: "var(--radius-xs, 3px)",
                          backgroundColor: "var(--color-action-primary-subtle)",
                          color: "var(--color-primary-cobalt)",
                        }}
                      >
                        {labels.chatBadge}
                      </span>
                    )}
                    {model.usageHint === "embedding" && labels.embeddingBadge && (
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 600,
                          padding: "1px 5px",
                          borderRadius: "var(--radius-xs, 3px)",
                          backgroundColor: "var(--color-bg-elevated)",
                          color: "var(--color-foreground)",
                          border: "1px solid var(--color-border)",
                        }}
                      >
                        {labels.embeddingBadge}
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { OrciaIcon } from "../components/icons";
import { normalizeComboboxSearchToken } from "./comboboxSearchUtils";

export interface OrciaSearchableSelectOption {
  readonly value: string;
  readonly label: string;
  readonly subLabel?: string;
}

export interface OrciaSearchableSelectProps {
  readonly id?: string;
  readonly testId: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly options: readonly OrciaSearchableSelectOption[];
  readonly maxDisplayedItems?: number;
  readonly searchPlaceholder: string;
  readonly noMatchLabel: string;
  readonly truncatedHintTemplate?: (hiddenCount: number) => string;
  readonly truncatedHint?: string;
  readonly onSearchQueryChange?: (query: string) => void;
  readonly disabled?: boolean;
  readonly selectedLabelFallback?: string;
  readonly className?: string;
  readonly style?: React.CSSProperties;
}

const POPOVER_STYLE: React.CSSProperties = {
  position: "absolute",
  top: "calc(100% + 4px)",
  left: 0,
  right: 0,
  zIndex: 100,
  maxHeight: "300px",
  display: "flex",
  flexDirection: "column",
  backgroundColor: "var(--color-surface-card)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-sm)",
  boxShadow: "var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.15))",
  overflow: "hidden",
};

export function OrciaSearchableSelect({
  id,
  testId,
  value,
  onChange,
  options,
  maxDisplayedItems = 10,
  searchPlaceholder,
  noMatchLabel,
  truncatedHintTemplate,
  truncatedHint,
  onSearchQueryChange,
  disabled = false,
  selectedLabelFallback,
  className = "orcia-ds-select",
  style,
}: OrciaSearchableSelectProps): React.ReactElement {
  const generatedId = useId();
  const effectiveId = id || `searchable-select-${generatedId}`;
  const listboxId = `${effectiveId}-listbox`;

  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedOption = useMemo(() => options.find((opt) => opt.value === value), [options, value]);
  const triggerLabel = selectedOption?.label || selectedLabelFallback || value || searchPlaceholder;
  const normalizedQuery = normalizeComboboxSearchToken(searchQuery);

  const matchingOptions = useMemo(() => {
    if (!normalizedQuery) return options;
    return options.filter((opt) => {
      const matchLabel = normalizeComboboxSearchToken(opt.label).includes(normalizedQuery);
      const matchSub = opt.subLabel ? normalizeComboboxSearchToken(opt.subLabel).includes(normalizedQuery) : false;
      const matchVal = normalizeComboboxSearchToken(opt.value).includes(normalizedQuery);
      return matchLabel || matchSub || matchVal;
    });
  }, [options, normalizedQuery]);

  const displayedOptions = useMemo(
    () => matchingOptions.slice(0, maxDisplayedItems),
    [matchingOptions, maxDisplayedItems],
  );
  const hasTruncation = matchingOptions.length > maxDisplayedItems;
  const hiddenCount = matchingOptions.length - maxDisplayedItems;

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

  useEffect(() => {
    if (isOpen) {
      setHighlightedIndex(displayedOptions.length > 0 ? 0 : -1);
      requestAnimationFrame(() => inputRef.current?.focus());
    } else {
      setSearchQuery("");
      setHighlightedIndex(-1);
    }
  }, [isOpen]);

  const handleSelect = (optValue: string) => {
    onChange(optValue);
    setIsOpen(false);
    setSearchQuery("");
    setHighlightedIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return;
    if (e.key === "ArrowDown" && displayedOptions.length > 0) {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev + 1) % displayedOptions.length);
    } else if (e.key === "ArrowUp" && displayedOptions.length > 0) {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev <= 0 ? displayedOptions.length - 1 : prev - 1));
    } else if (e.key === "Enter" && highlightedIndex >= 0 && displayedOptions[highlightedIndex]) {
      e.preventDefault();
      handleSelect(displayedOptions[highlightedIndex].value);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
    }
  };

  const truncatedMsg = truncatedHintTemplate
    ? truncatedHintTemplate(hiddenCount)
    : truncatedHint || "";

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%", ...style }} data-testid={`${testId}-container`}>
      <select
        hidden
        aria-hidden="true"
        tabIndex={-1}
        id={id}
        data-testid={testId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
        {!selectedOption && value ? (
          <option key={value} value={value}>{selectedLabelFallback || value}</option>
        ) : null}
      </select>

      <button
        type="button"
        id={`${effectiveId}-trigger`}
        data-testid={`${testId}-trigger`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        disabled={disabled}
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        className={className}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: disabled ? "not-allowed" : "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{triggerLabel}</span>
        <OrciaIcon
          name="chevronDown"
          size={12}
          style={{
            marginLeft: "8px",
            color: "var(--color-muted-foreground)",
            transform: isOpen ? "rotate(180deg)" : "none",
            transition: "transform 150ms ease",
          }}
        />
      </button>

      {isOpen && !disabled && (
        <div id={listboxId} role="listbox" data-testid={`${testId}-listbox`} style={POPOVER_STYLE}>
          <div style={{ padding: "8px", borderBottom: "1px solid var(--color-border)" }}>
            <input
              ref={inputRef}
              name="orcia_select_filter_q"
              type="search"
              data-testid={`${testId}-search-input`}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="none"
              spellCheck={false}
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-protonpass-ignore="true"
              data-form-type="other"
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(e) => {
                const nextQuery = e.target.value;
                setSearchQuery(nextQuery);
                onSearchQueryChange?.(nextQuery);
              }}
              onKeyDown={handleKeyDown}
              className="orcia-ds-input"
              style={{ width: "100%", fontSize: "12px", padding: "6px 8px" }}
            />
          </div>

          <div style={{ overflowY: "auto", flex: 1, padding: "4px 0" }}>
            {matchingOptions.length === 0 ? (
              <div data-testid={`${testId}-no-match`} style={{ padding: "8px 12px", fontSize: "12px", color: "var(--color-muted-foreground)" }}>
                {noMatchLabel}
              </div>
            ) : (
              displayedOptions.map((opt, idx) => {
                const isSelected = opt.value === value;
                const isHighlighted = idx === highlightedIndex;
                return (
                  <div
                    key={opt.value}
                    role="option"
                    aria-selected={isSelected}
                    data-testid={`${testId}-option-${opt.value}`}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleSelect(opt.value);
                    }}
                    onMouseEnter={() => setHighlightedIndex(idx)}
                    style={{
                      padding: "8px 12px",
                      fontSize: "13px",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: "2px",
                      backgroundColor: isHighlighted ? "var(--color-surface-secondary)" : "transparent",
                      color: isHighlighted ? "var(--color-primary-cobalt)" : "var(--color-foreground)",
                    }}
                  >
                    <span style={{ fontWeight: isSelected ? 600 : 400 }}>{opt.label}</span>
                    {opt.subLabel ? (
                      <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)", fontFamily: "var(--font-mono)" }}>
                        {opt.subLabel}
                      </span>
                    ) : null}
                  </div>
                );
              })
            )}
          </div>

          {hasTruncation ? (
            <div
              data-testid={`${testId}-truncated-hint`}
              style={{
                padding: "6px 12px",
                fontSize: "11px",
                color: "var(--color-muted-foreground)",
                backgroundColor: "var(--color-surface-secondary)",
                borderTop: "1px solid var(--color-border)",
                textAlign: "center",
              }}
            >
              {truncatedMsg}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

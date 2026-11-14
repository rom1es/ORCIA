import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { normalizeComboboxSearchToken } from "./comboboxSearchUtils";

export interface KnownUserOption {
  readonly principalId: string;
  readonly displayName: string;
  readonly email?: string | null;
}

export interface OrciaKnownUserComboboxProps {
  readonly inputId?: string;
  readonly inputTestId?: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly knownUsers: readonly KnownUserOption[];
  readonly excludedPrincipalIds?: readonly string[];
  readonly placeholder?: string;
  readonly disabled?: boolean;
  readonly noResultsLabel?: string;
  readonly ariaLabel?: string;
  readonly onBlur?: () => void;
  readonly onSelectOption?: (user: KnownUserOption) => void;
  readonly className?: string;
  readonly style?: React.CSSProperties;
}

export function OrciaKnownUserCombobox({
  inputId,
  inputTestId = "known-user-combobox",
  value,
  onChange,
  knownUsers,
  excludedPrincipalIds = [],
  placeholder,
  disabled = false,
  noResultsLabel = "Aucun utilisateur trouvé",
  ariaLabel,
  onBlur,
  onSelectOption,
  className = "orcia-ds-input",
  style,
}: OrciaKnownUserComboboxProps): React.ReactElement {
  const generatedId = useId();
  const effectiveId = inputId || `combobox-${generatedId}`;
  const listboxId = `${effectiveId}-suggestions`;

  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  const excludedSet = useMemo(
    () => new Set(excludedPrincipalIds.map((id) => id.toLowerCase().trim())),
    [excludedPrincipalIds],
  );

  const availableUsers = useMemo(
    () => knownUsers.filter((u) => !excludedSet.has(u.principalId.toLowerCase().trim())),
    [knownUsers, excludedSet],
  );

  const matchingUsers = useMemo(() => {
    const query = normalizeComboboxSearchToken(value);
    if (!query) {
      return availableUsers;
    }
    return availableUsers.filter((user) => {
      const matchName = normalizeComboboxSearchToken(user.displayName).includes(query);
      const matchPrincipal = normalizeComboboxSearchToken(user.principalId).includes(query);
      const matchEmail = user.email ? normalizeComboboxSearchToken(user.email).includes(query) : false;
      return matchName || matchPrincipal || matchEmail;
    });
  }, [availableUsers, value]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleSelect = (user: KnownUserOption) => {
    onChange(user.principalId);
    onSelectOption?.(user);
    setIsOpen(false);
    setHighlightedIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        setHighlightedIndex(matchingUsers.length > 0 ? 0 : -1);
      } else if (matchingUsers.length > 0) {
        setHighlightedIndex((prev) => (prev + 1) % matchingUsers.length);
      }
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        setHighlightedIndex(matchingUsers.length > 0 ? matchingUsers.length - 1 : -1);
      } else if (matchingUsers.length > 0) {
        setHighlightedIndex((prev) => (prev <= 0 ? matchingUsers.length - 1 : prev - 1));
      }
      return;
    }

    if (e.key === "Enter") {
      if (isOpen && highlightedIndex >= 0 && matchingUsers[highlightedIndex]) {
        e.preventDefault();
        handleSelect(matchingUsers[highlightedIndex]);
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
    isOpen && highlightedIndex >= 0 && matchingUsers[highlightedIndex]
      ? `${effectiveId}-option-${matchingUsers[highlightedIndex].principalId}`
      : undefined;

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", width: "100%", ...style }}
      data-testid={`${inputTestId}-container`}
    >
      <input
        id={effectiveId}
        type="text"
        role="combobox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={activeDescendantId}
        aria-label={ariaLabel}
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        data-testid={inputTestId}
        disabled={disabled}
        value={value}
        placeholder={placeholder}
        className={className}
        style={{ width: "100%" }}
        onChange={(e) => {
          onChange(e.target.value);
          if (!isOpen) setIsOpen(true);
          setHighlightedIndex(0);
        }}
        onFocus={() => {
          if (!disabled) {
            setIsOpen(true);
            setHighlightedIndex(0);
          }
        }}
        onBlur={() => {
          onBlur?.();
        }}
        onKeyDown={handleKeyDown}
      />

      {isOpen && !disabled && (
        <div
          id={listboxId}
          role="listbox"
          data-testid={`${inputTestId}-suggestions`}
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            zIndex: 100,
            maxHeight: "220px",
            overflowY: "auto",
            backgroundColor: "var(--color-surface-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            boxShadow: "var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.15))",
            padding: "4px 0",
          }}
        >
          {matchingUsers.length === 0 ? (
            <div
              data-testid={`${inputTestId}-no-match`}
              style={{
                padding: "8px 12px",
                fontSize: "12px",
                color: "var(--color-muted-foreground)",
              }}
            >
              {noResultsLabel}
            </div>
          ) : (
            matchingUsers.map((user, idx) => {
              const isSelected = user.principalId.toLowerCase() === value.toLowerCase().trim();
              const isHighlighted = idx === highlightedIndex;
              return (
                <div
                  key={user.principalId}
                  id={`${effectiveId}-option-${user.principalId}`}
                  role="option"
                  aria-selected={isSelected || isHighlighted}
                  data-testid={`${inputTestId}-option-${user.principalId}`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleSelect(user);
                  }}
                  onMouseEnter={() => setHighlightedIndex(idx)}
                  style={{
                    padding: "8px 12px",
                    fontSize: "13px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "8px",
                    backgroundColor: isHighlighted
                      ? "var(--color-surface-secondary)"
                      : "transparent",
                    color: isHighlighted
                      ? "var(--color-primary-cobalt)"
                      : "var(--color-foreground)",
                  }}
                >
                  <span style={{ fontWeight: isSelected ? 600 : 400 }}>
                    {user.displayName}
                  </span>
                  <span
                    style={{
                      fontSize: "11px",
                      color: "var(--color-muted-foreground)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {user.email && user.email !== user.principalId
                      ? `${user.principalId} (${user.email})`
                      : user.principalId}
                  </span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

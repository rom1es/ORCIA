import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { normalizeComboboxSearchToken } from "./comboboxSearchUtils";
import { OrciaKnownUserComboboxDropdown } from "./OrciaKnownUserComboboxDropdown";

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
  readonly maxDisplayedItems?: number;
  readonly hasMoreMatches?: boolean;
  readonly truncatedHint?: string;
  readonly onSearchQueryChange?: (query: string) => void;
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
  maxDisplayedItems = 10,
  hasMoreMatches = false,
  truncatedHint,
  onSearchQueryChange,
  placeholder,
  disabled = false,
  noResultsLabel = "",
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
      const matchEmail = user.email
        ? normalizeComboboxSearchToken(user.email).includes(query)
        : false;
      return matchName || matchPrincipal || matchEmail;
    });
  }, [availableUsers, value]);

  const displayedUsers = useMemo(
    () => matchingUsers.slice(0, maxDisplayedItems),
    [matchingUsers, maxDisplayedItems],
  );

  const isTruncated = matchingUsers.length > maxDisplayedItems || Boolean(hasMoreMatches);

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
        setHighlightedIndex(displayedUsers.length > 0 ? 0 : -1);
      } else if (displayedUsers.length > 0) {
        setHighlightedIndex((prev) => (prev + 1) % displayedUsers.length);
      }
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        setHighlightedIndex(displayedUsers.length > 0 ? displayedUsers.length - 1 : -1);
      } else if (displayedUsers.length > 0) {
        setHighlightedIndex((prev) => (prev <= 0 ? displayedUsers.length - 1 : prev - 1));
      }
      return;
    }

    if (e.key === "Enter") {
      if (isOpen && highlightedIndex >= 0 && displayedUsers[highlightedIndex]) {
        e.preventDefault();
        handleSelect(displayedUsers[highlightedIndex]);
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
    isOpen && highlightedIndex >= 0 && displayedUsers[highlightedIndex]
      ? `${effectiveId}-option-${displayedUsers[highlightedIndex].principalId}`
      : undefined;

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", width: "100%", ...style }}
      data-testid={`${inputTestId}-container`}
    >
      <input
        id={effectiveId}
        name="orcia_directory_filter_q"
        type="search"
        role="combobox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={activeDescendantId}
        aria-label={ariaLabel}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="none"
        spellCheck={false}
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-protonpass-ignore="true"
        data-form-type="other"
        data-testid={inputTestId}
        disabled={disabled}
        value={value}
        placeholder={placeholder}
        className={className}
        style={{ width: "100%" }}
        onChange={(e) => {
          const nextVal = e.target.value;
          onChange(nextVal);
          onSearchQueryChange?.(nextVal);
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
        <OrciaKnownUserComboboxDropdown
          effectiveId={effectiveId}
          listboxId={listboxId}
          inputTestId={inputTestId}
          value={value}
          displayedUsers={displayedUsers}
          highlightedIndex={highlightedIndex}
          noResultsLabel={noResultsLabel}
          isTruncated={isTruncated}
          truncatedHint={truncatedHint}
          onHighlight={setHighlightedIndex}
          onSelectUser={handleSelect}
        />
      )}
    </div>
  );
}

import React from "react";

export interface UiAssistantAutocompleteSuggestion {
  readonly id: string;
  readonly kind: "agent" | "skill";
  readonly token: string;
  readonly name: string;
  readonly description: string;
  readonly badge?: string;
}

export function extractAutocompleteTrigger(promptText: string): {
  readonly kind: "agent" | "skill";
  readonly query: string;
} | null {
  const match = /(?:^|\s)(@|\/)([a-zA-Z0-9_/:.-]*)$/.exec(promptText);
  if (!match) return null;
  const prefix = match[1];
  const query = (match[2] ?? "").toLowerCase();
  return {
    kind: prefix === "@" ? "agent" : "skill",
    query,
  };
}

export function applyAutocompleteSuggestionToPrompt(
  promptText: string,
  token: string,
): string {
  return promptText.replace(/(?:^|\s)(?:@|\/)[a-zA-Z0-9_/:.-]*$/, (m) => {
    const leadingSpace = m.startsWith(" ") ? " " : "";
    return `${leadingSpace}${token} `;
  });
}

export function AssistantAutocompleteDropdown({
  suggestions,
  ariaLabel,
  onSelectSuggestion,
}: {
  readonly suggestions: readonly UiAssistantAutocompleteSuggestion[];
  readonly ariaLabel?: string;
  readonly onSelectSuggestion: (item: UiAssistantAutocompleteSuggestion) => void;
}): React.JSX.Element | null {
  if (suggestions.length === 0) return null;
  return (
    <div
      data-testid="assistant-autocomplete-dropdown"
      role="listbox"
      aria-label={ariaLabel}
      className="mt-2 max-h-52 overflow-y-auto rounded-lg border border-border-subtle bg-surface-primary p-1.5 text-xs shadow-md space-y-1"
    >
      {suggestions.map((item) => (
        <button
          key={item.id}
          type="button"
          role="option"
          aria-selected={false}
          data-testid={`assistant-autocomplete-option-${item.token.slice(1).replace(/[/:]/g, "-")}`}
          onClick={() => onSelectSuggestion(item)}
          className="flex w-full items-center justify-between gap-2 rounded px-2.5 py-1.5 text-left hover:bg-surface-secondary"
        >
          <div className="flex flex-wrap items-center gap-2">
            <code className="rounded border border-border-subtle bg-surface-secondary px-1.5 py-0.5 font-mono text-[11px] font-semibold">
              {item.token}
            </code>
            <span className="font-semibold text-text-primary">{item.name}</span>
            <span className="text-[11px] text-text-secondary">{item.description}</span>
          </div>
          {item.badge && (
            <span className="rounded-full border border-border-subtle bg-surface-secondary px-2 py-0.5 text-[10px]">
              {item.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

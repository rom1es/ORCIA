import React, { useState } from "react";
import type {
  PackComposerModalLabels,
  UiPackClosureIssue,
  UiPackDraftMemberOption,
  UiPackProseWarning,
} from "./PackUiTypes";
import { StatusBadge } from "./StatusBadge";

export interface PackComposerMembersStepProps {
  readonly availableMembers: readonly UiPackDraftMemberOption[];
  readonly selectedMemberKeys: readonly string[];
  readonly closureComplete: boolean;
  readonly missingDependencies: readonly UiPackClosureIssue[];
  readonly nonActiveDependencies: readonly UiPackClosureIssue[];
  readonly proseWarnings: readonly UiPackProseWarning[];
  readonly autoIncludeDependencies: boolean;
  readonly readOnlyObserver: boolean;
  readonly isBusy: boolean;
  readonly labels: PackComposerModalLabels;
  readonly onToggleMember: (option: UiPackDraftMemberOption) => void;
  readonly onToggleAutoInclude: (checked: boolean) => void;
}

export function memberSelectionKey(
  item: Pick<UiPackDraftMemberOption, "entityType" | "entityId">,
): string {
  return `${item.entityType}:${item.entityId}`;
}

export function PackComposerMembersStep({
  availableMembers,
  selectedMemberKeys,
  closureComplete,
  missingDependencies,
  nonActiveDependencies,
  proseWarnings,
  autoIncludeDependencies,
  readOnlyObserver,
  isBusy,
  labels,
  onToggleMember,
  onToggleAutoInclude,
}: PackComposerMembersStepProps): React.ReactElement {
  const [searchQuery, setSearchQuery] = useState("");
  const normalizedQuery = searchQuery.trim().toLowerCase();
  const filtered = availableMembers.filter(
    (m) =>
      !normalizedQuery ||
      m.title.toLowerCase().includes(normalizedQuery) ||
      m.entitySlug.toLowerCase().includes(normalizedQuery) ||
      m.entityType.toLowerCase().includes(normalizedQuery),
  );
  const selectedSet = new Set(selectedMemberKeys);

  return (
    <div className="flex flex-col gap-3" data-testid="pack-composer-members-step">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <input
          type="text"
          value={searchQuery}
          placeholder={labels.membersSearchPlaceholder}
          aria-label={labels.membersSearchPlaceholder}
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="pack-composer-members-search"
          onChange={(e) => setSearchQuery(e.target.value)}
          className="orcia-ds-input flex-1"
        />
        <StatusBadge
          label={closureComplete ? labels.closureCompleteBadge : labels.closureIncompleteBadge}
          tone={closureComplete ? "emerald" : "crimson"}
        />
      </div>

      {filtered.length === 0 ? (
        <p className="text-xs text-[var(--orcia-text-secondary)]">{labels.membersEmptyHint}</p>
      ) : (
        <div
          className="flex max-h-56 flex-col gap-1.5 overflow-y-auto rounded border p-2"
          style={{ borderColor: "var(--color-border-subtle)" }}
        >
          {filtered.map((item) => {
            const key = memberSelectionKey(item);
            const checked = selectedSet.has(key);
            return (
              <label
                key={key}
                data-testid={`pack-composer-member-option-${item.entitySlug}`}
                className="flex items-center justify-between gap-2 rounded px-2 py-1 text-xs hover:bg-[var(--orcia-surface-secondary)]"
              >
                <span className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={readOnlyObserver || isBusy}
                    autoComplete="off"
                    data-lpignore="true"
                    data-1p-ignore="true"
                    data-bwignore="true"
                    data-form-type="other"
                    data-testid={`pack-composer-member-checkbox-${item.entitySlug}`}
                    onChange={() => onToggleMember(item)}
                  />
                  <span className="font-semibold">{item.title}</span>
                  <code className="font-mono text-[11px] text-[var(--orcia-text-secondary)]">
                    {item.entitySlug}
                  </code>
                </span>
                <StatusBadge
                  label={labels.entityTypeLabels[item.entityType]}
                  tone="neutral"
                />
              </label>
            );
          })}
        </div>
      )}

      {(missingDependencies.length > 0 || nonActiveDependencies.length > 0) && (
        <div
          data-testid="pack-composer-closure-gaps"
          className="rounded border p-2.5 text-xs"
          style={{
            borderColor: "var(--color-stale-crimson)",
            backgroundColor: "var(--color-stale-bg)",
          }}
        >
          <strong className="block">{labels.missingDependenciesTitle}</strong>
          <ul className="mt-1 list-disc pl-4">
            {[...missingDependencies, ...nonActiveDependencies].map((gap) => (
              <li key={`${gap.entityType}:${gap.entityId}:${gap.referencedBy}`}>
                <span className="font-mono">{`${gap.entityType}:${gap.entityId}`}</span>
                {` — ${gap.reason}`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {proseWarnings.length > 0 && (
        <div
          data-testid="pack-composer-prose-warnings"
          className="rounded border p-2.5 text-xs"
          style={{
            borderColor: "var(--color-arbitration-amber)",
            backgroundColor: "var(--color-arbitration-bg)",
          }}
        >
          <strong className="block">{labels.proseWarningsTitle}</strong>
          <ul className="mt-1 list-disc pl-4">
            {proseWarnings.map((w, idx) => (
              <li key={`${w.entitySlug}-${w.token}-${idx}`}>
                <span className="font-mono">{w.token}</span>
                {` — ${w.message}`}
              </li>
            ))}
          </ul>
        </div>
      )}

      <label className="inline-flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={autoIncludeDependencies}
          disabled={readOnlyObserver || isBusy}
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="pack-composer-auto-include-checkbox"
          onChange={(e) => onToggleAutoInclude(e.target.checked)}
        />
        <span>{labels.autoIncludeDependenciesLabel}</span>
      </label>
    </div>
  );
}

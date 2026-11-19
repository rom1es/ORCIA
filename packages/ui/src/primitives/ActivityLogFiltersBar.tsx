import React from "react";
import type {
  ActivityLogExplorerLabels,
  ActivityMaxLimitOption,
  ActivityTimeWindowOption,
  UiActivityScopeFilterOption,
} from "./ActivityLogExplorerView";

export interface ActivityLogFiltersBarProps {
  readonly labels: ActivityLogExplorerLabels;
  readonly scopeOptions: readonly UiActivityScopeFilterOption[];
  readonly selectedScopeId: string;
  readonly onScopeChange: (scopeId: string) => void;
  readonly allowAllScopesOption?: boolean;
  readonly distinctActors: readonly string[];
  readonly selectedActor: string;
  readonly onActorChange: (actor: string) => void;
  readonly actorSearchQuery: string;
  readonly onActorSearchChange: (query: string) => void;
  readonly maxLimit: ActivityMaxLimitOption;
  readonly onMaxLimitChange: (limit: ActivityMaxLimitOption) => void;
  readonly timeWindow: ActivityTimeWindowOption;
  readonly onTimeWindowChange: (window: ActivityTimeWindowOption) => void;
  readonly dateFrom: string;
  readonly onDateFromChange: (val: string) => void;
  readonly dateTo: string;
  readonly onDateToChange: (val: string) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "12px",
  width: "100%",
  maxWidth: "100%",
  minWidth: 0,
  boxSizing: "border-box",
};

export function ActivityLogFiltersBar({
  labels,
  scopeOptions,
  selectedScopeId,
  onScopeChange,
  allowAllScopesOption = true,
  distinctActors,
  selectedActor,
  onActorChange,
  actorSearchQuery,
  onActorSearchChange,
  maxLimit,
  onMaxLimitChange,
  timeWindow,
  onTimeWindowChange,
  dateFrom,
  onDateFromChange,
  dateTo,
  onDateToChange,
}: ActivityLogFiltersBarProps): React.ReactElement {
  return (
    <>
      <div
        data-testid="activity-filters-bar"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(min(200px, 100%), 1fr))",
          gap: "10px",
          marginTop: "4px",
          width: "100%",
          minWidth: 0,
        }}
      >
        {/* 1. Observation Scope Filter */}
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", minWidth: 0, maxWidth: "100%" }}>
          <span style={{ fontWeight: 600 }}>{labels.scopeFilterLabel}</span>
          <select
            data-testid="activity-scope-filter-select"
            value={selectedScopeId}
            onChange={(e) => onScopeChange(e.target.value)}
            style={inputStyle}
          >
            {scopeOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
            {allowAllScopesOption && !scopeOptions.some((o) => o.id === "ALL") && (
              <option value="ALL">{labels.allScopesOptionLabel}</option>
            )}
          </select>
        </label>

        {/* 2. User / Author Filter + Search */}
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", minWidth: 0, maxWidth: "100%" }}>
          <span style={{ fontWeight: 600 }}>{labels.userFilterLabel}</span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", minWidth: 0, maxWidth: "100%" }}>
            <select
              data-testid="activity-user-filter-select"
              value={selectedActor}
              onChange={(e) => onActorChange(e.target.value)}
              style={{ ...inputStyle, flex: "1 1 120px" }}
            >
              <option value="ALL">{labels.allUsersOptionLabel}</option>
              {distinctActors.map((actor) => (
                <option key={actor} value={actor}>
                  {actor}
                </option>
              ))}
            </select>
            <input
              type="text"
              spellCheck={false}
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="activity-user-search-input"
              value={actorSearchQuery}
              onChange={(e) => onActorSearchChange(e.target.value)}
              placeholder={labels.userSearchPlaceholder}
              style={{ ...inputStyle, flex: "1 1 110px" }}
            />
          </div>
        </label>

        {/* 3. Max Recent Limit Filter */}
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", minWidth: 0, maxWidth: "100%" }}>
          <span style={{ fontWeight: 600 }}>{labels.maxLimitFilterLabel}</span>
          <select
            data-testid="activity-max-limit-select"
            value={String(maxLimit)}
            onChange={(e) => onMaxLimitChange(Number(e.target.value) as ActivityMaxLimitOption)}
            style={inputStyle}
          >
            <option value="50">{labels.limit50Label}</option>
            <option value="100">{labels.limit100Label}</option>
            <option value="200">{labels.limit200Label}</option>
            <option value="500">{labels.limit500Label}</option>
          </select>
        </label>

        {/* 4. Time Window Filter */}
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{labels.timeWindowFilterLabel}</span>
          <select
            data-testid="activity-time-window-select"
            value={timeWindow}
            onChange={(e) => onTimeWindowChange(e.target.value as ActivityTimeWindowOption)}
            style={inputStyle}
          >
            <option value="ALL">{labels.windowAllLabel}</option>
            <option value="1H">{labels.window1hLabel}</option>
            <option value="24H">{labels.window24hLabel}</option>
            <option value="7D">{labels.window7dLabel}</option>
            <option value="30D">{labels.window30dLabel}</option>
          </select>
        </label>
      </div>

      {/* Optional Custom Date Bounds */}
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px", fontSize: "12px" }}>
        <label style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ color: "var(--color-muted-foreground)" }}>{labels.customDateFromLabel}</span>
          <input
            type="date"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="activity-date-from-input"
            value={dateFrom}
            onChange={(e) => onDateFromChange(e.target.value)}
            style={inputStyle}
          />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ color: "var(--color-muted-foreground)" }}>{labels.customDateToLabel}</span>
          <input
            type="date"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="activity-date-to-input"
            value={dateTo}
            onChange={(e) => onDateToChange(e.target.value)}
            style={inputStyle}
          />
        </label>
      </div>
    </>
  );
}

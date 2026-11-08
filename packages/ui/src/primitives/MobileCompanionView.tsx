import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";

export type ResponsiveBreakpointTier = "DESKTOP" | "LAPTOP" | "MOBILE";
export type MobileCompanionTabId = "inbox" | "arbitration" | "briefing";
export type SemanticStateBadgeKind =
  | "HUMAN_ANCHOR"
  | "AI_ARBITRATION"
  | "GATE"
  | "STALE_WARNING";

export function resolveResponsiveBreakpoint(
  viewportWidthPx: number,
): ResponsiveBreakpointTier {
  if (viewportWidthPx >= 1280) return "DESKTOP";
  if (viewportWidthPx >= 768) return "LAPTOP";
  return "MOBILE";
}

export interface MobileCompanionLabels {
  readonly companionTitle: string;
  readonly tabInbox: string;
  readonly tabArbitration: string;
  readonly tabBriefing: string;
  readonly desktopOnlyBanner: string;
  readonly blockedYamlEditorLabel: string;
  readonly blockedHeavyCoEditingLabel: string;
  readonly blockedAdminModuleLabel: string;
  readonly badgeHumanAnchor: string;
  readonly badgeAiArbitration: string;
  readonly badgeGate: string;
  readonly badgeStaleWarning: string;
  readonly approveSectionCta: string;
  readonly liveRegionDefault: string;
}

export interface MobileCompanionViewProps {
  readonly viewportWidthPx?: number;
  readonly activeTab?: MobileCompanionTabId;
  readonly attemptedDesktopOnlyFeature?:
    | "YAML_EDITOR"
    | "HEAVY_CO_EDITING"
    | "ADMIN_MODULE"
    | null;
  readonly liveAnnouncement?: string;
  readonly inboxCount?: number;
  readonly briefingSections?: readonly {
    readonly sectionId: string;
    readonly title: string;
    readonly approved: boolean;
  }[];
  readonly labels: MobileCompanionLabels;
  readonly onChangeTab?: (tab: MobileCompanionTabId) => void;
  readonly onApproveBriefingSection?: (sectionId: string) => void;
}

export function MobileCompanionView({
  viewportWidthPx = 390,
  activeTab: controlledTab,
  attemptedDesktopOnlyFeature = null,
  liveAnnouncement,
  inboxCount = 2,
  briefingSections = [],
  labels,
  onChangeTab,
  onApproveBriefingSection,
}: MobileCompanionViewProps) {
  const [internalTab, setInternalTab] = useState<MobileCompanionTabId>("inbox");
  const currentTab = controlledTab ?? internalTab;
  const breakpoint = resolveResponsiveBreakpoint(viewportWidthPx);

  const selectTab = (tab: MobileCompanionTabId) => {
    setInternalTab(tab);
    onChangeTab?.(tab);
  };

  const semanticBadges: readonly {
    kind: SemanticStateBadgeKind;
    text: string;
  }[] = [
    { kind: "HUMAN_ANCHOR", text: labels.badgeHumanAnchor },
    { kind: "AI_ARBITRATION", text: labels.badgeAiArbitration },
    { kind: "GATE", text: labels.badgeGate },
    { kind: "STALE_WARNING", text: labels.badgeStaleWarning },
  ];

  return (
    <section
      data-testid="mobile-companion-view"
      data-breakpoint={breakpoint}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        padding: "12px",
        borderRadius: "10px",
        border: "1px solid var(--orcia-border-subtle)",
        backgroundColor: "var(--orcia-surface-elevated)",
      }}
    >
      <div
        role="status"
        aria-live="polite"
        data-testid="wcag-live-region"
        style={{
          fontSize: "0.75rem",
          color: "var(--orcia-text-secondary)",
        }}
      >
        {liveAnnouncement ?? labels.liveRegionDefault}
      </div>

      <div
        data-testid="wcag-semantic-badges"
        style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}
      >
        {semanticBadges.map((b) => (
          <span
            key={b.kind}
            data-testid={`semantic-badge-${b.kind}`}
            style={{
              padding: "3px 8px",
              borderRadius: "9999px",
              fontSize: "0.75rem",
              fontWeight: 600,
              border: "1px solid var(--orcia-border-subtle)",
              backgroundColor: "var(--orcia-surface-secondary)",
              color: "var(--orcia-text-primary)",
            }}
          >
            {b.text}
          </span>
        ))}
      </div>

      {breakpoint === "MOBILE" && attemptedDesktopOnlyFeature ? (
        <div
          role="alert"
          data-testid="desktop-only-restriction-banner"
          style={{
            padding: "10px 12px",
            borderRadius: "8px",
            border: "1px solid var(--orcia-status-warning, var(--orcia-border-subtle))",
            backgroundColor: "var(--orcia-surface-secondary)",
            fontWeight: 600,
            fontSize: "0.8125rem",
          }}
        >
          <OrciaIcon name="desktop" /> {labels.desktopOnlyBanner} (
          {attemptedDesktopOnlyFeature === "YAML_EDITOR"
            ? labels.blockedYamlEditorLabel
            : attemptedDesktopOnlyFeature === "HEAVY_CO_EDITING"
              ? labels.blockedHeavyCoEditingLabel
              : labels.blockedAdminModuleLabel}
          )
        </div>
      ) : null}

      <div data-testid={`mobile-tab-content-${currentTab}`}>
        {currentTab === "inbox" ? (
          <div style={{ fontSize: "0.8125rem" }}>
            <strong>{labels.tabInbox}</strong> ({inboxCount})
          </div>
        ) : null}

        {currentTab === "arbitration" ? (
          <div style={{ fontSize: "0.8125rem" }}>
            <strong>{labels.tabArbitration}</strong>
          </div>
        ) : null}

        {currentTab === "briefing" ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <strong style={{ fontSize: "0.8125rem" }}>{labels.tabBriefing}</strong>
            {briefingSections.map((sec) => (
              <div
                key={sec.sectionId}
                data-testid={`mobile-briefing-section-${sec.sectionId}`}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "6px 8px",
                  borderRadius: "6px",
                  border: "1px solid var(--orcia-border-subtle)",
                }}
              >
                <span style={{ fontSize: "0.8125rem" }}>{sec.title}</span>
                <button
                  type="button"
                  data-testid={`mobile-approve-btn-${sec.sectionId}`}
                  onClick={() => onApproveBriefingSection?.(sec.sectionId)}
                  style={{
                    padding: "3px 8px",
                    borderRadius: "6px",
                    fontSize: "0.75rem",
                    border: "1px solid var(--orcia-border-subtle)",
                    backgroundColor: "var(--orcia-surface-secondary)",
                    color: "var(--orcia-text-primary)",
                    cursor: "pointer",
                  }}
                >
                  {labels.approveSectionCta}
                </button>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      <nav
        aria-label={labels.companionTitle}
        data-testid="mobile-bottom-tab-bar"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "6px",
          paddingTop: "8px",
          borderTop: "1px solid var(--orcia-border-subtle)",
        }}
      >
        {(
          [
            { id: "inbox", text: labels.tabInbox },
            { id: "arbitration", text: labels.tabArbitration },
            { id: "briefing", text: labels.tabBriefing },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            type="button"
            data-testid={`mobile-tab-btn-${tab.id}`}
            aria-current={currentTab === tab.id ? "page" : undefined}
            onClick={() => selectTab(tab.id)}
            style={{
              padding: "8px",
              borderRadius: "8px",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
              border:
                currentTab === tab.id
                  ? "1px solid var(--orcia-action-primary)"
                  : "1px solid var(--orcia-border-subtle)",
              backgroundColor:
                currentTab === tab.id
                  ? "var(--orcia-surface-secondary)"
                  : "var(--orcia-surface-primary)",
              color: "var(--orcia-text-primary)",
            }}
          >
            {tab.text}
          </button>
        ))}
      </nav>
    </section>
  );
}

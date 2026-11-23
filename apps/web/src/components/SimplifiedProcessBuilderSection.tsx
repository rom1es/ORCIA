import { StatusBadge } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../i18n";
import { CreateProcessFormDialog } from "./CreateProcessFormDialog";
import type { ConfiguredWorkflowItem } from "./platformSetupStore";

export interface SimplifiedProcessBuilderSectionProps {
  readonly isFr: boolean;
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly upsertWorkflow: (input: ConfiguredWorkflowItem) => void;
  readonly onOpenProcessesMenu?: () => void;
  readonly presetDraft?: ConfiguredWorkflowItem | null;
}

const secondaryBtnStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontWeight: 600,
  fontSize: "12px",
  cursor: "pointer",
};

export function SimplifiedProcessBuilderSection({
  isFr,
  workflows,
  openHelpSection,
  upsertWorkflow,
  onOpenProcessesMenu,
  presetDraft,
}: SimplifiedProcessBuilderSectionProps) {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const copy = resolveDictionaryForFlag(isFr).shellChrome.simplifiedProcessBuilder;

  useEffect(() => {
    if (presetDraft) {
      setIsCreateModalOpen(true);
    }
  }, [presetDraft]);

  const publishedCount = workflows.filter((w) => w.status === "PUBLISHED").length;
  const draftCount = workflows.filter((w) => w.status === "DRAFT").length;

  return (
    <section
      data-testid="settings-workflows-section"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      <div
        className="orcia-bento-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <h2 style={{ margin: 0, fontSize: "16px" }}>{copy.title}</h2>
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {copy.description}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          {publishedCount > 0 ? (
            <StatusBadge
              label={formatI18nTemplate(copy.publishedBadgeTemplate, { count: publishedCount })}
              tone="emerald"
            />
          ) : null}
          {draftCount > 0 ? (
            <StatusBadge
              label={formatI18nTemplate(copy.draftsBadgeTemplate, { count: draftCount })}
              tone="cobalt"
            />
          ) : null}
          <button
            type="button"
            data-testid="open-create-process-modal-btn"
            onClick={() => setIsCreateModalOpen(true)}
            className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
          >
            {copy.newProcessCta}
          </button>
          {onOpenProcessesMenu ? (
            <button
              type="button"
              data-testid="settings-workflows-open-processes-menu-btn"
              onClick={onOpenProcessesMenu}
              style={secondaryBtnStyle}
            >
              {copy.openProcessesMenuCta}
            </button>
          ) : null}
        </div>
      </div>

      <CreateProcessFormDialog
        open={isCreateModalOpen}
        onOpenChange={setIsCreateModalOpen}
        isFr={isFr}
        openHelpSection={openHelpSection}
        upsertWorkflow={upsertWorkflow}
        presetDraft={presetDraft}
      />

      <div className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <strong style={{ fontSize: "14px" }}>
          {workflows.length > 0
            ? formatI18nTemplate(copy.savedProcessesCountTemplate, { count: workflows.length })
            : copy.savedProcessesTitle}
        </strong>
        {workflows.length === 0 ? (
          <p data-testid="workflows-empty-state" style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {copy.emptyState}
          </p>
        ) : (
          <div data-testid="workflow-saved-list" style={{ display: "grid", gap: "8px" }}>
            {workflows.map((wf) => (
              <div
                key={wf.workflowKey}
                data-testid={`workflow-row-${wf.workflowKey}`}
                style={{
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <div>
                  <strong>{wf.title}</strong>{" "}
                  <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
                    ({wf.workflowKey} · v{wf.version})
                  </span>
                </div>
                <StatusBadge
                  label={wf.status === "PUBLISHED" ? copy.statusPublished : copy.statusDraft}
                  tone={wf.status === "PUBLISHED" ? "emerald" : "cobalt"}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

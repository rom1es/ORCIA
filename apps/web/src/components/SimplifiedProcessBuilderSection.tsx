import { StatusBadge } from "@orcia/ui";
import React, { useEffect, useState } from "react";
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
            <h2 style={{ margin: 0, fontSize: "16px" }}>
              {isFr
                ? "Créer et Gérer mes Processus Métiers"
                : "Create and Manage Business Processes"}
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr
              ? "Définissez un processus réutilisable qui combine vos agents et vos validations humaines."
              : "Define a reusable process combining your agents and human reviews."}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          {publishedCount > 0 ? (
            <StatusBadge
              label={isFr ? `Publiés : ${publishedCount}` : `Published: ${publishedCount}`}
              tone="emerald"
            />
          ) : null}
          {draftCount > 0 ? (
            <StatusBadge
              label={isFr ? `Brouillons : ${draftCount}` : `Drafts: ${draftCount}`}
              tone="cobalt"
            />
          ) : null}
          <button
            type="button"
            data-testid="open-create-process-modal-btn"
            onClick={() => setIsCreateModalOpen(true)}
            className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
          >
            {isFr ? "+ Nouveau processus" : "+ New process"}
          </button>
          {onOpenProcessesMenu ? (
            <button
              type="button"
              data-testid="settings-workflows-open-processes-menu-btn"
              onClick={onOpenProcessesMenu}
              style={secondaryBtnStyle}
            >
              {isFr ? "Ouvrir dans Mes Processus →" : "Open in My Processes →"}
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

      {/* Liste des processus enregistrés */}
      <div className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <strong style={{ fontSize: "14px" }}>
          {workflows.length > 0
            ? isFr
              ? `Processus enregistrés (${workflows.length})`
              : `Saved processes (${workflows.length})`
            : isFr
              ? "Processus enregistrés"
              : "Saved processes"}
        </strong>
        {workflows.length === 0 ? (
          <p data-testid="workflows-empty-state" style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr
              ? "Aucun processus enregistré pour le moment. Cliquez sur « + Nouveau processus » pour créer votre premier processus."
              : "No process saved yet. Click '+ New process' to create your first process."}
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
                  label={
                    wf.status === "PUBLISHED"
                      ? isFr
                        ? "Publié"
                        : "Published"
                      : isFr
                        ? "Brouillon"
                        : "Draft"
                  }
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

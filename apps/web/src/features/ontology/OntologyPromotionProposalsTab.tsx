import { OrciaIcon, StatusBadge } from "@orcia/ui";
import React, { useState } from "react";
import type { OntologyPromotionProposalDetailItem } from "../../components/ontologyApiBridge";
import type { OntologyGlossaryCopy } from "../../i18n/locales/ontology_glossary_labels";

export interface OntologyPromotionProposalsTabProps {
  readonly proposals: readonly OntologyPromotionProposalDetailItem[];
  readonly copy: OntologyGlossaryCopy;
  readonly busyProposalId: string | null;
  readonly onDecideProposal: (
    proposalId: string,
    decision: "APPROVE" | "REJECT",
    comment?: string,
  ) => void;
}

export function OntologyPromotionProposalsTab({
  proposals,
  copy,
  busyProposalId,
  onDecideProposal,
}: OntologyPromotionProposalsTabProps): React.ReactElement {
  const [commentsById, setCommentsById] = useState<Record<string, string>>({});

  return (
    <section
      data-testid="ontology-promotions-proposals-tab"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div>
        <strong style={{ fontSize: "15px" }}>{copy.proposalsTitle}</strong>
        <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {copy.proposalsSubtitle}
        </p>
      </div>

      {proposals.length === 0 ? (
        <div
          data-testid="ontology-promotions-empty-state"
          style={{
            padding: "20px",
            borderRadius: "var(--radius-sm)",
            border: "1px dashed var(--color-border)",
            textAlign: "center",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
          }}
        >
          {copy.proposalsEmptyState}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {proposals.map((p) => {
            const isPending = p.status === "PENDING_REVIEW";
            const isBusy = busyProposalId === p.id;
            const statusLabel =
              p.status === "APPROVED"
                ? copy.statusApproved
                : p.status === "REJECTED"
                  ? copy.statusRejected
                  : copy.statusPending;
            const statusTone =
              p.status === "APPROVED" ? "emerald" : p.status === "REJECTED" ? "crimson" : "amber";
            return (
              <article
                key={p.id}
                data-testid={`promotion-proposal-card-${p.id}`}
                style={{
                  padding: "12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-bg-elevated)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <strong style={{ fontSize: "14px" }}>{p.canonical_term}</strong>
                    <StatusBadge label={statusLabel} tone={statusTone} />
                    <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                      {copy.levelLabels[p.source_level] ?? p.source_level}{" "}
                      <OrciaIcon name="arrowRight" />{" "}
                      {copy.levelLabels[p.target_level] ?? p.target_level}
                    </span>
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                    {`${copy.proposalsMetaProposedBy} ${p.proposed_by_user_id} · ${copy.proposalsMetaTarget} ${p.target_scope_id}`}
                  </span>
                </div>

                {p.definition_text && (
                  <p style={{ margin: 0, fontSize: "12px", color: "var(--color-text-primary)" }}>
                    {p.definition_text}
                  </p>
                )}

                {p.collision_detected && (
                  <div
                    data-testid={`promotion-collision-alert-${p.id}`}
                    style={{
                      padding: "8px 10px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-status-warning)",
                      backgroundColor: "var(--color-surface-card)",
                      fontSize: "12px",
                    }}
                  >
                    <strong>
                      <OrciaIcon name="warning" /> {copy.collisionWarningPrefix}
                    </strong>{" "}
                    {p.colliding_definition && (
                      <span>{`${copy.existingDefinitionLabel} ${p.colliding_definition}`}</span>
                    )}
                  </div>
                )}

                {isPending && p.can_decide && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
                    <input
                      type="text"
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      data-bwignore="true"
                      data-form-type="other"
                      data-testid={`promotion-comment-input-${p.id}`}
                      value={commentsById[p.id] ?? ""}
                      onChange={(e) =>
                        setCommentsById((prev) => ({ ...prev, [p.id]: e.target.value }))
                      }
                      placeholder={copy.proposalsCommentPlaceholder}
                      style={{
                        flex: 1,
                        minWidth: "200px",
                        padding: "6px 8px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                        backgroundColor: "var(--color-surface-card)",
                        color: "var(--color-foreground)",
                      }}
                    />
                    <button
                      type="button"
                      data-testid={`approve-promotion-btn-${p.id}`}
                      disabled={isBusy}
                      onClick={() => onDecideProposal(p.id, "APPROVE", commentsById[p.id])}
                      className="orcia-ds-btn orcia-ds-btn-primary"
                    >
                      <OrciaIcon name="check" /> <span>{copy.approveButtonLabel}</span>
                    </button>
                    <button
                      type="button"
                      data-testid={`reject-promotion-btn-${p.id}`}
                      disabled={isBusy}
                      onClick={() => onDecideProposal(p.id, "REJECT", commentsById[p.id])}
                      className="orcia-ds-btn"
                    >
                      <OrciaIcon name="cross" /> <span>{copy.rejectButtonLabel}</span>
                    </button>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

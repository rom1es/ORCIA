import React, { useState } from "react";

export interface UiEvidenceSourceItem {
  readonly tag: string;
  readonly index: number;
  readonly uri: string;
  readonly title: string;
  readonly authorityTier: "REFERENCE" | "ACTIVE";
  readonly freshness: "FRESH" | "STALE_WARNING";
  readonly snippet: string | null;
  readonly lineStart: number;
  readonly lineEnd: number;
  readonly restrictedAccess: boolean;
  readonly displayPill: string;
}

export interface UiEvidenceGlossaryItem {
  readonly tag: string;
  readonly label: string;
  readonly ontologyLevel:
    | "N1_DIRECTIVE"
    | "N2_NORME"
    | "N3_MECANISME"
    | "L4_GLOSSARY";
  readonly definition: string;
}

export interface UiEvidenceToolItem {
  readonly tag: string;
  readonly toolName: string;
  readonly connectorUri: string;
  readonly summary: string;
}

export interface AssistantCitationPillsAndArtifactCardLabels {
  readonly freshnessFreshBadge: string;
  readonly freshnessStaleBadge: string;
  readonly restrictedSourcePillSuffix: string;
  readonly requestAccessCta: string;
  readonly unverifiedCitationBadge: string;
  readonly artifactCardTitlePrefix: string;
  readonly copyArtifactCta: string;
  readonly exportArtifactCta: string;
  readonly saveDraftCta: string;
  readonly continueInProcessCta: string;
  readonly v5LockNoticeText: string;
}

export interface AssistantCitationPillsAndArtifactCardProps {
  readonly sanitizedResponseText: string;
  readonly strippedPhantomTags?: readonly string[];
  readonly sources: readonly UiEvidenceSourceItem[];
  readonly glossaryItems?: readonly UiEvidenceGlossaryItem[];
  readonly toolOutputs?: readonly UiEvidenceToolItem[];
  readonly footerSummaryLine: string;
  readonly artifactTitle?: string;
  readonly artifactContent?: string;
  readonly labels: AssistantCitationPillsAndArtifactCardLabels;
  readonly onInspectSource?: (source: UiEvidenceSourceItem) => void;
  readonly onRequestRestrictedAccess?: (uri: string) => void;
  readonly onSaveDraft?: (title: string, content: string) => void;
  readonly onContinueInProcess?: (
    title: string,
    content: string,
    citedTags: readonly string[],
  ) => void;
}

/**
 * Story 10.3 — Interactive `[S1]` / `[G1]` / `[O1]` Citation Pills, Dynamic Per-Reader
 * `READ_SOURCE` Filtering (`[S1 · 🔒 Source restreinte — Demander l'accès]`), `< 5 ms`
 * Anti-Phantom Verifier & Structured Artifact Card with Verrou V5 (`AD-15`).
 */
export function AssistantCitationPillsAndArtifactCard({
  sanitizedResponseText,
  strippedPhantomTags = [],
  sources,
  glossaryItems = [],
  toolOutputs = [],
  footerSummaryLine,
  artifactTitle,
  artifactContent,
  labels,
  onInspectSource,
  onRequestRestrictedAccess,
  onSaveDraft,
  onContinueInProcess,
}: AssistantCitationPillsAndArtifactCardProps): React.JSX.Element {
  const [hoveredTag, setHoveredTag] = useState<string | null>(null);
  const [inspectedSource, setInspectedSource] =
    useState<UiEvidenceSourceItem | null>(null);
  const [footerExpanded, setFooterExpanded] = useState<boolean>(false);

  const hoveredSource = sources.find((s) => s.tag === hoveredTag) ?? null;

  return (
    <section
      data-testid="assistant-citation-pills-and-artifact-card"
      className="rounded-lg border border-border-subtle bg-surface-elevated p-4 text-text-primary space-y-3"
    >
      {/* Sanitized response text */}
      <div
        data-testid="assistant-sanitized-response-text"
        className="text-xs leading-relaxed"
      >
        {sanitizedResponseText}
      </div>

      {/* Stripped phantom citation alert if any */}
      {strippedPhantomTags.length > 0 && (
        <div
          data-testid="assistant-phantom-citations-alert"
          role="status"
          className="rounded border border-status-warning/40 bg-status-warning/10 px-2.5 py-1 text-[11px] font-medium text-status-warning"
        >
          {labels.unverifiedCitationBadge} ({strippedPhantomTags.join(", ")})
        </div>
      )}

      {/* Interactive [S1..Sn], [G1..Gn], [O1..On] pills */}
      <div
        data-testid="assistant-citation-pills-bar"
        className="flex flex-wrap items-center gap-1.5"
      >
        {sources.map((src) =>
          src.restrictedAccess ? (
            <span
              key={src.tag}
              data-testid={`citation-pill-restricted-${src.tag}`}
              className="inline-flex items-center gap-1.5 rounded border border-status-warning/40 bg-status-warning/10 px-2 py-0.5 font-mono text-[11px] text-status-warning"
            >
              <span>{src.displayPill}</span>
              <button
                type="button"
                data-testid={`citation-request-access-btn-${src.tag}`}
                onClick={() => onRequestRestrictedAccess?.(src.uri)}
                className="underline font-sans font-semibold"
              >
                {labels.requestAccessCta}
              </button>
            </span>
          ) : (
            <button
              key={src.tag}
              type="button"
              data-testid={`citation-pill-${src.tag}`}
              onMouseEnter={() => setHoveredTag(src.tag)}
              onMouseLeave={() => setHoveredTag(null)}
              onClick={() => {
                setInspectedSource(src);
                onInspectSource?.(src);
              }}
              className="inline-flex items-center gap-1 rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 font-mono text-[11px] font-medium text-text-primary hover:border-action-primary"
            >
              <span>[{src.tag}]</span>
              <span className="text-[10px] text-text-secondary">
                {src.authorityTier}
              </span>
              <span>
                {src.freshness === "FRESH"
                  ? labels.freshnessFreshBadge
                  : labels.freshnessStaleBadge}
              </span>
            </button>
          ),
        )}

        {glossaryItems.map((g) => (
          <span
            key={g.tag}
            data-testid={`citation-pill-${g.tag}`}
            className="inline-flex items-center gap-1 rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 font-mono text-[11px]"
          >
            [{g.tag}] {g.label} ({g.ontologyLevel})
          </span>
        ))}

        {toolOutputs.map((t) => (
          <span
            key={t.tag}
            data-testid={`citation-pill-${t.tag}`}
            className="inline-flex items-center gap-1 rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 font-mono text-[11px]"
          >
            [{t.tag}] {t.toolName}
          </span>
        ))}
      </div>

      {/* Hover preview popover for non-restricted source */}
      {hoveredSource && !hoveredSource.restrictedAccess && (
        <div
          data-testid={`citation-hover-preview-${hoveredSource.tag}`}
          className="rounded border border-border-subtle bg-surface-primary p-2.5 text-xs space-y-1 shadow-sm"
        >
          <div className="flex items-center justify-between gap-2 font-semibold">
            <span>{hoveredSource.title}</span>
            <span className="font-mono text-[11px] text-text-secondary">
              {hoveredSource.uri} (L{hoveredSource.lineStart}–L
              {hoveredSource.lineEnd})
            </span>
          </div>
          <p className="text-text-secondary italic">{hoveredSource.snippet}</p>
        </div>
      )}

      {/* Side inspection panel opened on click */}
      {inspectedSource && !inspectedSource.restrictedAccess && (
        <aside
          data-testid="citation-side-inspector-panel"
          className="rounded border border-action-primary/40 bg-surface-primary p-3 text-xs space-y-1"
        >
          <div className="font-semibold">
            [{inspectedSource.tag}] {inspectedSource.title} — Lignes{" "}
            {inspectedSource.lineStart}..{inspectedSource.lineEnd}
          </div>
          <div className="font-mono text-[11px] text-text-secondary">
            {inspectedSource.uri}
          </div>
          <p className="text-text-primary">{inspectedSource.snippet}</p>
        </aside>
      )}

      {/* Structured Artifact Card with Verrou V5 (AD-15) */}
      {artifactTitle && artifactContent && (
        <div
          data-testid="assistant-structured-artifact-card"
          className="rounded-lg border border-border-subtle bg-surface-primary p-3 space-y-2.5"
        >
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-xs font-semibold">
              {labels.artifactCardTitlePrefix} : {artifactTitle}{" "}
              <span className="rounded bg-surface-secondary px-1.5 py-0.5 font-mono text-[10px]">
                @draft
              </span>
            </h4>
          </div>
          <pre className="overflow-x-auto rounded bg-surface-secondary p-2 font-mono text-[11px]">
            {artifactContent}
          </pre>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="artifact-card-save-draft-btn"
              onClick={() => onSaveDraft?.(artifactTitle, artifactContent)}
              className="rounded border border-border-subtle bg-surface-secondary px-2.5 py-1 text-xs font-medium"
            >
              {labels.saveDraftCta}
            </button>
            <button
              type="button"
              data-testid="artifact-card-continue-process-btn"
              onClick={() =>
                onContinueInProcess?.(
                  artifactTitle,
                  artifactContent,
                  sources.map((s) => s.tag),
                )
              }
              className="rounded bg-action-primary px-3 py-1 text-xs font-semibold text-white"
            >
              {labels.continueInProcessCta}
            </button>
          </div>
          <p
            data-testid="artifact-card-v5-lock-notice"
            className="text-[11px] text-text-secondary"
          >
            {labels.v5LockNoticeText}
          </p>
        </div>
      )}

      {/* Collapsible 1-line evidence footer */}
      <footer className="border-t border-border-subtle pt-2">
        <button
          type="button"
          data-testid="assistant-evidence-footer-toggle"
          aria-expanded={footerExpanded}
          onClick={() => setFooterExpanded((prev) => !prev)}
          className="text-left text-[11px] font-medium text-text-secondary hover:text-text-primary"
        >
          {footerSummaryLine}
        </button>
      </footer>
    </section>
  );
}

import type { UiAssistantRagCitationItem, UiEvidenceSourceItem } from "@orcia/ui";

export interface BuiltCitationCardPreview {
  readonly sanitizedResponseText: string;
  readonly footerSummaryLine: string;
  readonly sources: readonly UiEvidenceSourceItem[];
  readonly artifactTitle?: string;
  readonly artifactContent?: string;
  readonly onInspectSource: (source: UiEvidenceSourceItem) => void;
}

export function buildAssistantCitationCardPreview(params: {
  readonly isGenerating: boolean;
  readonly replyText: string;
  readonly activeSources: readonly UiAssistantRagCitationItem[];
  readonly activeFolderTitle: string | null;
  readonly isFr: boolean;
  readonly onInspectCitationUri: (uri: string, title: string) => void;
}): BuiltCitationCardPreview | null {
  const {
    isGenerating,
    replyText,
    activeSources,
    activeFolderTitle,
    isFr,
    onInspectCitationUri,
  } = params;
  const trimmed = replyText.trim();
  if (isGenerating || trimmed.length === 0) {
    return null;
  }

  const hasStructuredArtifactOrCitation =
    /\[[SGO]\d+\]/i.test(trimmed) || /^#{1,3}\s/m.test(trimmed) || trimmed.includes("\n```");
  const hasDistinctArtifactOrSources =
    activeSources.length > 0 || activeFolderTitle !== null || hasStructuredArtifactOrCitation;
  if (!hasDistinctArtifactOrSources) {
    return null;
  }

  const mappedSources: readonly UiEvidenceSourceItem[] = activeSources.map(
    (src, idx) => ({
      tag: `S${idx + 1}`,
      index: idx + 1,
      uri: src.uri,
      title: src.title,
      authorityTier: "REFERENCE",
      freshness: "FRESH",
      snippet: src.snippet ?? src.title,
      lineStart: 1,
      lineEnd: 20,
      restrictedAccess: false,
      displayPill: `[S${idx + 1}] ${src.title}`,
    }),
  );

  const summaryLine =
    mappedSources.length > 0
      ? isFr
        ? `${mappedSources.length} source(s) vérifiée(s) · Gouvernance de publication active`
        : `${mappedSources.length} verified source(s) · Publication review active`
      : isFr
        ? `Dossier « ${activeFolderTitle ?? (isFr ? "Synthèse" : "Draft")} » · Gouvernance de publication active`
        : `Folder "${activeFolderTitle ?? "Draft"}" · Publication review active`;

  const sanitizedPreview =
    activeFolderTitle !== null || hasStructuredArtifactOrCitation
      ? isFr
        ? "Sources et brouillon prêt pour révision ou transfert vers un processus."
        : "Verified citations and draft ready for review or process handoff."
      : trimmed;

  return {
    sanitizedResponseText: sanitizedPreview,
    sources: mappedSources,
    artifactTitle:
      activeFolderTitle ?? (isFr ? "Synthèse de réponse" : "Response Draft"),
    artifactContent: trimmed.slice(0, 800),
    footerSummaryLine: summaryLine,
    onInspectSource: (src: UiEvidenceSourceItem) =>
      onInspectCitationUri(src.uri, src.title),
  };
}

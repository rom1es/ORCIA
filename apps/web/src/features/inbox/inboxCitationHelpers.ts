import type {
  UiAssistantRagCitationItem,
  UiEvidenceGlossaryItem,
  UiEvidenceSourceItem,
  UiEvidenceToolItem,
} from "@orcia/ui";

export interface BuiltCitationCardPreview {
  readonly sanitizedResponseText: string;
  readonly strippedPhantomTags: readonly string[];
  readonly footerSummaryLine: string;
  readonly sources: readonly UiEvidenceSourceItem[];
  readonly glossaryItems: readonly UiEvidenceGlossaryItem[];
  readonly toolOutputs: readonly UiEvidenceToolItem[];
  readonly artifactTitle?: string;
  readonly artifactContent?: string;
  readonly onInspectSource: (source: UiEvidenceSourceItem) => void;
  readonly onRequestRestrictedAccess?: (uri: string) => void;
}

export interface ParsedServerCitationMap {
  readonly sources: readonly UiEvidenceSourceItem[];
  readonly glossaryItems: readonly UiEvidenceGlossaryItem[];
  readonly toolOutputs: readonly UiEvidenceToolItem[];
  readonly strippedPhantomTags: readonly string[];
  readonly footerSummaryLine: string;
  readonly sanitizedResponseText: string | null;
}

function asRecord(val: unknown): Record<string, unknown> | null {
  return typeof val === "object" && val !== null && !Array.isArray(val)
    ? (val as Record<string, unknown>)
    : null;
}

function mapSourceEntry(entry: unknown, idx: number): UiEvidenceSourceItem | null {
  const row = asRecord(entry);
  if (!row) return null;
  const tag = String(row.tag ?? `S${idx + 1}`);
  const title = String(row.title ?? row.label ?? row.uri ?? tag);
  const uri = String(row.uri ?? row.source_uri ?? "");
  const restricted = Boolean(row.restricted_access);
  const authorityTier: "REFERENCE" | "ACTIVE" =
    row.authority_tier === "ACTIVE" ? "ACTIVE" : "REFERENCE";
  const freshness: "FRESH" | "STALE_WARNING" =
    row.freshness === "STALE_WARNING" || row.stale_warning === true ? "STALE_WARNING" : "FRESH";
  const snippet = row.snippet === null || row.snippet === undefined ? null : String(row.snippet);
  const displayPill = String(row.display_pill ?? `[${tag}] ${title}`);
  return {
    tag,
    index: typeof row.index === "number" ? row.index : idx + 1,
    uri,
    title,
    authorityTier,
    freshness,
    snippet,
    lineStart: typeof row.line_start === "number" ? row.line_start : 1,
    lineEnd: typeof row.line_end === "number" ? row.line_end : 20,
    restrictedAccess: restricted,
    displayPill,
  };
}

function mapGlossaryEntry(entry: unknown): UiEvidenceGlossaryItem | null {
  const row = asRecord(entry);
  if (!row) return null;
  const rawLevel = String(row.ontology_level ?? "L4_GLOSSARY");
  const ontologyLevel =
    rawLevel === "N1_DIRECTIVE" ||
    rawLevel === "N2_NORME" ||
    rawLevel === "N3_MECANISME" ||
    rawLevel === "L4_GLOSSARY"
      ? rawLevel
      : "L4_GLOSSARY";
  return {
    tag: String(row.tag ?? "G1"),
    label: String(row.label ?? ""),
    ontologyLevel,
    definition: String(row.definition ?? ""),
  };
}

function mapToolEntry(entry: unknown): UiEvidenceToolItem | null {
  const row = asRecord(entry);
  if (!row) return null;
  return {
    tag: String(row.tag ?? "O1"),
    toolName: String(row.tool_name ?? ""),
    connectorUri: String(row.connector_uri ?? ""),
    summary: String(row.summary ?? ""),
  };
}

export function parseServerCitationMap(rawCitationMap: unknown): ParsedServerCitationMap {
  const root = asRecord(rawCitationMap);
  if (!root) {
    return {
      sources: [],
      glossaryItems: [],
      toolOutputs: [],
      strippedPhantomTags: [],
      footerSummaryLine: "",
      sanitizedResponseText: null,
    };
  }
  const nestedDict = asRecord(root.citation_map_dict);
  const rawSources = Array.isArray(root.sources)
    ? root.sources
    : Array.isArray(nestedDict?.sources)
      ? nestedDict.sources
      : [];
  const rawGlossary = Array.isArray(root.glossary_items)
    ? root.glossary_items
    : Array.isArray(nestedDict?.glossary_items)
      ? nestedDict.glossary_items
      : [];
  const rawTools = Array.isArray(root.tool_outputs)
    ? root.tool_outputs
    : Array.isArray(nestedDict?.tool_outputs)
      ? nestedDict.tool_outputs
      : [];
  const rawStripped = Array.isArray(root.stripped_phantom_tags)
    ? root.stripped_phantom_tags
    : Array.isArray(nestedDict?.stripped_phantom_tags)
      ? nestedDict.stripped_phantom_tags
      : [];
  const sources = rawSources.map(mapSourceEntry).filter((x): x is UiEvidenceSourceItem => x !== null);
  const glossaryItems = rawGlossary.map(mapGlossaryEntry).filter((x): x is UiEvidenceGlossaryItem => x !== null);
  const toolOutputs = rawTools.map(mapToolEntry).filter((x): x is UiEvidenceToolItem => x !== null);
  const strippedPhantomTags = rawStripped.map((tag) => String(tag)).filter(Boolean);
  const footerSummaryLine = String(root.footer_summary_line ?? nestedDict?.footer_summary_line ?? "");
  const sanitizedResponseText =
    typeof root.sanitized_response_text === "string" && root.sanitized_response_text.trim().length > 0
      ? root.sanitized_response_text
      : null;

  return {
    sources,
    glossaryItems,
    toolOutputs,
    strippedPhantomTags,
    footerSummaryLine,
    sanitizedResponseText,
  };
}

export function citationMapToRagItems(rawCitationMap: unknown): readonly UiAssistantRagCitationItem[] {
  const parsed = parseServerCitationMap(rawCitationMap);
  return parsed.sources.map((src) => ({
    title: src.title,
    uri: src.uri,
    ...(src.snippet ? { snippet: src.snippet } : {}),
  }));
}

export function buildAssistantCitationCardPreview(params: {
  readonly isGenerating: boolean;
  readonly replyText: string;
  readonly citationMap?: unknown;
  readonly activeFolderTitle: string | null;
  readonly isFr: boolean;
  readonly onInspectCitationUri: (uri: string, title: string) => void;
  readonly onRequestRestrictedAccess?: (uri: string) => void;
}): BuiltCitationCardPreview | null {
  const {
    isGenerating,
    replyText,
    citationMap,
    activeFolderTitle,
    isFr,
    onInspectCitationUri,
    onRequestRestrictedAccess,
  } = params;
  const trimmed = replyText.trim();
  if (isGenerating || trimmed.length === 0) {
    return null;
  }

  const parsed = parseServerCitationMap(citationMap);
  const hasServerEvidence =
    parsed.sources.length > 0 ||
    parsed.glossaryItems.length > 0 ||
    parsed.toolOutputs.length > 0 ||
    parsed.strippedPhantomTags.length > 0;

  if (!hasServerEvidence && activeFolderTitle === null) {
    return null;
  }

  const summaryLine =
    parsed.footerSummaryLine ||
    (parsed.sources.length > 0
      ? isFr
        ? `${parsed.sources.length} source(s) vérifiée(s) par le serveur`
        : `${parsed.sources.length} server-verified source(s)`
      : isFr
        ? `Dossier « ${activeFolderTitle ?? "Synthèse"} »`
        : `Folder "${activeFolderTitle ?? "Draft"}"`);

  return {
    sanitizedResponseText: parsed.sanitizedResponseText ?? trimmed,
    strippedPhantomTags: parsed.strippedPhantomTags,
    sources: parsed.sources,
    glossaryItems: parsed.glossaryItems,
    toolOutputs: parsed.toolOutputs,
    artifactTitle: activeFolderTitle ?? (isFr ? "Synthèse de réponse" : "Response Draft"),
    artifactContent: (parsed.sanitizedResponseText ?? trimmed).slice(0, 800),
    footerSummaryLine: summaryLine,
    onInspectSource: (src: UiEvidenceSourceItem) => onInspectCitationUri(src.uri, src.title),
    ...(onRequestRestrictedAccess ? { onRequestRestrictedAccess } : {}),
  };
}

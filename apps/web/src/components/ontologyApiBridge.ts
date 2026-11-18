import {
  createOrciaApiClient,
  type OntologyConceptWithPermissionsItem,
  type OntologyPromotionCreateRequest,
  type OntologyPromotionDecideRequest,
  type OntologyPromotionDecideResponse,
  type OntologyPromotionProposalDetailItem,
  type WritableScopeOptionItem,
} from "@orcia/api-client";
import type { UiOntologyConceptView, UiOntologyLevel } from "@orcia/ui";
import { resolveWebApiBaseUrl } from "../stores/authSessionStore";

export type {
  OntologyConceptWithPermissionsItem,
  OntologyPromotionProposalDetailItem,
  WritableScopeOptionItem,
};

export function mapConceptDtoToView(
  dto: OntologyConceptWithPermissionsItem,
): UiOntologyConceptView {
  return {
    conceptKey: dto.concept_key,
    canonicalTerm: dto.canonical_term,
    level: dto.level as UiOntologyLevel,
    scopeId: dto.scope_id,
    definitionText: dto.definition_text,
    immutable: dto.level === "1_ENTERPRISE",
    synonyms: dto.synonyms ?? [],
    profileTranslations: dto.profile_translations ?? {},
    impactedTemplates: [],
    impactedWorkflows: [],
    impactedRuns: [],
    canEdit: dto.can_edit,
    canProposePromotion: dto.can_propose_promotion,
    nextPromotionLevel: (dto.next_promotion_level ?? null) as UiOntologyLevel | null,
    nextPromotionScopeId: dto.next_promotion_scope_id ?? null,
  };
}

export function createGlossaryClient(locale: "fr" | "en") {
  return createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl(), locale });
}

export async function fetchOntologyConceptsFromApi(locale: "fr" | "en"): Promise<{
  concepts: UiOntologyConceptView[];
  writableLevels: UiOntologyLevel[];
  writableScopes: WritableScopeOptionItem[];
}> {
  const client = createGlossaryClient(locale);
  const res = await client.listOntologyConcepts(false);
  return {
    concepts: res.concepts.map(mapConceptDtoToView),
    writableLevels: res.writable_levels as UiOntologyLevel[],
    writableScopes: res.writable_scopes,
  };
}

export async function upsertOntologyConceptToApi(
  locale: "fr" | "en",
  payload: {
    conceptKey: string;
    canonicalTerm: string;
    level: UiOntologyLevel;
    scopeId: string;
    definitionText: string;
    synonyms?: string[];
    profileTranslations?: Record<string, string>;
  },
) {
  const client = createGlossaryClient(locale);
  return client.upsertOntologyConcept({
    concept_key: payload.conceptKey,
    canonical_term: payload.canonicalTerm,
    level: payload.level,
    scope_id: payload.scopeId,
    definition_text: payload.definitionText,
    synonyms: payload.synonyms ?? [],
    profile_translations: payload.profileTranslations ?? {},
  });
}

export async function fetchOntologyPromotionsFromApi(locale: "fr" | "en"): Promise<{
  proposals: OntologyPromotionProposalDetailItem[];
  pendingCount: number;
}> {
  const client = createGlossaryClient(locale);
  const res = await client.listOntologyPromotions(undefined, false);
  return { proposals: res.proposals, pendingCount: res.pending_count };
}

export async function proposeOntologyPromotionToApi(
  locale: "fr" | "en",
  payload: OntologyPromotionCreateRequest,
): Promise<OntologyPromotionProposalDetailItem> {
  const client = createGlossaryClient(locale);
  return client.createOntologyPromotion(payload, false);
}

export async function decideOntologyPromotionToApi(
  locale: "fr" | "en",
  proposalId: string,
  payload: OntologyPromotionDecideRequest,
): Promise<OntologyPromotionDecideResponse> {
  const client = createGlossaryClient(locale);
  return client.decideOntologyPromotion(proposalId, payload, false);
}

export function slugifyScopedConceptKey(
  term: string,
  level: UiOntologyLevel,
  scopeId: string,
): string {
  const normTerm =
    term
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || `concept-${Date.now()}`;
  const normLevel = level
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const normScope =
    scopeId
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "global";
  const prefix = `${normLevel}-${normScope}-`;
  const maxTermLen = Math.max(8, 120 - prefix.length);
  return `${prefix}${normTerm.slice(0, maxTermLen)}`.slice(0, 120).replace(/-+$/, "");
}

import type {
  OntologyConceptsListResponse,
  OntologyPromotionCreateRequest,
  OntologyPromotionDecideRequest,
  OntologyPromotionDecideResponse,
  OntologyPromotionProposalDetailItem,
  OntologyPromotionsListResponse,
} from "../generated/ontology_promotions";
import type { createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type {
  OntologyConceptWithPermissionsItem,
  OntologyConceptsListResponse,
  OntologyPromotionCreateRequest,
  OntologyPromotionDecideRequest,
  OntologyPromotionDecideResponse,
  OntologyPromotionProposalDetailItem,
  OntologyPromotionsListResponse,
  WritableScopeOptionItem,
} from "../generated/ontology_promotions";

export function createOntologyPromotionsDomainClient(requestJson: RequestJsonFn) {
  return {
    listOntologyConcepts(fixture = false): Promise<OntologyConceptsListResponse> {
      return requestJson<OntologyConceptsListResponse>(
        `/api/v1/ontology-rag/ontology/concepts?fixture=${fixture ? "true" : "false"}`,
      );
    },
    listOntologyPromotions(
      status?: string,
      fixture = false,
    ): Promise<OntologyPromotionsListResponse> {
      const qs = new URLSearchParams({ fixture: fixture ? "true" : "false" });
      if (status) {
        qs.set("status", status);
      }
      return requestJson<OntologyPromotionsListResponse>(
        `/api/v1/ontology-rag/ontology/promotions?${qs.toString()}`,
      );
    },
    createOntologyPromotion(
      payload: OntologyPromotionCreateRequest,
      fixture = false,
    ): Promise<OntologyPromotionProposalDetailItem> {
      return requestJson<OntologyPromotionProposalDetailItem>(
        `/api/v1/ontology-rag/ontology/promotions?fixture=${fixture ? "true" : "false"}`,
        "POST",
        payload,
      );
    },
    decideOntologyPromotion(
      proposalId: string,
      payload: OntologyPromotionDecideRequest,
      fixture = false,
    ): Promise<OntologyPromotionDecideResponse> {
      return requestJson<OntologyPromotionDecideResponse>(
        `/api/v1/ontology-rag/ontology/promotions/${encodeURIComponent(proposalId)}/decide?fixture=${fixture ? "true" : "false"}`,
        "POST",
        payload,
      );
    },
  };
}

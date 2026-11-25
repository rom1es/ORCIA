import {
  createOrciaApiClient,
  type ExceptionWaiverResponseItem,
  type GeneratedStarlarkMechanismResponse,
  type OntologyPromotionProposalDetailItem,
  type WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import type {
  ControlCenterWorkspaceGovItem,
  ExceptionWaiverItem,
  UiCompiledStarlarkMechanism,
  UiGlossaryCandidateItem,
} from "@orcia/ui";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import type { FeatureWorkspacesDictionary } from "../../i18n/locales/feature_workspaces_labels";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import type { WorkspaceFeedbackInput } from "./workspaceFeedbackTypes";

function mapWaiverItem(w: ExceptionWaiverResponseItem): ExceptionWaiverItem {
  return {
    waiverId: String(w.waiver_id),
    sourceUri: w.source_uri,
    conflictRuleId: w.conflict_rule_id,
    normLevel: w.norm_level,
    hasInviolableEnterpriseDirective:
      w.norm_level === "1_ENTERPRISE" ||
      w.dna_chain.some((n) => n.level === "1_ENTERPRISE" && n.inviolable),
    status: w.status,
    reason: w.reason,
  };
}

function mapMechanismItem(
  res: GeneratedStarlarkMechanismResponse,
  dnaCopy: FeatureWorkspacesDictionary["dnaAndWaivers"],
): UiCompiledStarlarkMechanism {
  return {
    mechanismId: String(res.mechanism_id),
    ruleId: res.rule_id,
    scriptName: res.script_name,
    starlarkCode: res.starlark_code,
    sha256: res.sha256,
    explanationFr: formatI18nTemplate(dnaCopy.compiledExplanationTemplate, {
      ruleId: res.rule_id,
    }),
    verifiedBadgeFr: dnaCopy.compiledVerifiedBadge,
    causalBreadcrumb: formatI18nTemplate(dnaCopy.compiledCausalBreadcrumbTemplate, {
      ruleId: res.rule_id,
    }),
    selfCorrected: Boolean(res.self_corrected),
    signedAndActive: Boolean(res.signed_and_active),
  };
}

function mapProposalToGlossaryCandidate(
  proposal: OntologyPromotionProposalDetailItem,
): UiGlossaryCandidateItem {
  const hasConflict = Boolean(proposal.collision_detected);
  return {
    candidateId: String(proposal.id),
    canonicalTerm: proposal.canonical_term,
    definitionFr: proposal.definition_text || proposal.canonical_term,
    confidenceScore: hasConflict ? 0.72 : 0.94,
    ontologyConflictWarning: hasConflict
      ? proposal.colliding_definition || proposal.concept_key
      : null,
    preCheckedForInFlowPromotion: !hasConflict,
  };
}

export function useWorkspaceDnaAndWaivers(params: {
  readonly isFr: boolean;
  readonly targetWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly onFeedback: (feedback: WorkspaceFeedbackInput) => void;
  readonly onGlossaryMutated?: () => void;
}) {
  const { isFr, targetWorkspace, onFeedback, onGlossaryMutated } = params;
  const locale = resolveLocaleForFlag(isFr);
  const dnaCopy = resolveDictionaryForFlag(isFr, locale).featureWorkspaces.dnaAndWaivers;

  const onFeedbackRef = useRef(onFeedback);
  onFeedbackRef.current = onFeedback;
  const onGlossaryMutatedRef = useRef(onGlossaryMutated);
  onGlossaryMutatedRef.current = onGlossaryMutated;

  const [activeWaivers, setActiveWaivers] = useState<ExceptionWaiverItem[]>([]);
  const [compiledMechanism, setCompiledMechanism] =
    useState<UiCompiledStarlarkMechanism | null>(null);
  const [scopedDatasources, setScopedDatasources] = useState<
    readonly WorkspaceDatasourceItemResponse[]
  >([]);
  const [glossaryCandidates, setGlossaryCandidates] = useState<UiGlossaryCandidateItem[]>([]);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const targetWsId = targetWorkspace?.workspaceId ?? "";

  const reloadWaiversAndMechanisms = useCallback(async () => {
    if (!targetWsId) {
      setActiveWaivers([]);
      setCompiledMechanism(null);
      setScopedDatasources([]);
      setGlossaryCandidates([]);
      return;
    }
    const client = createOrciaApiClient({ baseUrl: "", locale });
    const [waiversRows, mechanismRows, dsRes, promoRes] = await Promise.all([
      client.listWorkspaceExceptionWaivers(targetWsId, true),
      client.listDnaMechanisms(targetWsId),
      client.listWorkspaceDatasources(targetWsId),
      client.listOntologyPromotions("PENDING_REVIEW", false),
    ]);
    setActiveWaivers(waiversRows.map(mapWaiverItem));
    setCompiledMechanism(mechanismRows[0] ? mapMechanismItem(mechanismRows[0], dnaCopy) : null);
    setScopedDatasources(dsRes.items ?? []);
    const scopedPending = (promoRes.proposals ?? []).filter(
      (p) =>
        p.status === "PENDING_REVIEW" &&
        (p.source_scope_id === targetWsId || p.target_scope_id === targetWsId),
    );
    setGlossaryCandidates(scopedPending.map(mapProposalToGlossaryCandidate));
  }, [targetWsId, locale, dnaCopy]);

  useEffect(() => {
    if (!targetWsId) {
      setActiveWaivers([]);
      setCompiledMechanism(null);
      setScopedDatasources([]);
      setGlossaryCandidates([]);
      return;
    }
    setScopedDatasources([]);
    setGlossaryCandidates([]);
    let cancelled = false;
    void reloadWaiversAndMechanisms().catch((err: unknown) => {
      if (cancelled) return;
      onFeedbackRef.current({
        tone: "crimson",
        message: formatRfc9457ErrorToBanner(err, locale, dnaCopy.governanceErrorContext).fullText,
      });
    });
    return () => {
      cancelled = true;
    };
  }, [targetWsId, locale, dnaCopy.governanceErrorContext, reloadWaiversAndMechanisms]);

  const handleRegisterWaiver = async (sourceUri: string, conflictRuleId: string) => {
    if (!targetWsId || submitting) return;
    setSubmitting(true);
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const saved = await client.registerWorkspaceExceptionWaiver(targetWsId, {
        source_uri: sourceUri,
        source_sha256: "sha256:workspace-source-baseline-0001",
        conflict_rule_id: conflictRuleId,
        norm_level: "3_WORKSPACE",
        dna_chain: [],
        reason: dnaCopy.defaultWaiverReason,
        ttl_days: 30,
      });
      const reloaded = await client.listWorkspaceExceptionWaivers(targetWsId, true);
      setActiveWaivers(
        reloaded.length > 0 ? reloaded.map(mapWaiverItem) : [mapWaiverItem(saved)],
      );
      onFeedbackRef.current(
        formatI18nTemplate(dnaCopy.waiverRegisteredTemplate, { ruleId: conflictRuleId }),
      );
    } catch (err: unknown) {
      onFeedbackRef.current({
        tone: "crimson",
        message: formatRfc9457ErrorToBanner(err, locale, dnaCopy.waiverErrorContext).fullText,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCompileFromNorm = async (ruleId: string) => {
    if (!targetWsId || submitting) return;
    setSubmitting(true);
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const res = await client.compileDnaStarlark(targetWsId, {
        rule_id: ruleId,
        directive_title: dnaCopy.compileDirectiveTitle,
        norm_title: formatI18nTemplate(dnaCopy.compileNormPrefix, { ruleId }),
        natural_language_rule_fr: dnaCopy.compileRuleText,
        required_field: "reference_code",
      });
      const persisted = await client.listDnaMechanisms(targetWsId);
      setCompiledMechanism(
        persisted[0] ? mapMechanismItem(persisted[0], dnaCopy) : mapMechanismItem(res, dnaCopy),
      );
      onFeedbackRef.current(formatI18nTemplate(dnaCopy.compileSuccessTemplate, { ruleId }));
    } catch (err: unknown) {
      onFeedbackRef.current({
        tone: "crimson",
        message: formatRfc9457ErrorToBanner(err, locale, dnaCopy.compileErrorContext).fullText,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSignAndActivate = async (mechanismId: string) => {
    if (!targetWsId || submitting) return;
    setSubmitting(true);
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const activated = await client.activateDnaMechanism(targetWsId, mechanismId);
      const persisted = await client.listDnaMechanisms(targetWsId);
      setCompiledMechanism(
        persisted[0]
          ? mapMechanismItem(persisted[0], dnaCopy)
          : mapMechanismItem(activated, dnaCopy),
      );
      onFeedbackRef.current(dnaCopy.activateSuccessBanner);
    } catch (err: unknown) {
      onFeedbackRef.current({
        tone: "crimson",
        message: formatRfc9457ErrorToBanner(err, locale, dnaCopy.activateErrorContext).fullText,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handlePromoteInFlow = async (candidateIds: readonly string[]) => {
    if (!targetWsId || submitting || candidateIds.length === 0) return;
    setSubmitting(true);
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      for (const candidateId of candidateIds) {
        await client.decideOntologyPromotion(
          candidateId,
          { decision: "APPROVE", review_comment: dnaCopy.promoteReviewComment },
          false,
        );
      }
      await reloadWaiversAndMechanisms();
      onGlossaryMutatedRef.current?.();
      onFeedbackRef.current(
        formatI18nTemplate(dnaCopy.candidatesApprovedTemplate, { count: candidateIds.length }),
      );
    } catch (err: unknown) {
      onFeedbackRef.current({
        tone: "crimson",
        message: formatRfc9457ErrorToBanner(err, locale, dnaCopy.governanceErrorContext).fullText,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleRejectCandidate = async (candidateId: string) => {
    if (!targetWsId || submitting) return;
    setSubmitting(true);
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      await client.decideOntologyPromotion(
        candidateId,
        { decision: "REJECT", review_comment: dnaCopy.rejectReviewComment },
        false,
      );
      await reloadWaiversAndMechanisms();
      onGlossaryMutatedRef.current?.();
      onFeedbackRef.current(dnaCopy.candidateRejectedBanner);
    } catch (err: unknown) {
      onFeedbackRef.current({
        tone: "crimson",
        message: formatRfc9457ErrorToBanner(err, locale, dnaCopy.governanceErrorContext).fullText,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return {
    activeWaivers,
    compiledMechanism,
    scopedDatasources,
    setScopedDatasources,
    glossaryCandidates,
    submitting,
    reloadGovernanceState: reloadWaiversAndMechanisms,
    handleRegisterWaiver,
    handleCompileFromNorm,
    handleSignAndActivate,
    handlePromoteInFlow,
    handleRejectCandidate,
  };
}

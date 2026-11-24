import {
  createOrciaApiClient,
  type ExceptionWaiverResponseItem,
  type GeneratedStarlarkMechanismResponse,
  type WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import type {
  ControlCenterWorkspaceGovItem,
  ExceptionWaiverItem,
  UiCompiledStarlarkMechanism,
  UiGlossaryCandidateItem,
} from "@orcia/ui";
import { useCallback, useEffect, useState } from "react";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";

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

function mapMechanismItem(res: GeneratedStarlarkMechanismResponse): UiCompiledStarlarkMechanism {
  return {
    mechanismId: String(res.mechanism_id),
    ruleId: res.rule_id,
    scriptName: res.script_name,
    starlarkCode: res.starlark_code,
    sha256: res.sha256,
    explanationFr: res.explanation_fr,
    verifiedBadgeFr: res.verified_badge_fr,
    causalBreadcrumb: res.causal_breadcrumb,
    selfCorrected: Boolean(res.self_corrected),
    signedAndActive: Boolean(res.signed_and_active),
  };
}

export function useWorkspaceDnaAndWaivers(params: {
  readonly isFr: boolean;
  readonly targetWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly onFeedback: (message: string | null) => void;
}) {
  const { isFr, targetWorkspace, onFeedback } = params;
  const locale = resolveLocaleForFlag(isFr);
  const dnaCopy = resolveDictionaryForFlag(isFr, locale).featureWorkspaces.dnaAndWaivers;

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
      return;
    }
    const client = createOrciaApiClient({ baseUrl: "", locale });
    const [waiversRows, mechanismRows, dsRes] = await Promise.all([
      client.listWorkspaceExceptionWaivers(targetWsId, true),
      client.listDnaMechanisms(targetWsId),
      client.listWorkspaceDatasources(targetWsId),
    ]);
    setActiveWaivers(waiversRows.map(mapWaiverItem));
    setCompiledMechanism(mechanismRows[0] ? mapMechanismItem(mechanismRows[0]) : null);
    setScopedDatasources(dsRes.items ?? []);
  }, [targetWsId, locale]);

  useEffect(() => {
    if (!targetWsId) {
      setActiveWaivers([]);
      setCompiledMechanism(null);
      setScopedDatasources([]);
      return;
    }
    setScopedDatasources([]);
    let cancelled = false;
    void reloadWaiversAndMechanisms().catch((err: unknown) => {
      if (cancelled) return;
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, locale, dnaCopy.governanceErrorContext).fullText}`,
      );
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      onFeedback(
        formatI18nTemplate(dnaCopy.waiverRegisteredTemplate, { ruleId: conflictRuleId }),
      );
    } catch (err: unknown) {
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, locale, dnaCopy.waiverErrorContext).fullText}`,
      );
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
        persisted[0] ? mapMechanismItem(persisted[0]) : mapMechanismItem(res),
      );
      onFeedback(formatI18nTemplate(dnaCopy.compileSuccessTemplate, { ruleId }));
    } catch (err: unknown) {
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, locale, dnaCopy.compileErrorContext).fullText}`,
      );
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
        persisted[0] ? mapMechanismItem(persisted[0]) : mapMechanismItem(activated),
      );
      onFeedback(dnaCopy.activateSuccessBanner);
    } catch (err: unknown) {
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, locale, dnaCopy.activateErrorContext).fullText}`,
      );
    } finally {
      setSubmitting(false);
    }
  };

  return {
    dnaCopy,
    activeWaivers,
    compiledMechanism,
    scopedDatasources,
    setScopedDatasources,
    glossaryCandidates,
    setGlossaryCandidates,
    submitting,
    handleRegisterWaiver,
    handleCompileFromNorm,
    handleSignAndActivate,
  };
}

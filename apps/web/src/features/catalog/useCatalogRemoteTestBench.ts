import { createOrciaApiClient } from "@orcia/api-client";
import type { ControlCenterDatasourceItem } from "@orcia/ui";
import { useEffect, useState } from "react";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../stores/authSessionStore";

export interface CatalogTestBenchStep {
  readonly stepNumber: 1 | 2 | 3 | 4;
  readonly stepCode:
    | "1_NETWORK_TLS_ANTI_SSRF"
    | "2_AUTHENTICATION"
    | "3_CONTRACT_DISCOVERY"
    | "4_HOT_DRY_RUN";
  readonly status:
    | "PASS"
    | "FAIL"
    | "WAITING_USER_PASSTHROUGH_TOKEN"
    | "SKIPPED";
  readonly detailFr: string;
}

export interface CatalogDiscoveredCapability {
  readonly toolName: string;
  readonly qualification: "READ_ONLY" | "WRITE_STAGED_REQUIRED";
  readonly badgeFr: string;
}

export function useCatalogRemoteTestBench(params: {
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly workspaceSlug?: string;
  readonly isFr: boolean;
  readonly setFeedback: (message: string) => void;
}) {
  const { datasources, isFr, setFeedback } = params;
  const effectiveWorkspaceSlug =
    params.workspaceSlug?.trim() || "global";
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const accessToken = useAuthSessionStore((s) => s.accessToken);
  const [mcpExposed, setMcpExposed] = useState<boolean>(false);
  const [exposedToolNames, setExposedToolNames] = useState<readonly string[]>([]);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [isSavingMcp, setIsSavingMcp] = useState<boolean>(false);
  const [testBenchSteps, setTestBenchSteps] = useState<
    readonly CatalogTestBenchStep[]
  >([]);
  const [discoveredCapabilities, setDiscoveredCapabilities] = useState<
    readonly CatalogDiscoveredCapability[]
  >([]);
  const [canActivateConnector, setCanActivateConnector] = useState<boolean>(
    datasources.length > 0,
  );

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    let cancelled = false;
    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .getMcpExposureState(effectiveWorkspaceSlug)
      .then((state) => {
        if (cancelled) return;
        setMcpExposed(Boolean(state.any_exposed));
        setExposedToolNames(state.exposed_tools ?? []);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setFeedback(
          `⚠️ ${formatRfc9457ErrorToBanner(err, isFr ? "fr" : "en", isFr ? "Exposition MCP" : "MCP exposure").fullText}`,
        );
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, effectiveWorkspaceSlug, isAuthenticated, isFr, setFeedback]);

  const handleRunRemoteTestBench = async () => {
    const targetUrl =
      datasources[0]?.uri ?? "https://mcp.entreprise.interne/api";
    setIsTesting(true);
    setTestBenchSteps([]);
    setDiscoveredCapabilities([]);
    setCanActivateConnector(false);
    setFeedback(
      isFr
        ? `⏳ Vérification en cours sur ${targetUrl}…`
        : `⏳ Testing connection to ${targetUrl}…`,
    );

    const client = createOrciaApiClient({ baseUrl: "" });
    try {
      const res = await client.runRemoteServiceTestBench({
        protocol: "MCP_STREAMABLE_HTTP_SSE",
        endpoint_url: targetUrl,
        identity_mode: "SECRET_REF",
        has_user_personal_token: true,
        secret_ref_valid: true,
        allow_private_network: true,
        raw_tool_names: ["search_documents", "propose_draft_update"],
        simulated_dry_run_elapsed_ms: 42,
        simulated_dry_run_bytes: 512,
      });

      const steps: CatalogTestBenchStep[] = Array.isArray(res.steps)
        ? res.steps.map((s) => ({
            stepNumber: (s.step_number ?? 1) as 1 | 2 | 3 | 4,
            stepCode: s.step_code as CatalogTestBenchStep["stepCode"],
            status: s.status as CatalogTestBenchStep["status"],
            detailFr: s.detail_fr,
          }))
        : [];
      setTestBenchSteps(steps);

      const capabilities: CatalogDiscoveredCapability[] = Array.isArray(
        res.discovered_capabilities,
      )
        ? res.discovered_capabilities.map((c) => ({
            toolName: c.tool_name,
            qualification: c.qualification as
              | "READ_ONLY"
              | "WRITE_STAGED_REQUIRED",
            badgeFr: c.badge_fr,
          }))
        : [];
      setDiscoveredCapabilities(capabilities);

      const canActivate = Boolean(res.can_activate);
      setCanActivateConnector(canActivate);
      setFeedback(
        canActivate
          ? isFr
            ? `✅ Banc de test vérifié avec succès sur ${targetUrl}.`
            : `✅ Test bench verified on ${targetUrl}.`
          : isFr
            ? `⚠️ Vérification incomplète ou bloquée sur ${targetUrl}.`
            : `⚠️ Verification incomplete or blocked on ${targetUrl}.`,
      );
    } catch (err: unknown) {
      setCanActivateConnector(false);
      setFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, isFr ? "fr" : "en", isFr ? "Banc de test connecteur" : "Connector test bench").fullText}`,
      );
    } finally {
      setIsTesting(false);
    }
  };

  const persistMcpExposure = async (
    nextExposed: boolean,
    agentSlug: string,
    displayName: string,
    successMessage: string,
  ) => {
    setIsSavingMcp(true);
    const client = createOrciaApiClient({ baseUrl: "" });
    try {
      const updated = await client.configureAgentMcpExposure({
        workspace_slug: effectiveWorkspaceSlug,
        agent_slug: agentSlug,
        display_name: displayName,
        mcp_exposed: nextExposed,
        regime: "GOVERNED_STAGED_COPILOT",
        human_authored_required: false,
      });
      setMcpExposed(Boolean(updated.mcp_exposed));
      setExposedToolNames(updated.exposed_tools ?? []);
      setFeedback(successMessage);
    } catch (err: unknown) {
      setFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, isFr ? "fr" : "en", isFr ? "Exposition MCP" : "MCP exposure").fullText}`,
      );
    } finally {
      setIsSavingMcp(false);
    }
  };

  const handleActivateRemoteService = () => {
    const targetName = datasources[0]?.alias?.trim() || "Service externe gouverné";
    void persistMcpExposure(
      true,
      "remote-connector-service",
      targetName,
      isFr
        ? "✅ Connecteur externe activé et persisté pour vos agents."
        : "✅ External connector enabled and saved for your agents.",
    );
  };

  const handleToggleMcp = (next: boolean) => {
    const targetName = datasources[0]?.alias?.trim() || "Connecteur MCP gouverné";
    void persistMcpExposure(
      next,
      "governed-mcp-connector",
      targetName,
      next
        ? isFr
          ? "🔌 Exposition MCP activée et enregistrée pour vos outils."
          : "🔌 MCP exposure enabled and saved."
        : isFr
          ? "🔌 Exposition MCP désactivée et enregistrée."
          : "🔌 MCP exposure disabled and saved.",
    );
  };

  return {
    mcpExposed,
    exposedToolNames,
    isTesting,
    isSavingMcp,
    testBenchSteps,
    discoveredCapabilities,
    canActivateConnector,
    handleRunRemoteTestBench: () => {
      void handleRunRemoteTestBench();
    },
    handleActivateRemoteService,
    handleToggleMcp,
  };
}

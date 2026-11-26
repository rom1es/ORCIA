import {
  createOrciaApiClient,
  type DeclarativePackSummaryResponse,
} from "@orcia/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../../../components/platformSetupStore";
import { useI18n } from "../../../i18n";
import {
  formatLocalizedProblemWithCode,
  resolveLocalizedClientError,
} from "../../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../../stores/authSessionStore";

export function usePacksRegistryHealthchecks(locale: "fr" | "en") {
  const { dictionary } = useI18n();
  const copy = dictionary.categoryAControllers.packsRegistry;
  const accessToken = useAuthSessionStore((s) => s.accessToken);
  const { workspaces } = usePlatformSetup();
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "", locale }), [locale]);

  const [packs, setPacks] = useState<readonly DeclarativePackSummaryResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(false);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>("");
  const [selectedPackId, setSelectedPackId] = useState<string>("orcia-pack-sdlc");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [exportedArchiveName, setExportedArchiveName] = useState<string | null>(null);

  const loadPacksFromServer = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await apiClient.listDeclarativePacks();
      setPacks(res.packs);
      const firstPack = res.packs[0];
      if (firstPack) {
        setSelectedPackId((prev) =>
          res.packs.some((p) => p.id === prev) ? prev : firstPack.id,
        );
      }
    } catch (err: unknown) {
      setErrorMessage(
        formatLocalizedProblemWithCode(err, locale, "ERR_CLIENT_PACKS_LOAD"),
      );
    } finally {
      setIsLoading(false);
    }
  }, [apiClient, locale]);

  useEffect(() => {
    void loadPacksFromServer();
  }, [accessToken, loadPacksFromServer]);

  useEffect(() => {
    const firstWs = workspaces[0];
    if (!firstWs) {
      if (selectedWorkspaceId !== "") {
        setSelectedWorkspaceId("");
      }
      return;
    }
    if (!workspaces.some((ws) => ws.workspaceId === selectedWorkspaceId)) {
      setSelectedWorkspaceId(firstWs.workspaceId);
    }
  }, [workspaces, selectedWorkspaceId]);

  const handleRefreshHealthchecks = async () => {
    setIsCheckingHealth(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const [packsRes, healthRes] = await Promise.all([
        apiClient.listDeclarativePacks(),
        apiClient.getPacksHealth(),
      ]);
      const healthByType = new Map(
        (healthRes.connectors ?? []).map((item) => [item.connector_type, item]),
      );
      setPacks(
        packsRes.packs.map((pack) => ({
          ...pack,
          connector_health: (pack.connector_health ?? []).map(
            (conn) => healthByType.get(conn.connector_type) ?? conn,
          ),
        })),
      );
      const { healthy_count: healthyCount, total_count: totalCount, all_healthy: allHealthy } =
        healthRes;
      if (totalCount === 0) {
        setStatusMessage(copy.healthEmpty);
      } else if (allHealthy) {
        setStatusMessage(
          copy.healthAllOk
            .replace("{healthy}", String(healthyCount))
            .replace("{total}", String(totalCount)),
        );
      } else {
        setErrorMessage(
          resolveLocalizedClientError("ERR_CLIENT_PACKS_HEALTH_DEGRADED", locale, {
            detail: `${healthyCount}/${totalCount}`,
          }),
        );
      }
    } catch (err: unknown) {
      setErrorMessage(
        formatLocalizedProblemWithCode(err, locale, "ERR_CLIENT_PACKS_HEALTH_REFRESH"),
      );
    } finally {
      setIsCheckingHealth(false);
    }
  };

  const executePackZipExport = async (targetWorkspaceId: string, packId?: string) => {
    const targetPackId = packId ?? selectedPackId;
    const pack = packs.find((p) => p.id === targetPackId) ?? packs[0];
    setErrorMessage(null);
    try {
      const result = await apiClient.exportWorkspacePackZip(targetWorkspaceId, targetPackId);
      const archiveName = result.filename ?? `${pack?.slug ?? "sdlc"}-${targetWorkspaceId}.zip`;
      setExportedArchiveName(archiveName);
      setStatusMessage(copy.archiveExported.replace("{archive}", archiveName));
      if (typeof URL !== "undefined" && typeof URL.createObjectURL === "function") {
        const objectUrl = URL.createObjectURL(result.blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = archiveName;
        link.click();
        URL.revokeObjectURL(objectUrl);
      }
    } catch (err: unknown) {
      setErrorMessage(
        formatLocalizedProblemWithCode(err, locale, "ERR_CLIENT_PACKS_EXPORT_ZIP"),
      );
    }
  };

  const handleExportWorkspaceZip = async (packId?: string) => {
    if (!selectedWorkspaceId) {
      setErrorMessage(
        resolveLocalizedClientError("ERR_CLIENT_PACKS_WORKSPACE_REQUIRED", locale),
      );
      return;
    }
    await executePackZipExport(selectedWorkspaceId, packId);
  };

  const handleExportPackBundleZip = async (packId?: string) => {
    await executePackZipExport(selectedWorkspaceId || "platform", packId);
  };

  const workspaceOptions = useMemo(
    () =>
      workspaces.map((ws) => ({
        id: ws.workspaceId,
        label: copy.workspaceOptionPrefix.replace("{name}", ws.name),
      })),
    [workspaces, copy.workspaceOptionPrefix],
  );

  return {
    packs,
    isLoading: isLoading || isCheckingHealth,
    selectedWorkspaceId,
    setSelectedWorkspaceId,
    selectedPackId,
    setSelectedPackId,
    statusMessage,
    errorMessage,
    exportedArchiveName,
    workspaceOptions,
    handleRefreshHealthchecks: () => {
      void handleRefreshHealthchecks();
    },
    reloadPacksFromServer: loadPacksFromServer,
    setStatusMessage,
    setErrorMessage,
    handleExportWorkspaceZip,
    handleExportPackBundleZip,
  };
}

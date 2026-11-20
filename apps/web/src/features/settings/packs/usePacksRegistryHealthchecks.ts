import {
  createOrciaApiClient,
  OrciaProblemError,
  type DeclarativePackSummaryResponse,
} from "@orcia/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../../../components/platformSetupStore";
import { useAuthSessionStore } from "../../../stores/authSessionStore";

function formatPackApiError(err: unknown, fallback: string): string {
  if (err instanceof OrciaProblemError) {
    return `${err.problem.detail} (${err.problem.error_code})`;
  }
  if (err instanceof Error && err.message.trim()) {
    return err.message;
  }
  return fallback;
}

export function usePacksRegistryHealthchecks(locale: "fr" | "en") {
  const isFr = locale === "fr";
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
      if (firstPack && !res.packs.some((p) => p.id === selectedPackId)) {
        setSelectedPackId(firstPack.id);
      }
    } catch (err: unknown) {
      setErrorMessage(
        formatPackApiError(
          err,
          isFr
            ? "Impossible de charger le registre des packs déclaratifs."
            : "Unable to load the declarative packs registry.",
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }, [apiClient, isFr, selectedPackId]);

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
        setStatusMessage(
          isFr
            ? "Diagnostics de santé MCP actualisés : aucun connecteur requis configuré."
            : "MCP connector healthchecks refreshed: no required connectors configured.",
        );
      } else if (allHealthy) {
        setStatusMessage(
          isFr
            ? `Diagnostics de santé MCP actualisés : ${healthyCount}/${totalCount} connecteurs requis opérationnels.`
            : `MCP connector healthchecks refreshed: ${healthyCount}/${totalCount} required connectors healthy.`,
        );
      } else {
        setErrorMessage(
          isFr
            ? `Diagnostics de santé MCP : ${healthyCount}/${totalCount} connecteurs opérationnels (${totalCount - healthyCount} indisponible(s)).`
            : `MCP connector healthchecks: ${healthyCount}/${totalCount} connectors operational (${totalCount - healthyCount} unavailable).`,
        );
      }
    } catch (err: unknown) {
      setErrorMessage(
        formatPackApiError(
          err,
          isFr
            ? "Impossible d'actualiser les diagnostics de santé des connecteurs."
            : "Unable to refresh connector healthchecks.",
        ),
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
      setStatusMessage(
        isFr
          ? `Archive déclarative ${archiveName} générée (pack.yaml, glossary.yaml, agents/*.md, skills/*.md, gates/*, workflows/*.yaml — 0 code exécutable).`
          : `Declarative archive ${archiveName} generated (pack.yaml, glossary.yaml, agents/*.md, skills/*.md, gates/*, workflows/*.yaml — 0 executable code).`,
      );
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
        formatPackApiError(
          err,
          isFr
            ? "Échec de l'export ZIP du pack déclaratif."
            : "Failed to export declarative pack ZIP.",
        ),
      );
    }
  };

  const handleExportWorkspaceZip = async (packId?: string) => {
    if (!selectedWorkspaceId) {
      setErrorMessage(
        isFr
          ? "Créez d'abord un espace de travail dans « Mes Espaces » avant d'exporter son pack."
          : "Create a workspace in 'My Spaces' before exporting its pack.",
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
        label: `Espace : ${ws.name}`,
      })),
    [workspaces],
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
    handleExportWorkspaceZip,
    handleExportPackBundleZip,
  };
}

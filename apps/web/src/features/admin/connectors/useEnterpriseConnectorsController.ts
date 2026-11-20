import { useCallback, useEffect, useState } from "react";
import {
  createOrciaApiClient,
  OrciaProblemError,
  type EnterpriseConnectorCreateRequest,
  type EnterpriseConnectorItemResponse,
} from "@orcia/api-client";
import { useAuthSessionStore } from "../../../stores/authSessionStore";

export function useEnterpriseConnectorsController(isFr: boolean) {
  const [connectors, setConnectors] = useState<readonly EnterpriseConnectorItemResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [kind, setKind] = useState<EnterpriseConnectorCreateRequest["connector_kind"]>("GITLAB");
  const [name, setName] = useState<string>("");
  const [baseUrl, setBaseUrl] = useState<string>("");
  const [authMode, setAuthMode] = useState<EnterpriseConnectorCreateRequest["auth_mode"]>("OAUTH2_PASSTHROUGH");
  const [adminSecret, setAdminSecret] = useState<string>("");

  const client = createOrciaApiClient({ baseUrl: "" });

  const loadConnectors = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await client.listEnterpriseConnectors();
      setConnectors(res.items);
    } catch (err) {
      if (err instanceof OrciaProblemError) {
        setErrorMessage(err.problem.title || err.message);
      } else {
        setErrorMessage(isFr ? "Impossible de charger les connecteurs." : "Failed to load connectors.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [isFr]);

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const accessToken = useAuthSessionStore((s) => s.accessToken);

  useEffect(() => {
    if (isHydrating) return;
    setErrorMessage(null);
    void loadConnectors();
  }, [loadConnectors, isHydrating, accessToken]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !baseUrl.trim()) return;
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await client.createEnterpriseConnector({
        connector_kind: kind,
        name: name.trim(),
        base_url: baseUrl.trim(),
        auth_mode: authMode,
        admin_secret_value: adminSecret.trim() ? adminSecret.trim() : undefined,
        enabled: true,
      });
      setName("");
      setBaseUrl("");
      setAdminSecret("");
      setSuccessMessage(
        isFr ? "Connecteur d'entreprise enregistré au niveau du socle." : "Enterprise connector registered.",
      );
      await loadConnectors();
    } catch (err) {
      if (err instanceof OrciaProblemError) {
        setErrorMessage(err.problem.detail || err.problem.title);
      } else {
        setErrorMessage(isFr ? "Erreur lors de l'enregistrement du connecteur." : "Error registering connector.");
      }
    }
  };

  const handleDelete = async (connectorId: string) => {
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await client.deleteEnterpriseConnector(connectorId);
      setSuccessMessage(isFr ? "Connecteur supprimé." : "Connector deleted.");
      await loadConnectors();
    } catch (err) {
      if (err instanceof OrciaProblemError) {
        setErrorMessage(err.problem.detail || err.problem.title);
      } else {
        setErrorMessage(isFr ? "Erreur lors de la suppression." : "Error deleting connector.");
      }
    }
  };

  return {
    connectors,
    isLoading,
    errorMessage,
    successMessage,
    kind,
    setKind,
    name,
    setName,
    baseUrl,
    setBaseUrl,
    authMode,
    setAuthMode,
    adminSecret,
    setAdminSecret,
    handleCreate,
    handleDelete,
  };
}

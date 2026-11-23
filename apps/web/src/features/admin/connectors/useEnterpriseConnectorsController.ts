import { useCallback, useEffect, useState } from "react";
import {
  createOrciaApiClient,
  type EnterpriseConnectorCreateRequest,
  type EnterpriseConnectorItemResponse,
} from "@orcia/api-client";
import { useI18n } from "../../../i18n";
import { extractLocalizedApiError } from "../../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../../stores/authSessionStore";

export function useEnterpriseConnectorsController(_useFrench?: boolean) {
  const { dictionary, locale } = useI18n();
  const copy = dictionary.categoryAControllers.connectors;
  const [connectors, setConnectors] = useState<readonly EnterpriseConnectorItemResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [kind, setKind] = useState<EnterpriseConnectorCreateRequest["connector_kind"]>("GITLAB");
  const [name, setName] = useState<string>("");
  const [baseUrl, setBaseUrl] = useState<string>("");
  const [authMode, setAuthMode] = useState<EnterpriseConnectorCreateRequest["auth_mode"]>("OAUTH2_PASSTHROUGH");
  const [adminSecret, setAdminSecret] = useState<string>("");

  const client = createOrciaApiClient({ baseUrl: "", locale });

  const loadConnectors = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await client.listEnterpriseConnectors();
      setConnectors(res.items);
    } catch (err) {
      setErrorMessage(
        extractLocalizedApiError(err, locale, "ERR_CLIENT_CONNECTORS_LOAD").errorMessage,
      );
    } finally {
      setIsLoading(false);
    }
  }, [locale]);

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
      setSuccessMessage(copy.registeredSuccess);
      await loadConnectors();
    } catch (err) {
      setErrorMessage(
        extractLocalizedApiError(err, locale, "ERR_CLIENT_CONNECTOR_SAVE").errorMessage,
      );
    }
  };

  const handleDelete = async (connectorId: string) => {
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await client.deleteEnterpriseConnector(connectorId);
      setSuccessMessage(copy.deletedSuccess);
      await loadConnectors();
    } catch (err) {
      setErrorMessage(
        extractLocalizedApiError(err, locale, "ERR_CLIENT_CONNECTOR_DELETE").errorMessage,
      );
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

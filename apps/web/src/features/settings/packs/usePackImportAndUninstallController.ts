import { createOrciaApiClient } from "@orcia/api-client";
import type { UiPackScopeType } from "@orcia/ui";
import { useCallback, useMemo, useState } from "react";
import { formatI18nTemplate, useI18n } from "../../../i18n";
import { useAuthSessionStore } from "../../../stores/authSessionStore";
import { formatDetailedPackError } from "./packMappers";

export function usePackImportAndUninstallController(params: {
  readonly onRefreshAll: () => Promise<void> | void;
  readonly onStatusMessage: (msg: string) => void;
  readonly onErrorMessage: (msg: string) => void;
}) {
  const { onRefreshAll, onStatusMessage, onErrorMessage } = params;
  const { dictionary, locale } = useI18n();
  const actionsCopy = dictionary.packsUi.actions;
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "", locale }), [locale]);

  const [importModalOpen, setImportModalOpen] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const handleImportPackFile = useCallback(
    async (input: {
      readonly file: File;
      readonly scopeType: Exclude<UiPackScopeType, "GLOBAL">;
      readonly scopeId: string;
      readonly replaceDraft: boolean;
    }) => {
      if (readOnlyObserver) return;
      setIsImporting(true);
      setImportError(null);
      try {
        const res = await apiClient.importPackArchiveFile({
          file: input.file,
          filename: input.file.name,
          scopeType: input.scopeType,
          scopeId: input.scopeId,
          replaceDraft: input.replaceDraft,
        });
        setImportModalOpen(false);
        onStatusMessage(
          formatI18nTemplate(actionsCopy.importSuccessTemplate, {
            name: res.name,
            version: res.version,
          }),
        );
        await onRefreshAll();
      } catch (err: unknown) {
        setImportError(formatDetailedPackError(err, locale, input.file.name).fullText);
      } finally {
        setIsImporting(false);
      }
    },
    [actionsCopy.importSuccessTemplate, apiClient, locale, onRefreshAll, onStatusMessage, readOnlyObserver],
  );

  const handleUninstallBundle = useCallback(
    async (bundleId: string, slug: string) => {
      if (readOnlyObserver) return;
      try {
        await apiClient.deletePackBundle(bundleId);
        onStatusMessage(formatI18nTemplate(actionsCopy.uninstallSuccessTemplate, { slug }));
        await onRefreshAll();
      } catch (err: unknown) {
        onErrorMessage(formatDetailedPackError(err, locale, slug).fullText);
      }
    },
    [actionsCopy.uninstallSuccessTemplate, apiClient, locale, onErrorMessage, onRefreshAll, onStatusMessage, readOnlyObserver],
  );

  return {
    importModalOpen,
    setImportModalOpen: (open: boolean) => {
      setImportError(null);
      setImportModalOpen(open);
    },
    isImporting,
    importError,
    handleImportPackFile,
    handleUninstallBundle,
  };
}

import {
  extractDraftPackReferences,
  OrciaProblemError,
  type DraftPackReferenceInfo,
} from "@orcia/api-client";
import { useCallback, useState } from "react";
import { useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";

export interface PendingUnlinkDeleteTarget {
  readonly entityType: "AGENT" | "SKILL" | "WORKFLOW_V2" | "VSM_V2";
  readonly entityId: string;
  readonly entityLabel: string;
  readonly draftPacks: readonly DraftPackReferenceInfo[];
  readonly executeUnlinkedDelete: () => Promise<boolean>;
}

export function isReferencedByPackDraftProblem(err: unknown): boolean {
  if (err instanceof OrciaProblemError) {
    return err.problem.error_code === "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT";
  }
  return (
    typeof err === "object" &&
    err !== null &&
    "error_code" in err &&
    (err as { error_code?: unknown }).error_code === "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT"
  );
}

export function useGuardedEntityDelete() {
  const { locale } = useI18n();
  const [pendingTarget, setPendingTarget] = useState<PendingUnlinkDeleteTarget | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  const interceptDeleteError = useCallback(
    (params: {
      readonly error: unknown;
      readonly entityType: PendingUnlinkDeleteTarget["entityType"];
      readonly entityId: string;
      readonly entityLabel: string;
      readonly executeUnlinkedDelete: () => Promise<boolean>;
    }): boolean => {
      if (!isReferencedByPackDraftProblem(params.error)) {
        return false;
      }
      setDialogError(null);
      setPendingTarget({
        entityType: params.entityType,
        entityId: params.entityId,
        entityLabel: params.entityLabel,
        draftPacks: extractDraftPackReferences(params.error),
        executeUnlinkedDelete: params.executeUnlinkedDelete,
      });
      return true;
    },
    [],
  );

  const cancelUnlink = useCallback(() => {
    setPendingTarget(null);
    setDialogError(null);
    setIsConfirming(false);
  }, []);

  const confirmUnlink = useCallback(async () => {
    if (!pendingTarget || isConfirming) return;
    setIsConfirming(true);
    setDialogError(null);
    try {
      const ok = await pendingTarget.executeUnlinkedDelete();
      if (ok) {
        setPendingTarget(null);
      }
    } catch (err: unknown) {
      setDialogError(formatRfc9457ErrorToBanner(err, locale, pendingTarget.entityLabel).fullText);
    } finally {
      setIsConfirming(false);
    }
  }, [isConfirming, locale, pendingTarget]);

  return {
    pendingTarget,
    isConfirming,
    dialogError,
    interceptDeleteError,
    cancelUnlink,
    confirmUnlink,
  };
}

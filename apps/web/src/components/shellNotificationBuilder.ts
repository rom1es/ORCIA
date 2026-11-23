import type {
  AutonomousRunSupervisionItemSchema,
  TaskNotificationItemResponse,
} from "@orcia/api-client";
import type {
  ControlCenterRunItem,
  ControlCenterWorkspaceGovItem,
  UiNotificationCenterItem,
} from "@orcia/ui";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../i18n";
import type {
  ConfiguredLlmTierMapping,
  ConfiguredOrgUnit,
  ConfiguredPlatformAdmin,
} from "./platformSetupStorageHelpers";
import type { WorkspaceSseClaimEvent } from "./useWorkspaceEventsSse";

export function buildShellNotificationItems(params: {
  readonly isFr: boolean;
  readonly locale?: "fr" | "en";
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly hasModels?: boolean;
  readonly hasOrgUnits?: boolean;
  readonly hasWorkspaces?: boolean;
  readonly runs: readonly ControlCenterRunItem[];
  readonly autonomousRuns?: readonly AutonomousRunSupervisionItemSchema[];
  readonly inboxNotifications?: readonly TaskNotificationItemResponse[];
  readonly lastClaimEvent: WorkspaceSseClaimEvent | null;
  readonly mustChangePassword?: boolean;
}): readonly UiNotificationCenterItem[] {
  const {
    isFr,
    locale,
    platformAdmin,
    orgUnits,
    workspaces,
    llmTiers,
    hasModels,
    hasOrgUnits,
    hasWorkspaces,
    runs,
    autonomousRuns = [],
    inboxNotifications = [],
    lastClaimEvent,
    mustChangePassword,
  } = params;

  if (platformAdmin === null) {
    return [];
  }

  const copy = resolveDictionaryForFlag(isFr, locale).shellNotifications;
  const effectiveHasModels = hasModels ?? llmTiers.length > 0;
  const effectiveHasOrgUnits = hasOrgUnits ?? orgUnits.length > 0;
  const effectiveHasWorkspaces = hasWorkspaces ?? workspaces.length > 0;
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const memberTeamIds = platformAdmin.memberTeamIds ?? [];
  const hasBillingTeam =
    memberTeamIds.length > 0 || teamUnits.length > 0 || effectiveHasWorkspaces;

  return [
    ...(mustChangePassword
      ? [
          {
            id: "notif-temporary-password",
            kind: "SETUP_PREREQUISITE" as const,
            badgeLabel: copy.tempPassword.badge,
            title: copy.tempPassword.title,
            description: copy.tempPassword.description,
            targetRoute: "#change-password",
            ctaLabel: copy.tempPassword.cta,
          },
        ]
      : []),
    ...(!effectiveHasModels
      ? [
          {
            id: "setup-llm-missing",
            kind: "SETUP_PREREQUISITE" as const,
            badgeLabel: copy.llmMissing.badge,
            title: copy.llmMissing.title,
            description: copy.llmMissing.description,
            targetRoute: "/settings",
            ctaLabel: copy.llmMissing.cta,
          },
        ]
      : []),
    ...(!hasBillingTeam
      ? [
          {
            id: "setup-billing-team-missing",
            kind: "SETUP_PREREQUISITE" as const,
            badgeLabel: copy.billingTeamMissing.badge,
            title: copy.billingTeamMissing.title,
            description: copy.billingTeamMissing.description,
            targetRoute: "/settings",
            ctaLabel: copy.billingTeamMissing.cta,
          },
        ]
      : []),
    ...(!effectiveHasOrgUnits
      ? [
          {
            id: "setup-org-missing",
            kind: "SETUP_PREREQUISITE" as const,
            badgeLabel: copy.orgMissing.badge,
            title: copy.orgMissing.title,
            description: copy.orgMissing.description,
            targetRoute: "/settings",
            ctaLabel: copy.orgMissing.cta,
          },
        ]
      : []),
    ...(!effectiveHasWorkspaces
      ? [
          {
            id: "setup-workspace-missing",
            kind: "SETUP_PREREQUISITE" as const,
            badgeLabel: copy.workspaceMissing.badge,
            title: copy.workspaceMissing.title,
            description: copy.workspaceMissing.description,
            targetRoute: "/workspaces",
            ctaLabel: copy.workspaceMissing.cta,
          },
        ]
      : []),
    ...runs.map((run) => ({
      id: `run-decision-${run.runId}`,
      kind: "DECISION_WAITING" as const,
      badgeLabel: copy.decisionWaiting.badge,
      title: run.title,
      description: `${run.workspaceName} • ${run.currentStepKey} — ${run.blackboardSummary}`,
      targetRoute: "/cockpit",
      ctaLabel: copy.decisionWaiting.cta,
    })),
    ...inboxNotifications
      .filter((n) => n.status !== "RESOLVED")
      .map((n) => ({
        id: `task-notif-${n.id}`,
        kind: (n.status === "OPEN" ? "ACTION_REQUIRED" : "DECISION_WAITING") as
          | "ACTION_REQUIRED"
          | "DECISION_WAITING",
        badgeLabel: n.status === "OPEN" ? copy.inboxTask.openBadge : copy.inboxTask.claimedBadge,
        title: n.title,
        description: n.summary,
        targetRoute: "/inbox",
        ctaLabel: copy.inboxTask.cta,
      })),
    ...autonomousRuns.map((autoRun): UiNotificationCenterItem => {
      const isEsc = autoRun.run_status === "PAUSED_AUTONOMOUS_ESCALATION";
      const isOpen = autoRun.trigger_status === "CIRCUIT_OPEN";
      const isSample = autoRun.post_hoc_status === "PENDING_SAMPLE";
      if (isEsc || isOpen || isSample) {
        const badgeLabel = isEsc
          ? copy.autonomous.escalationBadge
          : isOpen
            ? copy.autonomous.triggerPausedBadge
            : copy.autonomous.qualitySampleBadge;
        return {
          id: `auto-priority-${autoRun.run_id}`,
          kind: "ACTION_REQUIRED",
          isAutonomousPriority: true,
          triggerLabel: autoRun.trigger_label,
          badgeLabel,
          title: autoRun.workflow_title,
          description: formatI18nTemplate(
            isSample
              ? copy.autonomous.sampleDescriptionTemplate
              : copy.autonomous.attentionDescriptionTemplate,
            { triggerLabel: autoRun.trigger_label },
          ),
          targetRoute: isSample ? "/finops" : "/processes",
          ctaLabel: copy.autonomous.reviewCta,
        };
      }
      return {
        id: `auto-nominal-${autoRun.run_id}`,
        kind: "INFO",
        isAutonomousNominal: true,
        triggerLabel: autoRun.trigger_label,
        badgeLabel: copy.autonomous.nominalBadge,
        title: autoRun.workflow_title,
        description: `${autoRun.trigger_label}`,
        targetRoute: "/processes",
        ctaLabel: copy.autonomous.inspectCta,
      };
    }),
    ...(lastClaimEvent
      ? [
          {
            id: `sse-claim-${lastClaimEvent.eventId}`,
            kind: "DECISION_WAITING" as const,
            badgeLabel: copy.livePresence.badge,
            title: formatI18nTemplate(
              lastClaimEvent.eventName === "task.claim.locked"
                ? copy.livePresence.claimedTitleTemplate
                : copy.livePresence.releasedTitleTemplate,
              { stepExecutionId: lastClaimEvent.stepExecutionId },
            ),
            description: `${lastClaimEvent.workspaceId} • ${lastClaimEvent.dispatchLatencyMs} ms`,
            targetRoute: "/cockpit",
            ctaLabel: copy.livePresence.cta,
          },
        ]
      : []),
  ];
}

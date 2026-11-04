import { createOrciaApiClient } from "@orcia/api-client";
import {
  AssistantCitationPillsAndArtifactCard,
  AssistantFoldersAndCollaborativeThreadView,
  AssistantGovernanceModalAndStudio,
  AssistantSpeedSelectorAndStreamView,
  ContextualInfoTriggerButton,
  StatusBadge,
  type AssistantFolderVisibilityMode,
  type UiAssistantFolderItem,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function InboxFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute, openHelpSection } = useShellNavigation();
  const { platformAdmin, workspaces } = usePlatformSetup();
  const inboxCopy = dictionary.inboxAndClaims;
  const isFr = locale === "fr";

  const [scopeFilter, setScopeFilter] = useState<"ALL" | "PERSONAL" | "TEAM">("ALL");
  const [folders, setFolders] = useState<readonly UiAssistantFolderItem[]>([]);
  const [activeFolderId, setActiveFolderId] = useState<string>("");
  const [governanceOpen, setGovernanceOpen] = useState<boolean>(false);
  const [streamedText, setStreamedText] = useState<string>("");

  const activeWorkspaceId = workspaces[0]?.workspaceId ?? "";

  return (
    <div className="space-y-4" data-testid="inbox-feature-panel">
      {/* Barre d'actions Mon Assistant & Réglages */}
      <div className="orcia-bento-card flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <StatusBadge
            testId="inbox-amber-counter"
            label={`${inboxCopy.amberCounterPrefix} 0`}
            tone="amber"
            pill
          />
          <ContextualInfoTriggerButton
            sectionId="assistant-modes"
            label={
              isFr
                ? "Comprendre les 3 modes de réponse de Mon Assistant"
                : "Understand My Assistant's 3 response modes"
            }
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <button
          type="button"
          data-testid="assistant-open-governance-btn"
          onClick={() => setGovernanceOpen((prev) => !prev)}
          className="rounded border border-border-subtle bg-surface-elevated px-3 py-1 text-xs font-semibold text-text-primary"
        >
          {dictionary.assistantGovernance.modalTitle}
        </button>
      </div>

      {/* Modale Réglages de l'Assistant */}
      {governanceOpen ? (
        <AssistantGovernanceModalAndStudio
          workspaceId={activeWorkspaceId}
          canEditWorkspaceLayer={true}
          canOpenStudioModeB={true}
          assembledLayers={[]}
          studioNodes={[]}
          labels={dictionary.assistantGovernance}
        />
      ) : null}

      {/* Dossiers Thématiques 📁 & Partage Collaboratif (démarre 100 % vide) */}
      <AssistantFoldersAndCollaborativeThreadView
        workspaceId={activeWorkspaceId}
        activeFolderId={activeFolderId}
        folders={folders}
        historyHits={[]}
        currentAuthorPassthroughIdentity={platformAdmin?.email ?? ""}
        labels={dictionary.assistantFolders}
        onSelectFolder={(folderId) => setActiveFolderId(folderId)}
        onUpdatePinnedNotes={(folderId, notes) => {
          setFolders((prev) =>
            prev.map((f) => (f.folderId === folderId ? { ...f, pinnedNotesMarkdown: notes } : f)),
          );
        }}
        onChangeVisibility={(folderId, mode: AssistantFolderVisibilityMode) => {
          setFolders((prev) =>
            prev.map((f) => (f.folderId === folderId ? { ...f, visibilityMode: mode } : f)),
          );
        }}
        onLaunchProcessFromFolder={() => navigateToRoute("/processes")}
      />

      {/* Sélecteur de Mode de Réponse (démarre 100 % vide) */}
      <AssistantSpeedSelectorAndStreamView
        workspaceId={activeWorkspaceId}
        userId={platformAdmin?.email ?? ""}
        hat="PLATFORM_ADMIN"
        cacheHit={false}
        cacheLookupMs={0}
        nodes1To4DeterministicMs={0}
        stepProgress={[]}
        streamedText={streamedText}
        labels={dictionary.assistantSpeedStream}
        onSendTurn={({ userPrompt, requestedSpeed }) => {
          setStreamedText(`[${requestedSpeed}] ${userPrompt}`);
          const isJsdom =
            typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
          if (!isJsdom) {
            const client = createOrciaApiClient({ baseUrl: "" });
            void client
              .executeAssistantTurn({
                workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
                hat: "PLATFORM_ADMIN",
                user_prompt: userPrompt,
                requested_speed: requestedSpeed,
              })
              .then((res) => {
                if (res.response_text) {
                  setStreamedText(res.response_text);
                }
              })
              .catch(() => undefined);
          }
        }}
      />

      {/* Pastilles de Citation & Brouillon de Document (démarre 100 % vide) */}
      <AssistantCitationPillsAndArtifactCard
        sanitizedResponseText={streamedText}
        sources={[]}
        glossaryItems={[]}
        toolOutputs={[]}
        footerSummaryLine=""
        labels={dictionary.assistantCitations}
        onContinueInProcess={() => navigateToRoute("/processes")}
      />

      {/* Boîte de notifications et filtres de périmètre */}
      <div className="orcia-bento-card">
        <div
          role="group"
          aria-label="Scope filters"
          style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}
        >
          {(["ALL", "PERSONAL", "TEAM"] as const).map((scopeKey) => {
            const label =
              scopeKey === "ALL"
                ? inboxCopy.filterAllLabel
                : scopeKey === "PERSONAL"
                  ? inboxCopy.filterPersonalLabel
                  : inboxCopy.filterTeamLabel;
            const active = scopeFilter === scopeKey;
            return (
              <button
                key={scopeKey}
                type="button"
                data-testid={`inbox-filter-${scopeKey.toLowerCase()}`}
                onClick={() => setScopeFilter(scopeKey)}
                style={{
                  padding: "4px 12px",
                  borderRadius: "var(--radius-full)",
                  border: active
                    ? "1px solid var(--color-primary-cobalt)"
                    : "1px solid var(--color-border)",
                  backgroundColor: active
                    ? "var(--color-sidebar-active-bg)"
                    : "var(--color-surface-card)",
                  color: active ? "var(--color-primary-cobalt)" : "var(--color-foreground)",
                  fontFamily: "var(--font-sans)",
                  fontSize: "var(--font-size-mono)",
                  fontWeight: active ? 600 : 500,
                  cursor: "pointer",
                }}
              >
                {label}
              </button>
            );
          })}
        </div>

        <div
          data-testid="inbox-empty-state"
          style={{
            padding: "20px",
            borderRadius: "var(--radius-md)",
            border: "1px dashed var(--color-border)",
            backgroundColor: "var(--color-surface-bg)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <strong>
              {isFr
                ? "Aucune demande ni décision en attente"
                : "No pending request or decision"}
            </strong>
            <p
              style={{
                margin: "4px 0 0 0",
                fontSize: "13px",
                color: "var(--color-muted-foreground)",
              }}
            >
              {isFr
                ? "Les demandes d'arbitrage, rédactions attendues et étapes de validation apparaîtront ici dès qu'un processus en aura besoin."
                : "Decisions, required authoring entries, and review steps will appear here as soon as a process requests them."}
            </p>
          </div>
          <button
            type="button"
            data-testid="inbox-go-cockpit-btn"
            onClick={() => navigateToRoute("/cockpit")}
            style={{
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-card)",
              color: "var(--color-foreground)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isFr ? "Retour au Cockpit" : "Back to Cockpit"}
          </button>
        </div>
      </div>
    </div>
  );
}

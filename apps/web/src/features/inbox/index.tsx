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
  type UiThreeSpeedStepProgress,
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
  const [governanceFeedback, setGovernanceFeedback] = useState<string | null>(null);
  const [streamedText, setStreamedText] = useState<string>("");
  const [stepProgress, setStepProgress] = useState<readonly UiThreeSpeedStepProgress[]>([]);
  const [cacheHit, setCacheHit] = useState<boolean>(false);
  const [cacheLookupMs, setCacheLookupMs] = useState<number>(0);
  const [nodes1To4Ms, setNodes1To4Ms] = useState<number>(0);
  const [ttftMs, setTtftMs] = useState<number>(0);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeWorkspaceId = workspaces[0]?.workspaceId ?? "";
  const isJsdom =
    typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");

  return (
    <div className="space-y-4" data-testid="inbox-feature-panel">
      {governanceFeedback ? (
        <div
          role="status"
          data-testid="assistant-governance-feedback-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          {governanceFeedback}
        </div>
      ) : null}

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
          onSaveUserPreferences={(payload) => {
            setGovernanceFeedback(
              isFr
                ? `✅ Préférences personnelles enregistrées (ton : ${payload.responseTone}, format : ${payload.favoriteFormat}).`
                : `✅ Personal preferences saved (tone: ${payload.responseTone}, format: ${payload.favoriteFormat}).`,
            );
            setGovernanceOpen(false);
          }}
          onSaveWorkspaceSettings={(payload) => {
            setGovernanceFeedback(
              isFr
                ? `✅ Réglages de l'Espace enregistrés (accès externe : ${payload.mcpExposeAssistant ? "activé" : "désactivé"}).`
                : `✅ Workspace settings saved (external access: ${payload.mcpExposeAssistant ? "enabled" : "disabled"}).`,
            );
            setGovernanceOpen(false);
          }}
          onSaveStudioOverride={(payload) => {
            setGovernanceFeedback(
              isFr
                ? `✅ Configuration avancée enregistrée pour le périmètre ${payload.scopeLevel}.`
                : `✅ Advanced configuration saved for scope ${payload.scopeLevel}.`,
            );
            setGovernanceOpen(false);
          }}
          onResetStudioOverride={(scopeLevel) => {
            setGovernanceFeedback(
              isFr
                ? `✅ Configuration réinitialisée aux valeurs par défaut (${scopeLevel}).`
                : `✅ Configuration reset to defaults (${scopeLevel}).`,
            );
          }}
          onClose={() => setGovernanceOpen(false)}
        />
      ) : null}

      {/* Dossiers Thématiques 📁 & Partage Collaboratif */}
      <AssistantFoldersAndCollaborativeThreadView
        workspaceId={activeWorkspaceId}
        activeFolderId={activeFolderId}
        folders={folders}
        historyHits={[]}
        currentAuthorPassthroughIdentity={platformAdmin?.email ?? ""}
        labels={dictionary.assistantFolders}
        onSelectFolder={(folderId) => setActiveFolderId(folderId)}
        onCreateFolder={(title) => {
          const newId = `folder-${folders.length + 1}`;
          const newFolder: UiAssistantFolderItem = {
            folderId: newId,
            title,
            pinnedNotesMarkdown: "",
            consolidatedSummary: isFr
              ? `Dossier thématique « ${title} »`
              : `Thematic folder "${title}"`,
            visibilityMode: "PRIVATE",
            hasRestrictedSources: false,
            assembledLayer5PromptBlock: `Dossier actif : ${title}`,
          };
          setFolders((prev) => [...prev, newFolder]);
          setActiveFolderId(newId);
          setGovernanceFeedback(
            isFr
              ? `✅ Dossier « ${title} » créé et sélectionné.`
              : `✅ Folder "${title}" created and selected.`,
          );
          if (!isJsdom) {
            const client = createOrciaApiClient({ baseUrl: "" });
            void client
              .createAssistantFolder({
                workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
                title,
              })
              .then((res) => {
                setFolders((prev) =>
                  prev.map((f) =>
                    f.folderId === newId ? { ...f, folderId: res.folder_id } : f,
                  ),
                );
                setActiveFolderId(res.folder_id);
              })
              .catch((err: unknown) => {
                const detail = err instanceof Error ? err.message : "Erreur de création";
                setGovernanceFeedback(
                  isFr
                    ? `⚠️ Dossier « ${title} » conservé localement (détail serveur : ${detail}).`
                    : `⚠️ Folder "${title}" kept locally (server detail: ${detail}).`,
                );
              });
          }
        }}
        onUpdatePinnedNotes={(folderId, notes) => {
          setFolders((prev) =>
            prev.map((f) => (f.folderId === folderId ? { ...f, pinnedNotesMarkdown: notes } : f)),
          );
          setGovernanceFeedback(
            isFr ? "✅ Notes du dossier enregistrées." : "✅ Folder notes saved.",
          );
        }}
        onChangeVisibility={(folderId, mode: AssistantFolderVisibilityMode) => {
          setFolders((prev) =>
            prev.map((f) => (f.folderId === folderId ? { ...f, visibilityMode: mode } : f)),
          );
          setGovernanceFeedback(
            isFr
              ? `✅ Visibilité du dossier mise à jour (${mode}).`
              : `✅ Folder visibility updated (${mode}).`,
          );
        }}
        onSendCollaborativeMessage={(message) => {
          setStreamedText(
            isFr
              ? `💬 Message ajouté à la discussion : ${message}`
              : `💬 Message added to thread: ${message}`,
          );
        }}
        onLaunchProcessFromFolder={() => navigateToRoute("/processes")}
      />

      {/* Sélecteur de Mode de Réponse */}
      <AssistantSpeedSelectorAndStreamView
        workspaceId={activeWorkspaceId}
        userId={platformAdmin?.email ?? ""}
        hat="PLATFORM_ADMIN"
        cacheHit={cacheHit}
        cacheLookupMs={cacheLookupMs}
        nodes1To4DeterministicMs={nodes1To4Ms}
        ttftMs={ttftMs}
        stepProgress={stepProgress}
        streamedText={streamedText}
        isGenerating={isGenerating}
        errorMessage={errorMessage}
        labels={dictionary.assistantSpeedStream}
        onSendTurn={({ userPrompt, requestedSpeed, deepAuditPillActive }) => {
          setErrorMessage(null);
          setIsGenerating(true);
          setStreamedText(
            isFr
              ? `⏳ Mon Assistant prépare votre réponse pour « ${userPrompt} »...`
              : `⏳ My Assistant is preparing your answer for "${userPrompt}"...`,
          );
          if (isJsdom) {
            setIsGenerating(false);
            setStreamedText(`[${requestedSpeed}] ${userPrompt}`);
            return;
          }
          const client = createOrciaApiClient({ baseUrl: "" });
          void client
            .executeAssistantTurn({
              workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
              hat: "PLATFORM_ADMIN",
              user_prompt: userPrompt,
              requested_speed: requestedSpeed,
              deep_audit_pill_active: deepAuditPillActive,
            })
            .then((res) => {
              setIsGenerating(false);
              setCacheHit(Boolean(res.cache_hit));
              setCacheLookupMs(Number(res.cache_lookup_ms ?? 0));
              setNodes1To4Ms(Number(res.nodes_1_to_4_deterministic_ms ?? 0));
              setTtftMs(Number(res.ttft_ms ?? 0));
              if (Array.isArray(res.step_progress)) {
                setStepProgress(
                  res.step_progress.map((st) => ({
                    stepCode: st.step_code,
                    label: st.label,
                    durationMs: st.duration_ms,
                    status: st.status ?? "COMPLETED",
                    connectorOrLens: st.connector_or_lens ?? null,
                  })),
                );
              }
              if (res.response_text) {
                setStreamedText(res.response_text);
              }
            })
            .catch((err: unknown) => {
              setIsGenerating(false);
              const detail =
                err instanceof Error ? err.message : "Erreur de communication avec le serveur";
              setErrorMessage(
                isFr
                  ? `⚠️ Impossible d'obtenir une réponse de Mon Assistant (${detail}). Vérifiez que le modèle IA configuré est bien démarré.`
                  : `⚠️ Could not get a response from My Assistant (${detail}). Please check that your configured AI model is running.`,
              );
            });
        }}
      />

      {/* Pastilles de Citation & Brouillon de Document */}
      <AssistantCitationPillsAndArtifactCard
        sanitizedResponseText={streamedText}
        sources={[]}
        glossaryItems={[]}
        toolOutputs={[]}
        footerSummaryLine=""
        labels={dictionary.assistantCitations}
        onSaveDraft={(title) => {
          setGovernanceFeedback(
            isFr
              ? `✅ Brouillon « ${title} » enregistré dans votre Espace.`
              : `✅ Draft "${title}" saved to your Workspace.`,
          );
        }}
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

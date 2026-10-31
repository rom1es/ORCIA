import {
  AssistantCitationPillsAndArtifactCard,
  AssistantFoldersAndCollaborativeThreadView,
  AssistantGovernanceModalAndStudio,
  AssistantSpeedSelectorAndStreamView,
  StatusBadge,
  type AssistantFolderVisibilityMode,
  type UiAssembledLayerItem,
  type UiAssistantFolderItem,
  type UiAssistantStudioNode,
  type UiEvidenceSourceItem,
} from "@orcia/ui";
import React, { useState } from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

const DEFAULT_FOLDERS: readonly UiAssistantFolderItem[] = [
  {
    folderId: "folder-payment-142",
    title: "PAY-142 · Exemption 3DS Frictionless TRA",
    pinnedNotesMarkdown:
      "Hypothèse structurante : Plafond TRA de 250 € sur les flux récurrents SEPA.",
    consolidatedSummary:
      "Analyse des règles PSD2 et de la chaîne causale ADN N1 -> N2 -> N3.",
    visibilityMode: "WORKSPACE_OPEN",
    hasRestrictedSources: true,
    assembledLayer5PromptBlock:
      "## Continuité Dossier PAY-142\nRespecter l'axiome PSD2 et l'isolation hexagonale AD-19.",
  },
  {
    folderId: "folder-arch-adr",
    title: "ADR-019 · Isolation Modulaire & Outbox",
    pinnedNotesMarkdown: "Zéro import transversal entre domaines orcia_core.",
    consolidatedSummary: "Revue des contrats lint-imports et du bus transactionnel PG18.",
    visibilityMode: "PRIVATE",
    hasRestrictedSources: false,
    assembledLayer5PromptBlock: "## Continuité Dossier ADR-019\nContrat 1 à 5 lint-imports.",
  },
];

const DEFAULT_EVIDENCE_SOURCES: readonly UiEvidenceSourceItem[] = [
  {
    tag: "S1",
    index: 1,
    uri: "confluence://ARCHI/psd2-tra-policy@v14",
    title: "Directive Entreprise PSD2 & Plafonds TRA (Référence)",
    authorityTier: "REFERENCE",
    freshness: "FRESH",
    snippet: "Les transactions sous 250 € avec score de risque < 0.12 bénéficient de l'exemption TRA.",
    lineStart: 12,
    lineEnd: 28,
    restrictedAccess: false,
    displayPill: "[S1 · Directive PSD2 TRA]",
  },
  {
    tag: "S2",
    index: 2,
    uri: "git://secops/fraud-scoring-rules@sha256:9b1c4e",
    title: "Matrice SecOps de Scoring Fraude (Source restreinte)",
    authorityTier: "ACTIVE",
    freshness: "FRESH",
    snippet: null,
    lineStart: 40,
    lineEnd: 75,
    restrictedAccess: true,
    displayPill: "[S2 · 🔒 Source restreinte — Demander l'accès]",
  },
];

const DEFAULT_ASSEMBLED_LAYERS: readonly UiAssembledLayerItem[] = [
  {
    layerNumber: 1,
    layerCode: "1_CONSTITUTION",
    label: "1. Constitution & Bornes AssistantHarness (AD-15)",
    immutable: true,
    originBadge: "SOCLE",
    content: "Passthrough strict, citations [S1]/[G1]/[O1] obligatoires, Verrou V5 sans écriture directe SI.",
    sha256: "sha256-layer-1",
  },
  {
    layerNumber: 2,
    layerCode: "2_PACK_METIER",
    label: "2. Pack Métier (orcia-pack-sdlc@1.0.0)",
    immutable: false,
    originBadge: "PACK",
    content: "Casquette Analyste / Tech Lead : structurer les réponses avec impacts SI et FinOps.",
    sha256: "sha256-layer-2",
  },
  {
    layerNumber: 4,
    layerCode: "4_ESPACE",
    label: "4. Espace Solution (Couche 4 — WORKSPACE)",
    immutable: false,
    originBadge: "ESPACE",
    content: "Prioriser les sources REFERENCE sur les brouillons ACTIVE.",
    sha256: "sha256-layer-4",
  },
  {
    layerNumber: 5,
    layerCode: "5_UTILISATEUR",
    label: "5. Préférences & Continuité Dossier (Couche 5 — USER)",
    immutable: false,
    originBadge: "UTILISATEUR",
    content: "Format structuré par sections avec extraits vérifiés.",
    sha256: "sha256-layer-5",
  },
];

const DEFAULT_STUDIO_NODES: readonly UiAssistantStudioNode[] = [
  {
    nodeId: "node-1-auth-guard",
    title: "1. Auth & PermissionGuard (🔒 AssistantHarness)",
    nodeOrder: 1,
    isHarnessBoundary: true,
    lockedBy: "HARNESS",
    enabled: true,
    subLayersCount: 2,
  },
  {
    nodeId: "node-2-context-rag",
    title: "2. Assemblage 5 Couches & RAG Hybride (REFERENCE > ACTIVE)",
    nodeOrder: 2,
    isHarnessBoundary: false,
    lockedBy: null,
    enabled: true,
    subLayersCount: 5,
  },
  {
    nodeId: "node-5-citation-verifier",
    title: "5. Vérificateur Déterministe [S1]/[G1]/[O1] & Verrou V5 (🔒 AssistantHarness)",
    nodeOrder: 3,
    isHarnessBoundary: true,
    lockedBy: "HARNESS",
    enabled: true,
    subLayersCount: 3,
  },
];

export function InboxFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const copy = dictionary.modulePages.inbox;
  const inboxCopy = dictionary.inboxAndClaims;
  const isFr = locale === "fr";

  const [scopeFilter, setScopeFilter] = useState<"ALL" | "PERSONAL" | "TEAM">("ALL");
  const [folders, setFolders] = useState<readonly UiAssistantFolderItem[]>(DEFAULT_FOLDERS);
  const [activeFolderId, setActiveFolderId] = useState<string>("folder-payment-142");
  const [governanceOpen, setGovernanceOpen] = useState<boolean>(false);
  const [streamedText, setStreamedText] = useState<string>(
    "D'après la directive PSD2 [S1] et l'axiome [G1], le flux SEPA sous 250 € est éligible au parcours Frictionless TRA. La matrice de fraude [S2] requiert une habilitation SecOps complémentaire.",
  );

  return (
    <div className="space-y-4" data-testid="inbox-feature-panel">
      {/* En-tête Mon Assistant + Bouton Gouvernance 4 Niveaux (Story 10.1) */}
      <div className="orcia-bento-card flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="font-semibold">{copy.subtitle}</span>
          <p className="text-xs text-text-secondary mt-0.5">{copy.description}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge
            testId="inbox-amber-counter"
            label={`${inboxCopy.amberCounterPrefix} 0`}
            tone="amber"
            pill
          />
          <StatusBadge
            testId="inbox-uri-badge"
            label={copy.uriBadgeExample}
            tone="cobalt"
            monospace
          />
          <button
            type="button"
            data-testid="assistant-open-governance-btn"
            onClick={() => setGovernanceOpen((prev) => !prev)}
            className="rounded border border-border-subtle bg-surface-elevated px-3 py-1 text-xs font-semibold text-text-primary"
          >
            {dictionary.assistantGovernance.modalTitle}
          </button>
        </div>
      </div>

      {/* Modale Gouvernance 4 Niveaux Mode A & Studio Mode B (Story 10.1) */}
      {governanceOpen ? (
        <AssistantGovernanceModalAndStudio
          workspaceId="ws-default"
          canEditWorkspaceLayer={true}
          canOpenStudioModeB={true}
          assembledLayers={DEFAULT_ASSEMBLED_LAYERS}
          studioNodes={DEFAULT_STUDIO_NODES}
          labels={dictionary.assistantGovernance}
        />
      ) : null}

      {/* Dossiers Thématiques 📁, Continuité Couche 5 & Partage Collaboratif (Story 10.4) */}
      <AssistantFoldersAndCollaborativeThreadView
        workspaceId="ws-default"
        activeFolderId={activeFolderId}
        folders={folders}
        historyHits={[
          {
            itemId: "hit-1",
            itemKind: "THREAD",
            title: "Analyse d'éligibilité TRA 250 €",
            snippet: "Vérification des plafonds PSD2 [S1] et du glossaire [G1].",
          },
          {
            itemId: "hit-2",
            itemKind: "ARTIFACT_CARD",
            title: "Brouillon Spécification Technique PAY-142",
            snippet: "Carte d'artefact prête pour le processus ticket-to-tech-spec.",
          },
        ]}
        currentAuthorPassthroughIdentity="operateur@orcia.io (Passthrough)"
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

      {/* Sélecteur Conversationnel à 3 Vitesses & Cache Redis < 5 ms (Story 10.2) */}
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-default"
        userId="usr-admin-1"
        hat="ANALYST_PM_PO"
        cacheHit={true}
        cacheLookupMs={1.2}
        nodes1To4DeterministicMs={16.4}
        ttftMs={380.0}
        stepProgress={[
          {
            stepCode: "NODE_1_4_DETERMINISTIC",
            label: "Nœuds 1..4 : Auth + Cache 5 Couches + RAG Hybride + Table des Preuves",
            durationMs: 16.4,
            status: "COMPLETED",
          },
          {
            stepCode: "NODE_5_VERIFIER",
            label: "Nœud 5 : Vérificateur déterministe des citations [S1]/[G1]/[O1] (< 5 ms)",
            durationMs: 1.8,
            status: "COMPLETED",
          },
        ]}
        streamedText={streamedText}
        labels={dictionary.assistantSpeedStream}
        onSendTurn={({ userPrompt, requestedSpeed }) => {
          setStreamedText(
            `[${requestedSpeed}] Réponse vérifiée pour « ${userPrompt} » selon [S1] et [G1].`,
          );
        }}
      />

      {/* Pastilles de Citation Déterministes [S1]/[G1]/[O1] & Carte d'Artefact Verrou V5 (Story 10.3) */}
      <AssistantCitationPillsAndArtifactCard
        sanitizedResponseText={streamedText}
        sources={DEFAULT_EVIDENCE_SOURCES}
        glossaryItems={[
          {
            tag: "G1",
            label: "Exemption 3DS Frictionless TRA",
            ontologyLevel: "N2_NORME",
            definition: "Dérogation d'authentification forte sous seuil d'analyse de risque temps réel.",
          },
        ]}
        toolOutputs={[
          {
            tag: "O1",
            toolName: "jira.get_issue",
            connectorUri: "jira://PAY/PAY-142",
            summary: "Statut : IN_ANALYSIS · Priorité : P1",
          },
        ]}
        footerSummaryLine="📚 2 sources (1 REFERENCE, 1 🔒 restreinte) · 1 terme du glossaire [G1] · 1 outil [O1]"
        artifactTitle="Spécification Technique — Exemption TRA PAY-142"
        artifactContent="## 1. Contexte & Règle PSD2 [S1]\nApplication du plafond de 250 € sous réserve du score de risque."
        labels={dictionary.assistantCitations}
        onContinueInProcess={() => navigateToRoute("/processes")}
      />

      {/* Boîte de notifications et filtres de périmètre (compatibilité ascendante) */}
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
                ? "Aucune notification ni demande d'arbitrage en attente"
                : "No pending notification or arbitration request"}
            </strong>
            <p
              style={{
                margin: "4px 0 0 0",
                fontSize: "13px",
                color: "var(--color-muted-foreground)",
              }}
            >
              {isFr
                ? "Les tâches d'arbitrage humain, signatures d'ancrage et Gates adaptatives apparaîtront ici lorsqu'un Workflow Run les déclenchera."
                : "Human arbitration tasks, anchor signatures, and adaptive Gates will appear here when triggered by an active Workflow Run."}
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

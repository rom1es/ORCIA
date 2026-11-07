import React, { useRef, useState } from "react";

export interface UiAssistantAutocompleteOption {
  readonly slug: string;
  readonly label: string;
  readonly description: string;
  readonly kind: "agent" | "skill";
}

export interface UiAssistantOrciaDocumentOption {
  readonly id: string;
  readonly title: string;
  readonly uri: string;
}

export interface UiAssistantAttachedFileItem {
  readonly id: string;
  readonly name: string;
  readonly sourceKind: "LOCAL_PC" | "ORCIA_WORKSPACE";
  readonly uri?: string;
}

export const DEFAULT_ASSISTANT_AGENT_OPTIONS: readonly UiAssistantAutocompleteOption[] = [
  { slug: "analyste-metier", label: "Analyste Métier", description: "Analyse des besoins, règles de gestion et cas d'usage", kind: "agent" },
  { slug: "architecte-solution", label: "Architecte Solution", description: "Conception technique, modèles de données et intégration", kind: "agent" },
  { slug: "reviseur-conformite", label: "Réviseur Conformité & Qualité", description: "Vérification des exigences, normes et points d'attention", kind: "agent" },
  { slug: "redacteur-technique", label: "Rédacteur Technique", description: "Structuration claire de livrables, guides et synthèses", kind: "agent" },
  { slug: "expert-securite", label: "Expert Sécurité", description: "Analyse des risques de sécurité et protection des données", kind: "agent" },
];

export const DEFAULT_ASSISTANT_SKILL_OPTIONS: readonly UiAssistantAutocompleteOption[] = [
  { slug: "synthese-executive", label: "Synthèse Exécutive", description: "Résumé structuré des points clés et décisions attendues", kind: "skill" },
  { slug: "analyse-risques", label: "Analyse des Risques", description: "Identification des risques, impacts et mesures de maîtrise", kind: "skill" },
  { slug: "revue-code", label: "Revue de Code & Qualité", description: "Inspection de la lisibilité, de la sécurité et des tests", kind: "skill" },
  { slug: "extraction-exigences", label: "Extraction d'Exigences", description: "Transformation de notes ou documents en critères vérifiables", kind: "skill" },
  { slug: "comparaison-versions", label: "Comparaison de Versions", description: "Mise en évidence des écarts entre deux documents ou normes", kind: "skill" },
];

export const DEFAULT_ORCIA_DOCUMENT_OPTIONS: readonly UiAssistantOrciaDocumentOption[] = [
  { id: "orcia-doc-1", title: "Référentiel Métier & Règles de l'Espace", uri: "https://docs.orcia.local/espaces/referentiel-metier" },
  { id: "orcia-doc-2", title: "Guide d'Architecture & Bonnes Pratiques", uri: "https://docs.orcia.local/espaces/guide-architecture" },
];

export function detectActiveAutocompleteTrigger(promptText: string): {
  readonly kind: "agent" | "skill";
  readonly query: string;
  readonly tokenStartIndex: number;
} | null {
  const match = /(?:^|\s)([@/])([a-zA-Z0-9_-]*)$/.exec(promptText);
  if (!match) {
    return null;
  }
  const symbol = match[1];
  const query = match[2] ?? "";
  const fullMatch = match[0];
  const leadingSpaceOffset = fullMatch.startsWith(" ") ? 1 : 0;
  const tokenStartIndex = match.index + leadingSpaceOffset;
  return {
    kind: symbol === "@" ? "agent" : "skill",
    query,
    tokenStartIndex,
  };
}

export function applyAutocompleteSelectionToPrompt(
  promptText: string,
  option: UiAssistantAutocompleteOption,
): string {
  const prefix = option.kind === "agent" ? `@${option.slug}` : `/${option.slug}`;
  const active = detectActiveAutocompleteTrigger(promptText);
  const stripped =
    active !== null
      ? `${promptText.slice(0, active.tokenStartIndex)}${promptText.slice(
          active.tokenStartIndex + 1 + active.query.length,
        )}`.trim()
      : promptText.trim();
  if (stripped.startsWith(`${prefix} `) || stripped === prefix) {
    return `${stripped} `;
  }
  return stripped ? `${prefix} ${stripped} ` : `${prefix} `;
}

export interface AssistantAttachedFilesInlineBarProps {
  readonly attachedFiles: readonly UiAssistantAttachedFileItem[];
  readonly onRemoveAttachedFile: (fileId: string) => void;
}

export function AssistantAttachedFilesInlineBar({
  attachedFiles,
  onRemoveAttachedFile,
}: AssistantAttachedFilesInlineBarProps): React.JSX.Element | null {
  if (attachedFiles.length === 0) {
    return null;
  }
  return (
    <div
      data-testid="assistant-attached-files-bar"
      className="flex flex-wrap items-center gap-1.5"
    >
      {attachedFiles.map((file) => (
        <span
          key={file.id}
          data-testid="assistant-attached-file-pill"
          className="inline-flex items-center gap-1.5 rounded-md bg-surface-secondary px-2 py-0.5 text-[11px] font-medium text-text-primary"
        >
          <span aria-hidden="true">
            {file.sourceKind === "LOCAL_PC" ? "💻" : "🗂️"}
          </span>
          <span>{file.name}</span>
          <button
            type="button"
            aria-label={`Retirer ${file.name}`}
            title={`Retirer ${file.name}`}
            onClick={() => onRemoveAttachedFile(file.id)}
            className="border-0 bg-transparent p-0.5 text-text-secondary hover:text-text-primary leading-none"
          >
            ×
          </button>
        </span>
      ))}
    </div>
  );
}

export interface AssistantPromptPlusAndAutocompleteProps {
  readonly plusMenuOpen: boolean;
  readonly autocompleteTrigger: {
    readonly kind: "agent" | "skill";
    readonly query: string;
  } | null;
  readonly agentOptions?: readonly UiAssistantAutocompleteOption[];
  readonly skillOptions?: readonly UiAssistantAutocompleteOption[];
  readonly orciaDocuments?: readonly UiAssistantOrciaDocumentOption[];
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly onSelectAutocompleteOption: (option: UiAssistantAutocompleteOption) => void;
  readonly onTriggerAgentAutocompleteFromPlus: () => void;
  readonly onTriggerSkillAutocompleteFromPlus: () => void;
  readonly onAttachFile: (file: UiAssistantAttachedFileItem) => void;
  readonly onRemoveAttachedFile?: (fileId: string) => void;
  readonly onOpenFoldersAndCloseMenus?: () => void;
}

export function AssistantPromptPlusAndAutocomplete({
  plusMenuOpen,
  autocompleteTrigger,
  agentOptions = DEFAULT_ASSISTANT_AGENT_OPTIONS,
  skillOptions = DEFAULT_ASSISTANT_SKILL_OPTIONS,
  orciaDocuments = DEFAULT_ORCIA_DOCUMENT_OPTIONS,
  onSelectAutocompleteOption,
  onTriggerAgentAutocompleteFromPlus,
  onTriggerSkillAutocompleteFromPlus,
  onAttachFile,
  onOpenFoldersAndCloseMenus,
}: AssistantPromptPlusAndAutocompleteProps): React.JSX.Element {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [orciaDocsSubmenuOpen, setOrciaDocsSubmenuOpen] = useState<boolean>(false);

  const filteredOptions =
    autocompleteTrigger === null
      ? []
      : (autocompleteTrigger.kind === "agent" ? agentOptions : skillOptions).filter(
          (opt) => {
            const q = autocompleteTrigger.query.toLowerCase();
            return !q || opt.slug.toLowerCase().includes(q) || opt.label.toLowerCase().includes(q);
          },
        );

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        data-testid="assistant-local-file-input"
        style={{ display: "none" }}
        onChange={(e) => {
          const picked = e.target.files?.[0];
          if (picked) {
            onAttachFile({
              id: `local-${Date.now()}-${picked.name}`,
              name: picked.name,
              sourceKind: "LOCAL_PC",
              uri: `#local-file-${encodeURIComponent(picked.name)}`,
            });
          }
          e.target.value = "";
        }}
      />

      {autocompleteTrigger !== null && filteredOptions.length > 0 && (
        <div
          data-testid="assistant-autocomplete-dropdown"
          data-trigger-kind={autocompleteTrigger.kind}
          role="listbox"
          style={{ position: "absolute", bottom: "calc(100% + 8px)", left: 0, zIndex: 45, minWidth: "300px" }}
          className="rounded-xl border border-border-subtle bg-surface-primary p-2 text-xs shadow-lg space-y-1"
        >
          <div className="px-2 py-1 text-[11px] font-semibold text-text-secondary border-b border-border-subtle">
            {autocompleteTrigger.kind === "agent"
              ? "🤖 Sélectionner un agent (@) — Entrée ou clic pour valider"
              : "🛠️ Sélectionner une compétence (/) — Entrée ou clic pour valider"}
          </div>
          {filteredOptions.map((opt, idx) => (
            <button
              key={`${opt.kind}-${opt.slug}`}
              type="button"
              role="option"
              aria-selected={idx === 0}
              data-testid={`assistant-autocomplete-option-${opt.slug}`}
              onClick={() => onSelectAutocompleteOption(opt)}
              className={`flex w-full flex-col items-start rounded-lg px-2.5 py-1.5 text-left hover:bg-surface-secondary ${
                idx === 0 ? "bg-surface-secondary/70" : ""
              }`}
            >
              <span className="font-semibold text-text-primary">
                {opt.kind === "agent" ? `@${opt.slug}` : `/${opt.slug}`} — {opt.label}
              </span>
              <span className="text-[11px] text-text-secondary">{opt.description}</span>
            </button>
          ))}
        </div>
      )}

      {plusMenuOpen && (
        <div
          data-testid="assistant-prompt-plus-popover"
          role="menu"
          style={{ position: "absolute", bottom: "calc(100% + 8px)", left: 0, zIndex: 40, minWidth: "290px" }}
          className="flex flex-col gap-1 rounded-xl border border-border-subtle bg-surface-primary p-2 text-xs shadow-lg"
        >
          <button
            type="button"
            role="menuitem"
            data-testid="assistant-plus-insert-agent-btn"
            onClick={() => { setOrciaDocsSubmenuOpen(false); onTriggerAgentAutocompleteFromPlus(); }}
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
          >
            <span>@ Mentionner un agent</span>
          </button>

          <button
            type="button"
            role="menuitem"
            data-testid="assistant-plus-insert-skill-btn"
            onClick={() => { setOrciaDocsSubmenuOpen(false); onTriggerSkillAutocompleteFromPlus(); }}
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
          >
            <span>/ Utiliser une compétence</span>
          </button>

          <button
            type="button"
            role="menuitem"
            data-testid="assistant-plus-upload-local-file-btn"
            onClick={() => { setOrciaDocsSubmenuOpen(false); fileInputRef.current?.click(); }}
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
          >
            <span>💻 Ajouter un fichier depuis mon ordinateur</span>
          </button>

          <button
            type="button"
            role="menuitem"
            data-testid="assistant-plus-attach-orcia-doc-btn"
            onClick={() => setOrciaDocsSubmenuOpen((prev) => !prev)}
            className="flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
          >
            <span>🗂️ Ajouter un document disponible dans ORCIA</span>
            <span aria-hidden="true">▸</span>
          </button>

          {orciaDocsSubmenuOpen && (
            <div data-testid="assistant-plus-orcia-docs-submenu" className="ml-2 space-y-1 border-l border-border-subtle pl-2 py-1">
              {orciaDocuments.map((doc) => (
                <button
                  key={doc.id}
                  type="button"
                  data-testid={`assistant-orcia-doc-option-${doc.id}`}
                  onClick={() => {
                    onAttachFile({ id: `orcia-${doc.id}`, name: doc.title, sourceKind: "ORCIA_WORKSPACE", uri: doc.uri });
                    setOrciaDocsSubmenuOpen(false);
                  }}
                  className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-[11px] text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                >
                  <span>📄 {doc.title}</span>
                </button>
              ))}
            </div>
          )}

          {onOpenFoldersAndCloseMenus && (
            <button
              type="button"
              role="menuitem"
              data-testid="assistant-plus-open-folders-btn"
              onClick={() => { setOrciaDocsSubmenuOpen(false); onOpenFoldersAndCloseMenus(); }}
              className="flex w-full items-center gap-2 rounded-lg border-t border-border-subtle pt-2 mt-1 px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
            >
              <span>📁 Gérer les dossiers thématiques</span>
            </button>
          )}
        </div>
      )}
    </>
  );
}

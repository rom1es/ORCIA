// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AssistantPromptPlusAndAutocomplete,
  EntityUnlinkConfirmDialog,
  PackComposerModal,
  PackSlotBindingDrawer,
  type EntityUnlinkConfirmDialogLabels,
  type PackComposerModalLabels,
  type PackSlotBindingDrawerLabels,
  type UiWorkspacePackItem,
} from "../index";
import { mergeAssistantAutocompleteOptions } from "../primitives/AssistantStickyFooterBadges";

afterEach(() => {
  cleanup();
});

const SLOT_DRAWER_LABELS: PackSlotBindingDrawerLabels = {
  drawerTitlePrefix: "Connector Slot Bindings",
  drawerDescription: "Bind required slots",
  closeLabel: "Close",
  requiredBadge: "Required",
  optionalBadge: "Optional",
  readyBadge: "Ready",
  missingBadge: "Unbound",
  optionalUnboundBadge: "Optional unbound",
  targetSelectLabel: "Bound target",
  unboundOptionLabel: "— Unbound —",
  missingSlotsAlertTitle: "Missing required slots",
  noSlotsMessage: "No slots",
  saveBtn: "Save bindings",
  savingBtn: "Saving...",
  cancelBtn: "Cancel",
  observerBlockedHint: "Read-only mode",
};

const COMPOSER_LABELS: PackComposerModalLabels = {
  createTitle: "Compose Custom Pack",
  editTitle: "Edit Custom Pack",
  closeLabel: "Close",
  stepMetadataTab: "1. Metadata",
  stepMembersTab: "2. Members",
  slugLabel: "Slug",
  nameLabel: "Name",
  versionLabel: "Version",
  descriptionLabel: "Description",
  authorLabel: "Author",
  licenseLabel: "License",
  scopeTypeLabel: "Scope",
  scopeTargetLabel: "Target",
  scopeBuLabel: "Business Unit",
  scopeTeamLabel: "Team",
  scopeWorkspaceLabel: "Workspace",
  membersSearchPlaceholder: "Filter members",
  membersEmptyHint: "No members",
  closureCompleteBadge: "Complete",
  closureIncompleteBadge: "Incomplete",
  missingDependenciesTitle: "Missing dependencies:",
  proseWarningsTitle: "Prose warnings:",
  autoIncludeDependenciesLabel: "Auto-include dependencies",
  saveDraftBtn: "Save draft",
  publishBtn: "Publish",
  exportZipBtn: "Export (.zip)",
  savingBtn: "Saving...",
  entityTypeLabels: {
    AGENT: "Agent",
    SKILL: "Skill",
    INSTRUCTION: "Instruction",
    WORKFLOW_V2: "Process",
    VSM_V2: "Value stream",
    ONTOLOGY_CONCEPT: "Concept",
    ONTOLOGY_RELATION: "Relation",
    ONTOLOGY_AXIOM: "Axiom",
    DNA_MECHANISM: "Rule",
    POLICY: "Policy",
    HELP_ARTICLE: "Help",
  },
};

const UNLINK_LABELS: EntityUnlinkConfirmDialogLabels = {
  title: "Item referenced by draft packs",
  descriptionPrefix: "Confirm unlinking:",
  referencingDraftsHeading: "Draft packs:",
  confirmBtn: "Detach and delete",
  confirmingBtn: "Deleting...",
  cancelBtn: "Cancel",
};

describe("Story 31.6 — @orcia/ui Pack Drawer, Composer, Unlink Dialog & Qualified Badges", () => {
  it("renders PackSlotBindingDrawer with missing required slot alert, optional_unbound badge, and saves selection", () => {
    const onSave = vi.fn();
    const pack: UiWorkspacePackItem = {
      bundleId: "b-1",
      packId: "orcia-pack-sdlc",
      slug: "sdlc",
      name: "SDLC Pack",
      version: "1.0.0",
      bundleKind: "SYSTEM",
      scopeType: "GLOBAL",
      scopeId: "global",
      status: "PUBLISHED",
      archiveSha256: "a".repeat(64),
      description: "SDLC",
      isActive: false,
      priorityOrder: null,
      declaredSlots: [
        { slotKey: "git_repo", scheme: "git", connectorKind: "mcp:git", sourceNature: "SOURCE_CODE", required: true, description: "Primary Git" },
        { slotKey: "wiki_space", scheme: "confluence", connectorKind: "mcp:confluence", sourceNature: "DOCUMENTATION", required: false, description: "Optional Wiki" },
      ],
      slotBindings: [],
      missingSlots: ["git_repo"],
      readinessOk: false,
    };

    render(
      <PackSlotBindingDrawer
        open={true}
        pack={pack}
        candidates={[
          { targetKind: "WORKSPACE_DATASOURCE", targetId: "ds-git-1", label: "Core Repo", scheme: "git", uri: "git://core" },
        ]}
        highlightedMissingSlots={["git_repo"]}
        errorMessage="Required slot unbound [ERR_PACK_SLOT_UNBOUND]"
        labels={SLOT_DRAWER_LABELS}
        onOpenChange={() => {}}
        onSaveBindings={onSave}
      />,
    );

    expect(screen.getByTestId("pack-slot-drawer-error-alert").getAttribute("role")).toBe("alert");
    expect(screen.getByTestId("pack-slot-row-git_repo").getAttribute("data-slot-missing")).toBe("true");
    expect(screen.getByTestId("pack-slot-optional-unbound-wiki_space")).toBeDefined();

    fireEvent.change(screen.getByTestId("pack-slot-select-git_repo"), {
      target: { value: "WORKSPACE_DATASOURCE::ds-git-1" },
    });
    fireEvent.click(screen.getByTestId("save-pack-slot-bindings-btn"));

    expect(onSave).toHaveBeenCalledWith(pack, [
      { slotKey: "git_repo", targetKind: "WORKSPACE_DATASOURCE", targetId: "ds-git-1", connectorScheme: "git" },
      { slotKey: "wiki_space", targetKind: "UNBOUND", targetId: null, connectorScheme: "confluence" },
    ]);
  });

  it("renders PackComposerModal closure gaps, auto_include_dependencies, and EntityUnlinkConfirmDialog", () => {
    const onPublish = vi.fn();
    const onConfirmUnlink = vi.fn();
    render(
      <>
        <PackComposerModal
          open={true}
          draft={{
            bundleId: "d-1",
            slug: "custom-pack",
            name: "Custom Pack",
            version: "0.1.0",
            description: "Custom",
            author: "Karim",
            license: "Apache-2.0",
            scopeType: "WORKSPACE",
            scopeId: "ws-1",
            status: "DRAFT",
            members: [],
            closureComplete: false,
            missingDependencies: [{ entityType: "SKILL", entityId: "sk-1", reason: "not included", referencedBy: "ag-1" }],
            nonActiveDependencies: [],
            proseWarnings: [],
          }}
          availableMembers={[
            { entityType: "AGENT", entityId: "ag-1", entitySlug: "architect", title: "Architect", lifecycleStatus: "ACTIVE" },
          ]}
          scopeOptions={[{ id: "ws-1", label: "Workspace Alpha", scopeType: "WORKSPACE" }]}
          errorMessage="Closure incomplete [ERR_PACK_CLOSURE_INCOMPLETE]"
          labels={COMPOSER_LABELS}
          onOpenChange={() => {}}
          onSaveDraft={() => {}}
          onPublishDraft={onPublish}
          onExportDraftZip={() => {}}
        />
        <EntityUnlinkConfirmDialog
          open={true}
          entityLabel="Architect"
          draftPacks={[{ bundleId: "d-1", slug: "custom-pack", name: "Custom Pack", version: "0.1.0" }]}
          labels={UNLINK_LABELS}
          onCancel={() => {}}
          onConfirmUnlinkAndDelete={onConfirmUnlink}
        />
      </>,
    );

    expect(screen.getByTestId("pack-composer-error-alert").getAttribute("role")).toBe("alert");
    expect(screen.getByTestId("pack-composer-closure-gaps").textContent).toContain("SKILL:sk-1");
    fireEvent.click(screen.getByTestId("pack-composer-auto-include-checkbox"));
    fireEvent.click(screen.getByTestId("pack-composer-publish-btn"));
    expect(onPublish).toHaveBeenCalledWith("d-1", true);

    expect(screen.getByTestId("entity-unlink-draft-packs-list").textContent).toContain("Custom Pack");
    fireEvent.click(screen.getByTestId("entity-unlink-confirm-btn"));
    expect(onConfirmUnlink).toHaveBeenCalledTimes(1);
  });

  it("preserves and renders origin pack attribution badges in @ / autocomplete dropdown", () => {
    const merged = mergeAssistantAutocompleteOptions(
      [
        { id: "a1", kind: "agent", token: "@sdlc/reviewer", name: "SDLC Reviewer", description: "SDLC", badge: "sdlc" },
        { id: "a2", kind: "agent", token: "@legal/reviewer", name: "Legal Reviewer", description: "Legal", badge: "legal" },
      ],
      [],
      [],
    );
    const onSelect = vi.fn();
    render(
      <AssistantPromptPlusAndAutocomplete
        plusMenuOpen={false}
        autocompleteTrigger={{ kind: "agent", query: "rev" }}
        agentOptions={merged.mergedAgentOptions}
        skillOptions={merged.mergedSkillOptions}
        labels={{
          removeFilePrefix: "Remove",
          selectAgentHeading: "Agents",
          selectSkillHeading: "Skills",
          plusInsertAgentLabel: "@ Agent",
          plusInsertSkillLabel: "/ Skill",
          plusUploadLocalFileLabel: "Upload",
          plusAttachOrciaDocLabel: "Attach",
          plusOpenFoldersLabel: "Folders",
        }}
        onSelectAutocompleteOption={onSelect}
        onTriggerAgentAutocompleteFromPlus={() => {}}
        onTriggerSkillAutocompleteFromPlus={() => {}}
        onAttachFile={() => {}}
      />,
    );

    expect(screen.getByTestId("assistant-autocomplete-badge-sdlc/reviewer").textContent).toBe("sdlc");
    expect(screen.getByTestId("assistant-autocomplete-badge-legal/reviewer").textContent).toBe("legal");
    fireEvent.click(screen.getByTestId("assistant-autocomplete-option-sdlc/reviewer"));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ slug: "sdlc/reviewer", badge: "sdlc" }));
  });
});

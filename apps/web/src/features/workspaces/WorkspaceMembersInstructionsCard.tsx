import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";
import React, { useState } from "react";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../i18n";

export interface WorkspaceMembersInstructionsCardProps {
  readonly isFr: boolean;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function WorkspaceMembersInstructionsCard({
  isFr,
  activeWorkspace,
}: WorkspaceMembersInstructionsCardProps): React.ReactElement {
  const tabsCopy = resolveDictionaryForFlag(isFr).featureWorkspaces.detailTabs;
  const [instructionsByWs, setInstructionsByWs] = useState<Record<string, string>>({});
  const [instructionsSavedWsId, setInstructionsSavedWsId] = useState<string | null>(null);

  return (
    <div
      data-testid="workspace-detail-members-content"
      style={{ display: "flex", flexDirection: "column", gap: "10px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div>
          <strong style={{ fontSize: "13px" }}>
            {formatI18nTemplate(tabsCopy.ownerTeamTemplate, {
              owner: activeWorkspace.ownerOrgUnitName ?? tabsCopy.defaultPlatformOwnerName,
            })}
          </strong>
          <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            {tabsCopy.instructionsHint}
          </p>
        </div>
        {instructionsSavedWsId === activeWorkspace.workspaceId && (
          <span
            data-testid="workspace-instructions-saved-badge"
            style={{
              fontSize: "11px",
              fontWeight: 700,
              padding: "3px 8px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-action-primary-subtle)",
              color: "var(--color-status-success)",
            }}
          >
            {tabsCopy.savedBadge}
          </span>
        )}
      </div>
      <textarea
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        data-testid="workspace-instructions-textarea"
        rows={3}
        value={instructionsByWs[activeWorkspace.workspaceId] ?? ""}
        onChange={(e) => {
          const val = e.target.value;
          setInstructionsByWs((prev) => ({ ...prev, [activeWorkspace.workspaceId]: val }));
          setInstructionsSavedWsId(activeWorkspace.workspaceId);
        }}
        placeholder={tabsCopy.instructionsPlaceholder}
        style={{ ...inputStyle, width: "100%", fontFamily: "var(--font-sans)" }}
      />
    </div>
  );
}

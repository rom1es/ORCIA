import type { RoleMatrixEntryResponse } from "@orcia/api-client";
import {
  OrciaAlertBanner,
  StatusBadge,
  type UiPermissionVerb,
} from "@orcia/ui";
import React from "react";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";
import { OFFICIAL_IAM_ROLES, type OfficialIamRoleKey } from "./iamApiBridge";

export interface IamNativeRoleMatrixCardProps {
  readonly roleMatrix: readonly RoleMatrixEntryResponse[];
  readonly labels: IamTabDictionarySection;
  readonly openHelpSection: (sectionId: string) => void;
}

interface FallbackMatrixRow {
  readonly role: OfficialIamRoleKey;
  readonly naturalScope: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  readonly workflowsVerbs: readonly UiPermissionVerb[];
  readonly connectorsVerbs: readonly UiPermissionVerb[];
  readonly orgIamVerbs: readonly UiPermissionVerb[];
}

const DEFAULT_FALLBACK_ROWS: readonly FallbackMatrixRow[] = [
  {
    role: "PLATFORM_ADMIN",
    naturalScope: "GLOBAL",
    workflowsVerbs: ["create", "read", "update", "delete", "execute"],
    connectorsVerbs: ["create", "read", "update", "delete", "execute"],
    orgIamVerbs: ["create", "read", "update", "delete", "grant"],
  },
  {
    role: "SECOPS",
    naturalScope: "GLOBAL",
    workflowsVerbs: ["read"],
    connectorsVerbs: ["read", "update"],
    orgIamVerbs: ["read", "update", "grant"],
  },
  {
    role: "BU_LEAD",
    naturalScope: "BU",
    workflowsVerbs: ["create", "read", "update", "execute"],
    connectorsVerbs: ["create", "read", "update", "execute"],
    orgIamVerbs: ["create", "read", "update", "grant"],
  },
  {
    role: "TEAM_LEAD",
    naturalScope: "TEAM",
    workflowsVerbs: ["create", "read", "update", "execute"],
    connectorsVerbs: ["read", "update", "execute"],
    orgIamVerbs: ["read", "update", "grant"],
  },
  {
    role: "ONTOLOGY_LEAD",
    naturalScope: "BU",
    workflowsVerbs: ["read"],
    connectorsVerbs: ["read"],
    orgIamVerbs: ["read"],
  },
  {
    role: "CONTRIBUTOR",
    naturalScope: "WORKSPACE",
    workflowsVerbs: ["create", "read", "update", "execute"],
    connectorsVerbs: ["read", "execute"],
    orgIamVerbs: ["read"],
  },
  {
    role: "OBSERVER",
    naturalScope: "WORKSPACE",
    workflowsVerbs: ["read"],
    connectorsVerbs: ["read"],
    orgIamVerbs: ["read"],
  },
];

export function IamNativeRoleMatrixCard({
  roleMatrix,
  labels,
  openHelpSection,
}: IamNativeRoleMatrixCardProps): React.ReactElement {
  const mat = labels.matrix;

  const summaryByRole: Record<OfficialIamRoleKey, string> = {
    PLATFORM_ADMIN: mat.summaryFullPlatform,
    SECOPS: mat.summarySecurityAudit,
    BU_LEAD: mat.summaryBuSupervision,
    TEAM_LEAD: mat.summaryTeamLead,
    ONTOLOGY_LEAD: mat.summaryOntologyLead,
    CONTRIBUTOR: mat.summaryContributor,
    OBSERVER: mat.summaryObserver,
  };

  const renderVerbBadges = (verbs: readonly UiPermissionVerb[]): React.ReactNode => (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
      {verbs.map((v) => (
        <span
          key={v}
          style={{
            fontSize: "11px",
            padding: "2px 6px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-muted)",
            color: "var(--color-foreground)",
          }}
        >
          {labels.verbs[v]}
        </span>
      ))}
    </div>
  );

  return (
    <section
      data-testid="iam-native-role-matrix-card"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h2 style={{ margin: 0, fontSize: "15px" }}>{mat.sectionTitle}</h2>
          </div>
          <p style={{ margin: 0, fontSize: "12.5px", color: "var(--color-muted-foreground)" }}>
            {mat.sectionSubtitle}
          </p>
        </div>
      </div>

      <OrciaAlertBanner tone="cobalt" testId="iam-write-only-secrets-banner">
        <strong>{mat.secretBannerTitle}</strong> — {mat.secretBannerBody}
      </OrciaAlertBanner>

      <div style={{ overflowX: "auto" }}>
        <table
          data-testid="iam-role-matrix-table"
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "12.5px",
          }}
        >
          <thead>
            <tr
              style={{
                borderBottom: "1px solid var(--color-border)",
                textAlign: "left",
                color: "var(--color-muted-foreground)",
              }}
            >
              <th style={{ padding: "8px 10px" }}>{mat.colRole}</th>
              <th style={{ padding: "8px 10px" }}>{mat.colNaturalScope}</th>
              <th style={{ padding: "8px 10px" }}>{mat.colWorkflowsAgents}</th>
              <th style={{ padding: "8px 10px" }}>{mat.colDatasourcesConnectors}</th>
              <th style={{ padding: "8px 10px" }}>{mat.colOrgAndIam}</th>
            </tr>
          </thead>
          <tbody>
            {OFFICIAL_IAM_ROLES.map((roleKey) => {
              const apiRow = roleMatrix.find((r) => r.role === roleKey);
              const fallback = DEFAULT_FALLBACK_ROWS.find((r) => r.role === roleKey)!;
              const scopeKey = apiRow?.natural_scope ?? fallback.naturalScope;
              return (
                <tr
                  key={roleKey}
                  data-testid={`iam-matrix-role-row-${roleKey}`}
                  style={{ borderBottom: "1px solid var(--color-border)" }}
                >
                  <td style={{ padding: "10px", verticalAlign: "top", minWidth: "200px" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      <div>
                        <StatusBadge
                          label={labels.roles[roleKey]}
                          tone={
                            roleKey === "PLATFORM_ADMIN" || roleKey === "SECOPS"
                              ? "cobalt"
                              : roleKey === "OBSERVER"
                                ? "neutral"
                                : "emerald"
                          }
                        />
                      </div>
                      <span style={{ fontSize: "11.5px", color: "var(--color-muted-foreground)" }}>
                        {summaryByRole[roleKey]}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: "10px", verticalAlign: "top", whiteSpace: "nowrap" }}>
                    <strong>{labels.roleScopes[scopeKey]}</strong>
                  </td>
                  <td style={{ padding: "10px", verticalAlign: "top" }}>
                    {renderVerbBadges(fallback.workflowsVerbs)}
                  </td>
                  <td style={{ padding: "10px", verticalAlign: "top" }}>
                    {renderVerbBadges(fallback.connectorsVerbs)}
                  </td>
                  <td style={{ padding: "10px", verticalAlign: "top" }}>
                    {renderVerbBadges(fallback.orgIamVerbs)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

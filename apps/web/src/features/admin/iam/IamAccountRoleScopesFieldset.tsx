import React from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { IamDirectoryLabels } from "../../../i18n/locales/iam_accounts_directory_labels";
import type { OfficialIamRoleKey } from "./iamApiBridge";

export interface IamAccountRoleScopesFieldsetProps {
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly selectedRoles: readonly OfficialIamRoleKey[];
  readonly selectedLedBuIds: readonly string[];
  readonly onChangeSelectedLedBuIds: (nextBuIds: readonly string[]) => void;
  readonly selectedLedTeamIds: readonly string[];
  readonly onChangeSelectedLedTeamIds: (nextTeamIds: readonly string[]) => void;
  readonly canMutate: boolean;
  readonly isSubmitting: boolean;
  readonly labels: IamDirectoryLabels;
}

const FIELDSET_STYLE: React.CSSProperties = {
  margin: 0,
  padding: "10px 12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  display: "flex",
  flexDirection: "column",
  gap: "6px",
};

export function IamAccountRoleScopesFieldset({
  orgUnits,
  selectedRoles,
  selectedLedBuIds,
  onChangeSelectedLedBuIds,
  selectedLedTeamIds,
  onChangeSelectedLedTeamIds,
  canMutate,
  isSubmitting,
  labels,
}: IamAccountRoleScopesFieldsetProps): React.ReactElement | null {
  const showLedBus = selectedRoles.includes("BU_LEAD");
  const showLedTeams = selectedRoles.includes("TEAM_LEAD");
  if (!showLedBus && !showLedTeams) return null;

  const buUnits = orgUnits.filter((u) => u.level === "BU");
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");

  return (
    <>
      {showLedBus ? (
        <fieldset data-testid="iam-account-led-bus-fieldset" style={FIELDSET_STYLE}>
          <legend style={{ fontSize: "12px", fontWeight: 600, padding: "0 4px" }}>
            {labels.ledBusFieldsetLabel}
          </legend>
          <p style={{ margin: 0, fontSize: "11.5px", color: "var(--color-muted-foreground)" }}>
            {labels.ledBusFieldsetHint}
          </p>
          {buUnits.length === 0 ? (
            <p style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}>
              {labels.noBusAvailableHint}
            </p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
              {buUnits.map((bu) => {
                const checked =
                  selectedLedBuIds.includes(bu.id) || selectedLedBuIds.includes(bu.slug);
                return (
                  <label
                    key={bu.id}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "12.5px",
                      cursor: !canMutate || isSubmitting ? "not-allowed" : "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      data-bwignore="true"
                      data-form-type="other"
                      data-testid={`iam-account-led-bu-checkbox-${bu.id}`}
                      disabled={!canMutate || isSubmitting}
                      checked={checked}
                      onChange={(e) =>
                        onChangeSelectedLedBuIds(
                          e.target.checked
                            ? [...selectedLedBuIds.filter((id) => id !== bu.slug), bu.id]
                            : selectedLedBuIds.filter((id) => id !== bu.id && id !== bu.slug),
                        )
                      }
                    />
                    <span>{bu.name}</span>
                  </label>
                );
              })}
            </div>
          )}
        </fieldset>
      ) : null}

      {showLedTeams ? (
        <fieldset data-testid="iam-account-led-teams-fieldset" style={FIELDSET_STYLE}>
          <legend style={{ fontSize: "12px", fontWeight: 600, padding: "0 4px" }}>
            {labels.ledTeamsFieldsetLabel}
          </legend>
          <p style={{ margin: 0, fontSize: "11.5px", color: "var(--color-muted-foreground)" }}>
            {labels.ledTeamsFieldsetHint}
          </p>
          {teamUnits.length === 0 ? (
            <p style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}>
              {labels.noTeamsAvailableHint}
            </p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
              {teamUnits.map((team) => {
                const checked =
                  selectedLedTeamIds.includes(team.id) || selectedLedTeamIds.includes(team.slug);
                return (
                  <label
                    key={team.id}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "12.5px",
                      cursor: !canMutate || isSubmitting ? "not-allowed" : "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      data-bwignore="true"
                      data-form-type="other"
                      data-testid={`iam-account-led-team-checkbox-${team.id}`}
                      disabled={!canMutate || isSubmitting}
                      checked={checked}
                      onChange={(e) =>
                        onChangeSelectedLedTeamIds(
                          e.target.checked
                            ? [...selectedLedTeamIds.filter((id) => id !== team.slug), team.id]
                            : selectedLedTeamIds.filter((id) => id !== team.id && id !== team.slug),
                        )
                      }
                    />
                    <span>{team.name}</span>
                  </label>
                );
              })}
            </div>
          )}
        </fieldset>
      ) : null}
    </>
  );
}

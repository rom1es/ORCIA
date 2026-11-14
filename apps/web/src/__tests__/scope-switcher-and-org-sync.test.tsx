import { describe, expect, it } from "vitest";
import { buildWorkspaceSwitcherOptions } from "../components/shellScopeOptions";

describe("TopHeader Workspace Switcher explicit Team vs Workspace distinction", () => {
  it("explicitly distinguishes an Espace (📦 Espace · RTS) from an Équipe (👥 Équipe · MonCompte) and a Direction (🏢 Direction (BU) · 123)", () => {
    const optionsFr = buildWorkspaceSwitcherOptions({
      isFr: true,
      orgUnits: [
        {
          id: "org-1",
          name: "123",
          slug: "123",
          level: "BU",
          parentId: "scope-global",
        },
        {
          id: "org-2",
          name: "MonCompte",
          slug: "moncompte",
          level: "TEAM",
          parentId: "org-1",
        },
      ],
      workspaces: [
        {
          workspaceId: "ws-1",
          name: "RTS",
          visibilityMode: "STANDARD",
          lifecyclePhase: "MIGRATION",
          suggestedWorkflows: [],
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
        {
          workspaceId: "ws-2",
          name: "Labo Perso",
          visibilityMode: "PRIVATE_USER",
          ownerOrgUnitId: "org-2",
          lifecyclePhase: "BUILD",
          suggestedWorkflows: [],
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
      scopes: [
        {
          id: "scope-global",
          level: "GLOBAL",
          name: "Plateforme Globale ORCIA",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        },
      ],
    });

    const rtsWorkspaceOpt = optionsFr.find((o) => o.id === "ws-1");
    expect(rtsWorkspaceOpt).toEqual({
      id: "ws-1",
      label: "📦 Espace · RTS",
      groupLabel: "📦 Espace · 👥 Mes Équipes & Espaces",
    });

    const teamOpt = optionsFr.find((o) => o.id === "org-2");
    expect(teamOpt).toEqual({
      id: "org-2",
      label: "👥 Équipe · MonCompte",
      groupLabel: "👥 Mes Équipes & Espaces · Équipe",
    });

    const privateWsOpt = optionsFr.find((o) => o.id === "ws-2");
    expect(privateWsOpt).toEqual({
      id: "ws-2",
      label: "🔒 Espace · Labo Perso · MonCompte",
      groupLabel: "🔒 Mes Espaces Privés",
    });

    const buOpt = optionsFr.find((o) => o.id === "org-1");
    expect(buOpt).toEqual({
      id: "org-1",
      label: "🏢 Direction (BU) · 123",
      groupLabel: "🏢 Supervision Organisation",
    });
  });

  it("supports English labels and resolves ownerOrgUnitName from orgUnits when ownerOrgUnitId is set", () => {
    const optionsEn = buildWorkspaceSwitcherOptions({
      isFr: false,
      orgUnits: [
        {
          id: "org-team-1",
          name: "Core AI Team",
          slug: "core-ai-team",
          level: "TEAM",
          parentId: "scope-global",
        },
      ],
      workspaces: [
        {
          workspaceId: "ws-1",
          name: "RTS",
          visibilityMode: "STANDARD",
          ownerOrgUnitId: "org-team-1",
          lifecyclePhase: "BUILD",
          suggestedWorkflows: [],
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
      scopes: [],
    });

    expect(optionsEn).toEqual([
      {
        id: "org-team-1",
        label: "👥 Team · Core AI Team",
        groupLabel: "👥 My Teams & Spaces · Team",
      },
      {
        id: "ws-1",
        label: "📦 Workspace · RTS · Core AI Team",
        groupLabel: "📦 Workspace · 👥 My Teams & Spaces",
      },
    ]);
  });
});

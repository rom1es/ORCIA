import { describe, expect, it, beforeEach } from "vitest";
import {
  detectActiveAutocompleteTrigger,
  applyAutocompleteSelectionToPrompt,
} from "@orcia/ui";
import {
  resetCachedAgentsAndSkillsForTest,
  writeCachedAgentsAndSkills,
} from "../components/agentsAndSkillsBridgeStore";
import { buildAssistantAutocompleteSuggestions } from "../features/inbox/assistantAutocompleteHelpers";

describe("Story 31.3 — Qualified Pack Autocomplete Collision Handling", () => {
  beforeEach(() => {
    resetCachedAgentsAndSkillsForTest();
  });

  it("inserts qualified @pack/slug and /pack/slug on slug collision and preserves short form when unique", () => {
    writeCachedAgentsAndSkills({
      agents: [
        {
          agentId: "sdlc:reviewer",
          slug: "reviewer",
          handle: "@reviewer",
          name: "SDLC Reviewer",
          roleMission: "SDLC checks",
          instructions: "Check SDLC",
          thinkingLevel: "medium",
          skillIds: [],
          visibilityScope: "PACK",
          sourcePackKey: "orcia-pack-sdlc",
          packSlug: "sdlc",
          qualifiedRef: "@sdlc/reviewer",
          isColliding: true,
          lifecycleStatus: "ACTIVE",
        },
        {
          agentId: "legal-audit:reviewer",
          slug: "reviewer",
          handle: "@reviewer",
          name: "Legal Reviewer",
          roleMission: "Legal checks",
          instructions: "Check Legal",
          thinkingLevel: "medium",
          skillIds: [],
          visibilityScope: "PACK",
          sourcePackKey: "orcia-pack-legal-audit",
          packSlug: "legal-audit",
          qualifiedRef: "@legal-audit/reviewer",
          isColliding: true,
          lifecycleStatus: "ACTIVE",
        },
        {
          agentId: "agent-unique-helper",
          slug: "unique-helper",
          handle: "@unique-helper",
          name: "Unique Helper",
          roleMission: "Assist",
          instructions: "Assist cleanly",
          thinkingLevel: "simple",
          skillIds: [],
          visibilityScope: "TEAM",
          lifecycleStatus: "ACTIVE",
        },
      ],
      skills: [
        {
          skillId: "sdlc:compliance-check",
          slug: "compliance-check",
          commandHandle: "/compliance-check",
          name: "SDLC Compliance",
          objective: "SDLC audit",
          inputParameters: [],
          instructions: "Run SDLC audit",
          expectedOutputFormat: "Markdown",
          visibilityScope: "PACK",
          packSlug: "sdlc",
          qualifiedRef: "/sdlc/compliance-check",
          isColliding: true,
        },
        {
          skillId: "legal-audit:compliance-check",
          slug: "compliance-check",
          commandHandle: "/compliance-check",
          name: "Legal Compliance",
          objective: "Legal audit",
          inputParameters: [],
          instructions: "Run Legal audit",
          expectedOutputFormat: "Markdown",
          visibilityScope: "PACK",
          packSlug: "legal-audit",
          qualifiedRef: "/legal-audit/compliance-check",
          isColliding: true,
        },
        {
          skillId: "skill-unique-summary",
          slug: "unique-summary",
          commandHandle: "/unique-summary",
          name: "Unique Summary",
          objective: "Summarize",
          inputParameters: [],
          instructions: "Summarize text",
          expectedOutputFormat: "Markdown",
          visibilityScope: "TEAM",
        },
      ],
    });

    const suggestions = buildAssistantAutocompleteSuggestions([], false);
    const agentTokens = suggestions.filter((s) => s.kind === "agent");
    const skillTokens = suggestions.filter((s) => s.kind === "skill");

    expect(agentTokens.map((a) => a.token)).toEqual([
      "@sdlc/reviewer",
      "@legal-audit/reviewer",
      "@unique-helper",
    ]);
    expect(agentTokens[0]?.badge).toBe("sdlc");
    expect(agentTokens[1]?.badge).toBe("legal-audit");

    expect(skillTokens.map((s) => s.token)).toEqual([
      "/sdlc/compliance-check",
      "/legal-audit/compliance-check",
      "/unique-summary",
    ]);
    expect(skillTokens[0]?.badge).toBe("sdlc");
    expect(skillTokens[1]?.badge).toBe("legal-audit");

    expect(detectActiveAutocompleteTrigger("Please ask @sdlc/rev")).toEqual({
      kind: "agent",
      query: "sdlc/rev",
      tokenStartIndex: 11,
    });
    expect(
      applyAutocompleteSelectionToPrompt("Please ask @sdlc/rev", {
        kind: "agent",
        slug: "sdlc/reviewer",
        label: "SDLC Reviewer",
        description: "SDLC checks",
      }),
    ).toBe("@sdlc/reviewer Please ask ");
  });
});

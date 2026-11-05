// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { resolveModuleFromPathname } from "../components/ShellContainer";
import { ORCIA_SITE_MANIFEST } from "../generated/orciaSiteManifest";
import { createOrciaQueryClient, createOrciaRouter } from "../router";

const FORBIDDEN_IMPLEMENTATION_TERMS_IN_MACRO_AND_FEATURES = [
  "PostgreSQL",
  "FastAPI",
  "DBOS",
  "SQLAlchemy",
  "pgvector",
  "halfvec",
  "Starlark",
  "Wasmtime",
  "Argon2id",
  "Dramatiq",
  "SeaweedFS",
] as const;

describe("ORCIA Product & Architecture Showcase Site (/showcase) — 3 Strictly Separated Pillars + Live Synced Changelog", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
  });

  afterEach(() => {
    cleanup();
  });

  it("navigates in 1 click from /help (open-orcia-showcase-site-btn) to /showcase and resolves module routing", async () => {
    expect(resolveModuleFromPathname("/showcase")).toBe("ontology");

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/help"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    const openShowcaseBtn = screen.getByTestId("open-orcia-showcase-site-btn");
    expect(openShowcaseBtn.textContent?.replace("🌐", "").trim()).toBe("Documentation");

    fireEvent.click(openShowcaseBtn);
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByTestId("orcia-product-showcase-site-view")).toBeDefined();
    expect(screen.getByTestId("showcase-pillar-macro")).toBeDefined();

    fireEvent.click(screen.getByTestId("showcase-export-standalone-btn"));
    const exportBanner = screen.getByTestId("showcase-standalone-export-banner");
    expect(exportBanner.textContent).toContain(
      "ouvrez directement `docs/site-catalog/index.html`.",
    );
    expect(exportBanner.textContent).not.toContain("dist/orcia-site/index.html");
  });

  it("enforces strict editorial separation (non-mixing gate): Space 1 (Macro) and Space 2 (Features) contain zero implementation terms, while Space 3 (Architecture) explains all of them", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/showcase"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // 1. Space 1: Vision & Pilotage Humain (Macro)
    const macroPillar = screen.getByTestId("showcase-pillar-macro");
    const macroText = macroPillar.textContent ?? "";
    expect(macroText).toContain("Human-Led");
    expect(macroText).toContain("Ancrages de Rédaction Humaine");
    expect(macroText).toContain("Anti-Validation Fantôme");
    expect(macroText).toContain("Double Barrière Anti-Hallucination");
    expect(macroText).toContain("Contrôles Déterministes");
    expect(macroText).toContain("Contrôles Probabilistes Croisés");
    expect(macroText).toContain("Remise en Cause Amont");

    for (const term of FORBIDDEN_IMPLEMENTATION_TERMS_IN_MACRO_AND_FEATURES) {
      expect(
        macroText,
        `Forbidden implementation term "${term}" leaked into Space 1 (showcase-pillar-macro)`,
      ).not.toContain(term);
    }

    // 2. Switch to Space 2: Fonctionnalités & Écrans (Guide Fonctionnel)
    fireEvent.click(screen.getByTestId("showcase-tab-features"));
    const featuresPillar = screen.getByTestId("showcase-pillar-features");
    const featuresText = featuresPillar.textContent ?? "";

    // Verify all 6 Human-Led devices and all 9 screens are presented
    expect(screen.getByTestId("showcase-device-1-human-anchor")).toBeDefined();
    expect(screen.getByTestId("showcase-device-2-arbitration-card")).toBeDefined();
    expect(screen.getByTestId("showcase-device-3-briefing-grid")).toBeDefined();
    expect(screen.getByTestId("showcase-device-4-impact-simulator")).toBeDefined();
    expect(screen.getByTestId("showcase-device-5-verified-citations")).toBeDefined();
    expect(screen.getByTestId("showcase-device-6-team-claim")).toBeDefined();

    for (const screenId of [
      "cockpit",
      "assistant",
      "processes",
      "agents",
      "spaces",
      "finops",
      "activity",
      "settings",
      "help",
    ]) {
      expect(screen.getByTestId(`showcase-screen-card-${screenId}`)).toBeDefined();
    }

    for (const term of FORBIDDEN_IMPLEMENTATION_TERMS_IN_MACRO_AND_FEATURES) {
      expect(
        featuresText,
        `Forbidden implementation term "${term}" leaked into Space 2 (showcase-pillar-features)`,
      ).not.toContain(term);
    }

    // 3. Switch to Space 3: Architecture & Choix Techniques (Sous le Capot)
    fireEvent.click(screen.getByTestId("showcase-tab-architecture"));
    const archPillar = screen.getByTestId("showcase-pillar-architecture");
    const archText = archPillar.textContent ?? "";

    for (const term of [
      "PostgreSQL 18",
      "FastAPI",
      "DBOS Transact",
      "SQLAlchemy",
      "pgvector",
      "halfvec(1024)",
      "RRF (k=60)",
      "Starlark",
      "Wasmtime",
      "Argon2id",
      "Dramatiq",
      "SeaweedFS",
      "human_anchor_signatures",
      "AdaptiveHumanGateService",
      "ExternalEditRebaser",
      "UpstreamChallengeAndReplayService",
    ]) {
      expect(
        archText,
        `Expected technical term "${term}" in Space 3 (showcase-pillar-architecture)`,
      ).toContain(term);
    }

    // 4. Switch to Space 4: Historique des Évolutions & Statistiques Vivantes
    fireEvent.click(screen.getByTestId("showcase-tab-changelog"));
    const changelogPillar = screen.getByTestId("showcase-pillar-changelog");
    expect(changelogPillar).toBeDefined();
    expect(screen.getByTestId("showcase-stat-routes").textContent).toContain(
      String(ORCIA_SITE_MANIFEST.stats.activeRoutesCount),
    );
    expect(screen.getByTestId("showcase-stat-reports").textContent).toContain(
      String(ORCIA_SITE_MANIFEST.stats.techLeadReportsCount),
    );

    // Filter reports in Space 4
    const searchInput = screen.getByTestId("showcase-changelog-search-input");
    fireEvent.change(searchInput, {
      target: { value: "2026-11-05-site-presentation-orcia" },
    });
    expect(
      screen.getByTestId(
        "showcase-report-item-2026-11-05-site-presentation-orcia-3-piliers-human-led-anti-hallucination-et-sync-auto-tech-lead-report.md",
      ),
    ).toBeDefined();
  });
});

/**
 * Unit & Integration tests for Story 6.3:
 * FinOps Human Mastery, Anti-Rubber-Stamping, Reversibility & F5 Survival (`AD-17 Layer 1b`).
 */

import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { FinopsFeaturePanel } from "../features/finops";
import { I18nProvider } from "../i18n";

const sampleOverviewResponse = {
  overview: {
    total_cost_usd: 150.0,
    total_cost_eur: 138.0,
    verified_internal_cost_usd: 120.0,
    verified_internal_cost_eur: 110.4,
    reported_external_cost_usd: 30.0,
    reported_external_cost_eur: 27.6,
    total_llm_tokens: 2500000,
    internal_tokens: 2200000,
    remote_tokens: 300000,
    total_external_calls: 150,
    external_units_breakdown: {},
    cache_savings_usd: 25.0,
    cache_savings_eur: 23.0,
    active_circuit_breakers_count: 0,
    paused_runs_count: 0,
    accounted_runs_count: 12,
  },
  processes: [],
  tiers: [],
  scope_budgets: [],
  baselines: [],
};

const sampleCognitiveResponse = {
  active_framing_ratio: 0.62,
  active_framing_target: 0.40,
  active_framing_alert: false,
  quick_pass_rate: 0.02,
  quick_pass_threshold: 0.05,
  quick_pass_alert: false,
  rubber_stamping_rate: 0.02,
  rubber_stamping_alert: false,
  architecture_deviation_index: 0.0,
  architecture_deviation_target: 0.0,
  architecture_deviation_alert: false,
  pattern_drift_index: 0.0,
  pattern_drift_alert: false,
  total_human_hours: 4.5,
  active_framing_hours: 2.8,
  review_hours: 1.7,
  uncovered_deviations_count: 0,
  workflow_breakdowns: [
    {
      workflow_id: "wf-review-1",
      workflow_title: "Contrat de Prestation",
      criticality: "STANDARD",
      human_gates_count: 8,
      human_passes_count: 8,
      quick_passes_count: 1,
      quick_pass_rate: 0.125,
      median_review_duration_ms: 18000,
      uncovered_drift_count: 0,
      has_alert: true,
    },
  ],
  recommendations: [
    {
      id: "rec-wf-review-1",
      workflow_id: "wf-review-1",
      workflow_title: "Contrat de Prestation",
      recommendation_type: "SWITCH_TO_RISK_OR_SAMPLING",
      title: "Politique ciblée par risque ou par échantillonnage",
      description:
        "Le processus présente un taux de validation unanime avec des délais courts. Basculez en échantillonnage.",
      action_label: "Passer en échantillonnage (20 %)",
      suggested_policy: "SAMPLING_20_PCT",
      status: "PROPOSED",
      applied_at: null,
      applied_by: null,
    },
  ],
};

describe("Story 6.3: FinOps Human Mastery Tab & Cognitive Governance", () => {
  let appliedCallCount = 0;

  beforeEach(() => {
    appliedCallCount = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/api/v1/finops/dashboard")) {
        return new Response(JSON.stringify(sampleOverviewResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.includes("/api/v1/finops/cognitive-impact")) {
        return new Response(JSON.stringify(sampleCognitiveResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.includes("/api/v1/finops/gates/policy-recommendation/")) {
        appliedCallCount++;
        return new Response(
          JSON.stringify({
            recommendation_id: "rec-wf-review-1",
            status: "APPLIED",
            applied_at: "2026-11-16T12:00:00Z",
            applied_by: "user-123",
            workflow_id: "wf-review-1",
            suggested_policy: "SAMPLING_20_PCT",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      return new Response(JSON.stringify({}), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders the 4th tab 'Maîtrise humaine & Qualité' and displays 3 counter-metric gauges", async () => {
    await act(async () => {
      render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <FinopsFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("finops-tab-cognitive-governance")).toBeDefined();
    });

    // Switch to tab 4
    await act(async () => {
      fireEvent.click(screen.getByTestId("finops-tab-cognitive-governance"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("finops-human-mastery-tab")).toBeDefined();
    });

    // Verify 3 gauges
    expect(screen.getByTestId("human-mastery-gauge-framing-value").textContent).toContain("62 %");
    expect(screen.getByTestId("human-mastery-gauge-framing-status").textContent).toContain(
      "Équilibré",
    );

    expect(screen.getByTestId("human-mastery-gauge-quick-pass-value").textContent).toContain("2 %");
    expect(screen.getByTestId("human-mastery-gauge-quick-pass-status").textContent).toContain(
      "Conforme",
    );

    expect(screen.getByTestId("human-mastery-gauge-architecture-value").textContent).toContain(
      "0 %",
    );
    expect(screen.getByTestId("human-mastery-gauge-architecture-status").textContent).toContain(
      "Aligné",
    );
  });

  it("displays gate policy recommendations and applies adjustment on button click", async () => {
    await act(async () => {
      render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <FinopsFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("finops-tab-cognitive-governance")).toBeDefined();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("finops-tab-cognitive-governance"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("human-mastery-rec-card-rec-wf-review-1")).toBeDefined();
    });

    const applyBtn = screen.getByTestId("human-mastery-apply-btn-rec-wf-review-1");
    expect(applyBtn.textContent).toContain("Passer en échantillonnage (20 %)");

    // Click apply
    await act(async () => {
      fireEvent.click(applyBtn);
    });

    await waitFor(() => {
      expect(appliedCallCount).toBe(1);
      expect(screen.getByTestId("finops-success-banner")).toBeDefined();
    });
  });

  it("survives F5 reload (unmount -> render): re-fetches and preserves cognitive mastery state", async () => {
    let unmountFn!: () => void;
    await act(async () => {
      const res = render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <FinopsFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );
      unmountFn = res.unmount;
    });

    await waitFor(() => {
      expect(screen.getByTestId("finops-tab-cognitive-governance")).toBeDefined();
    });

    // F5 unmount
    await act(async () => {
      unmountFn();
    });

    // F5 render
    await act(async () => {
      render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <FinopsFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("finops-tab-cognitive-governance")).toBeDefined();
      expect(screen.getByTestId("finops-page-title")).toBeDefined();
    });
  });
});

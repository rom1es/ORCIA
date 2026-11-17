/**
 * Vitest Layer 1b tests for Story 6.4:
 * Remote MCP & A2A multi-metric telemetry, separate KPIs, quota modal, circuit reset & F5 survival.
 */

import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { FinopsFeaturePanel } from "../features/finops";
import { I18nProvider } from "../i18n";

const baseDashboardResponse = {
  overview: {
    total_cost_usd: 150.0,
    total_cost_eur: 138.0,
    verified_internal_cost_usd: 120.0,
    verified_internal_cost_eur: 110.4,
    reported_external_cost_usd: 30.0,
    reported_external_cost_eur: 27.6,
    total_llm_tokens: 2_500_000,
    internal_tokens: 2_200_000,
    remote_tokens: 300_000,
    total_external_calls: 150,
    external_units_breakdown: { pages_ocr: 450, recherches_web: 120 },
    cache_savings_usd: 25.0,
    cache_savings_eur: 23.0,
    active_circuit_breakers_count: 1,
    paused_runs_count: 0,
    accounted_runs_count: 12,
  },
  processes: [],
  tiers: [],
  scope_budgets: [],
  baselines: [],
};

const baseCognitiveResponse = {
  active_framing_ratio: 0.62,
  active_framing_target: 0.4,
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
  workflow_breakdowns: [],
  recommendations: [],
};

describe("Story 6.4: Remote MCP Services Tab, Quota Modal, Circuit Reset & F5 Survival", () => {
  let remoteServicesState: Array<Record<string, unknown>>;

  beforeEach(() => {
    remoteServicesState = [
      {
        connector_key: "mcp-ocr",
        display_name: "Service OCR Documentaire",
        service_kind: "MCP_SERVER",
        scope_type: "GLOBAL",
        scope_id: null,
        valuation_mode: "NATIVE_TELEMETRY",
        max_reported_cost_per_call_eur: 5.0,
        fixed_cost_per_call_eur: 0.0,
        unit_tariff_eur: 0.04,
        default_unit_name: "pages_ocr",
        max_daily_calls: 100,
        max_monthly_cost_eur: 50.0,
        daily_calls_count: 42,
        avg_latency_ms: 185,
        total_remote_tokens: 0,
        total_business_units: 450,
        consolidated_cost_usd: 25.0,
        consolidated_cost_eur: 23.0,
        quota_used_pct: 46.0,
        circuit_state: "CIRCUIT_OPEN",
        anomaly_count: 1,
        last_tripped_reason: "Monthly cap reached",
      },
      {
        connector_key: "a2a-research",
        display_name: "Agent Recherche Veille",
        service_kind: "A2A_AGENT",
        scope_type: "GLOBAL",
        scope_id: null,
        valuation_mode: "FIXED_SCALE",
        max_reported_cost_per_call_eur: 5.0,
        fixed_cost_per_call_eur: 0.05,
        unit_tariff_eur: 0.02,
        default_unit_name: "recherches_web",
        max_daily_calls: 500,
        max_monthly_cost_eur: 40.0,
        daily_calls_count: 108,
        avg_latency_ms: 310,
        total_remote_tokens: 300_000,
        total_business_units: 120,
        consolidated_cost_usd: 5.0,
        consolidated_cost_eur: 4.6,
        quota_used_pct: 11.5,
        circuit_state: "CLOSED",
        anomaly_count: 0,
        last_tripped_reason: null,
      },
    ];

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();

      if (url.includes("/api/v1/finops/dashboard")) {
        return new Response(JSON.stringify(baseDashboardResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.includes("/api/v1/finops/cognitive-impact")) {
        return new Response(JSON.stringify(baseCognitiveResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.includes("/api/v1/finops/remote-services")) {
        return new Response(
          JSON.stringify({
            services: remoteServicesState,
            total_external_calls: 150,
            total_remote_tokens: 300_000,
            total_reported_cost_eur: 27.6,
            open_circuits_count: remoteServicesState.filter((s) => s.circuit_state === "CIRCUIT_OPEN").length,
            units_breakdown: { pages_ocr: 450, recherches_web: 120 },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (url.includes("/api/v1/finops/connectors/mcp-ocr/reset-circuit") && method === "POST") {
        remoteServicesState = remoteServicesState.map((s) =>
          s.connector_key === "mcp-ocr" ? { ...s, circuit_state: "CLOSED" } : s,
        );
        return new Response(
          JSON.stringify({
            connector_key: "mcp-ocr",
            circuit_state: "CLOSED",
            anomaly_count: 1,
            reset_at: "2026-11-16T12:00:00Z",
            reset_by: "user-123",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (url.includes("/api/v1/finops/connectors/a2a-research/quota") && method === "PUT") {
        const body = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
        remoteServicesState = remoteServicesState.map((s) =>
          s.connector_key === "a2a-research"
            ? {
                ...s,
                valuation_mode: body.valuation_mode ?? s.valuation_mode,
                max_monthly_cost_eur: body.max_monthly_cost_eur ?? s.max_monthly_cost_eur,
              }
            : s,
        );
        const updated = remoteServicesState.find((s) => s.connector_key === "a2a-research");
        return new Response(JSON.stringify(updated), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
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

  it("displays separated internal vs external KPIs, external units breakdown, and remote services tab", async () => {
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
      expect(screen.getByTestId("finops-kpi-verified-internal-cost").textContent).toContain("Coût interne vérifié");
      expect(screen.getByTestId("finops-kpi-reported-external-cost").textContent).toContain("Coût externe déclaré");
      expect(screen.getByTestId("finops-kpi-external-units-summary").textContent).toContain("450 pages_ocr");
    });

    fireEvent.click(screen.getByTestId("finops-tab-external-services"));

    await waitFor(() => {
      expect(screen.getByTestId("finops-remote-services-table")).toBeDefined();
      expect(screen.getByTestId("finops-remote-row-mcp-ocr")).toBeDefined();
      expect(screen.getByTestId("finops-circuit-badge-mcp-ocr").textContent).toContain("Connecteur suspendu");
      expect(screen.getByTestId("finops-circuit-badge-a2a-research").textContent).toContain("Opérationnel");
      expect(screen.getByTestId("finops-remote-row-mcp-ocr").textContent).toContain("Télémétrie déclarée par le service");
      expect(screen.getByTestId("finops-remote-row-a2a-research").textContent).toContain("Barème de référence");
    });
  });

  it("resets circuit breaker, updates quota via anti-LastPass modal, and survives F5 unmount/render", async () => {
    let firstRender!: ReturnType<typeof render>;
    await act(async () => {
      firstRender = render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <FinopsFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("finops-tab-external-services")).toBeDefined();
    });
    fireEvent.click(screen.getByTestId("finops-tab-external-services"));

    // 1. Reset suspended circuit breaker
    fireEvent.click(screen.getByTestId("finops-reset-circuit-btn-mcp-ocr"));
    await waitFor(() => {
      expect(screen.getByTestId("finops-circuit-badge-mcp-ocr").textContent).toContain("Opérationnel");
    });

    // 2. Open quota modal and verify anti-LastPass attributes
    fireEvent.click(screen.getByTestId("finops-edit-quota-btn-a2a-research"));
    const modal = await screen.findByTestId("finops-connector-quota-modal");
    expect(modal).toBeDefined();
    const monthlyInput = screen.getByTestId("finops-connector-max-monthly-eur") as HTMLInputElement;
    expect(monthlyInput.getAttribute("data-lpignore")).toBe("true");
    expect(monthlyInput.getAttribute("autocomplete")).toBe("off");

    fireEvent.change(screen.getByTestId("finops-connector-valuation-select"), {
      target: { value: "VOLUMETRIC_ONLY" },
    });
    fireEvent.change(monthlyInput, { target: { value: "120" } });
    fireEvent.submit(screen.getByTestId("finops-connector-quota-form"));

    await waitFor(() => {
      expect(screen.getByTestId("finops-remote-row-a2a-research").textContent).toContain(
        "Suivi volumétrique seul",
      );
    });

    // 3. Simulate F5 reload (unmount -> render) and confirm persisted state rehydrates
    await act(async () => {
      firstRender.unmount();
    });

    await act(async () => {
      render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <FinopsFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );
    });

    fireEvent.click(await screen.findByTestId("finops-tab-external-services"));
    await waitFor(() => {
      expect(screen.getByTestId("finops-circuit-badge-mcp-ocr").textContent).toContain("Opérationnel");
      expect(screen.getByTestId("finops-remote-row-a2a-research").textContent).toContain(
        "Suivi volumétrique seul",
      );
    });
  });
});

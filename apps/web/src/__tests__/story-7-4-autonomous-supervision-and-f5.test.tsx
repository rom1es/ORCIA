import {
  AutonomousExecutionBadge,
  FinopsHumanMasteryTab,
  FourZoneNotificationsDrawer,
} from "@orcia/ui";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { FinopsFeaturePanel } from "../features/finops";
import { ProcessesHubPage } from "../features/processes/ProcessesHubPage";
import { I18nProvider } from "../i18n";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";
import {
  seedVitestAutonomousSupervisionRuns,
  seedVitestContextualHelpResolve,
} from "./vitestAutonomousSupervisionMockHandlers";

const WS_ID = "0195f000-0000-7000-8000-000000000301";
const RUN_ID_1 = "0195f000-0000-7000-8000-000000007401";
const RUN_ID_2 = "0195f000-0000-7000-8000-000000007402";
const CONTRACT_ID = "0195f000-0000-7000-8000-000000007201";

function seedLeadAuthAndWorkspace() {
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "mock-token-lead",
    email: "marc@orcia.local",
    displayName: "Marc Tech Lead",
    roles: ["TEAM_LEAD", "PLATFORM_ADMIN"],
    activeHat: "Tech Lead",
    readOnlyObserver: false,
    mustChangePassword: false,
  });
  seedVitestPlatformSetupState({
    org_units: [
      { id: "org-root", name: "Entreprise", slug: "entreprise", level_kind: "BU", parent_id: null },
    ],
    rbac_grants: [],
    llm_tiers: [{ tier: "fast", model_name: "qwen", endpoint_url: "http://127.0.0.1:11434" }],
    workspaces: [
      {
        workspaceId: WS_ID,
        name: "Espace Documentation",
        visibilityMode: "STANDARD",
        ownerOrgUnitName: "Equipe Docs",
        lifecyclePhase: "RUN",
        suggestedWorkflows: [],
        accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        finopsCostUsd: 0.25,
      },
    ],
    datasources: [],
    packs: [],
    workflows: [],
    runs: [],
    catalog_items: [],
    ontology_concepts: [],
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Story 7.4 — Supervision UX des runs autonomes, Direction C & survie F5", () => {
  it("interdit tout jargon technique (Kill-Switch, Rollback, Service Principal, SM-A1..3, CIRCUIT_OPEN) dans les dictionnaires FR/EN", () => {
    const serialized = JSON.stringify({
      fr: frDictionary.autonomousSupervision,
      en: enDictionary.autonomousSupervision,
      frHelp: frDictionary.contextualHelpHybrid,
      frShell: frDictionary.fourZoneShell,
    });
    const bannedTerms = [
      "Kill-Switch",
      "Kill Switch",
      "Rollback",
      "Tie-Break",
      "Service Principal",
      "CIRCUIT_OPEN",
      "POST_HOC_AUDIT_SAMPLE",
      "AUTONOMOUS_CONTRACT",
      "SM-A1",
      "SM-A2",
      "SM-A3",
      "DBOS",
      "PostgreSQL",
      "Redis",
      "Outbox",
    ];
    for (const term of bannedTerms) {
      expect(serialized).not.toContain(term);
    }
  });

  it("rend AutonomousExecutionBadge en Cyan/Cobalt (jamais Violet humain) et groupe les exécutions nominales dans le tiroir de notifications", () => {
    render(
      <div>
        <AutonomousExecutionBadge
          runId={RUN_ID_1}
          triggerLabel="Mise à jour nocturne"
          runStatus="RUNNING"
          labels={frDictionary.autonomousSupervision.badge}
          onEmergencyStop={vi.fn()}
          onInvalidateAndRestore={vi.fn()}
          onOpenHelpSection={vi.fn()}
        />
        <FourZoneNotificationsDrawer
          onClose={vi.fn()}
          onSelectMenu={vi.fn()}
          notifications={[
            {
              id: "n-nom-1",
              kind: "INFO",
              badgeLabel: "Automatisé",
              title: "Guide processus mis à jour",
              description: "Exécuté selon le contrat",
              isAutonomousNominal: true,
              triggerLabel: "Mise à jour nocturne",
            },
            {
              id: "n-nom-2",
              kind: "INFO",
              badgeLabel: "Automatisé",
              title: "Glossaire synchronisé",
              description: "Exécuté selon le contrat",
              isAutonomousNominal: true,
              triggerLabel: "Mise à jour nocturne",
            },
            {
              id: "n-esc-1",
              kind: "ACTION_REQUIRED",
              badgeLabel: "Escalade",
              title: "Escalade requise : Vérification règle métier",
              description: "Confiance sous le seuil convenu",
              isAutonomousPriority: true,
              triggerLabel: "Mise à jour nocturne",
            },
            {
              id: "n-smp-1",
              kind: "ACTION_REQUIRED",
              badgeLabel: "Échantillon qualité",
              title: "Contrôle qualité par échantillonnage",
              description: "Dossier tiré au sort",
              isAutonomousPriority: true,
              triggerLabel: "Mise à jour nocturne",
            },
          ]}
          labels={frDictionary.fourZoneShell}
          onSelectNotification={vi.fn()}
        />
      </div>,
    );

    const badge = screen.getByTestId("autonomous-execution-badge");
    const outerHtml = badge.outerHTML;
    expect(outerHtml).toContain("--color-autonomous-badge-bg");
    expect(outerHtml).toContain("--color-autonomous-badge-fg");
    expect(outerHtml).not.toContain("--color-human-led-violet");

    expect(screen.getByTestId("notification-center-item-n-esc-1")).toBeDefined();
    expect(screen.getByTestId("notification-center-item-n-smp-1")).toBeDefined();
    expect(screen.queryByTestId("notifications-autonomous-nominal-content")).toBeNull();
    fireEvent.click(screen.getByTestId("notifications-autonomous-nominal-toggle"));
    expect(screen.getByTestId("notifications-autonomous-nominal-content").textContent).toContain(
      "Guide processus mis à jour",
    );
  });

  it("câble /processes Supervision + Arrêt d'urgence + Rétablissement @v(N-1) et survit au rechargement F5", async () => {
    seedLeadAuthAndWorkspace();
    seedVitestAutonomousSupervisionRuns([
      {
        run_id: RUN_ID_1,
        workspace_id: WS_ID,
        workflow_id: "orcia://pack-sdlc/workflows/help-sync",
        workflow_title: "Synchronisation de l'aide",
        trigger_id: "0195f000-0000-7000-8000-000000007301",
        trigger_label: "Mise à jour nocturne",
        trigger_type: "CRON",
        trigger_status: "ACTIVE",
        run_status: "RUNNING",
        post_hoc_status: "NONE",
        contract_id: CONTRACT_ID,
        cost_usd: 0.12,
        created_at_iso: "2026-11-17T08:00:00Z",
        help_resource_id: "help-processes-guide",
        previous_version_available: true,
      },
      {
        run_id: RUN_ID_2,
        workspace_id: WS_ID,
        workflow_id: "orcia://pack-sdlc/workflows/help-sync",
        workflow_title: "Revue documentation API",
        trigger_id: "0195f000-0000-7000-8000-000000007302",
        trigger_label: "Publication documentaire",
        trigger_type: "OUTBOX_EVENT",
        trigger_status: "ACTIVE",
        run_status: "COMMITTED_AUTONOMOUS",
        post_hoc_status: "PENDING_SAMPLE",
        contract_id: CONTRACT_ID,
        cost_usd: 0.08,
        created_at_iso: "2026-11-17T09:00:00Z",
        help_resource_id: "help-processes-guide",
        previous_version_available: true,
      },
    ]);

    const first = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <ProcessesHubPage />
        </ShellContainer>
      </I18nProvider>,
    );

    const stopBtn = await screen.findByTestId(
      `autonomous-run-badge-${RUN_ID_1}-emergency-stop-btn`,
    );
    fireEvent.click(stopBtn);
    await waitFor(() => {
      expect(screen.getByTestId(`autonomous-run-badge-${RUN_ID_1}`).textContent).toContain(
        "Arrêt d'urgence activé",
      );
    });

    const restoreBtn = screen.getByTestId(`autonomous-run-badge-${RUN_ID_2}-restore-btn`);
    fireEvent.click(restoreBtn);
    await waitFor(() => {
      expect(screen.getByTestId(`autonomous-run-badge-${RUN_ID_2}`).textContent).toContain(
        "Annulée · Version précédente rétablie",
      );
    });

    first.unmount();
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <ProcessesHubPage />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId(`autonomous-run-badge-${RUN_ID_1}`).textContent).toContain(
        "Arrêt d'urgence activé",
      );
      expect(screen.getByTestId(`autonomous-run-badge-${RUN_ID_2}`).textContent).toContain(
        "Annulée · Version précédente rétablie",
      );
    });
  });

  it("affiche le badge autonome dans ShellContextualHelpColumn et rétablit @v(N-1) en 1 clic à travers F5", async () => {
    window.history.replaceState({}, "", "/processes");
    seedLeadAuthAndWorkspace();
    seedVitestContextualHelpResolve({
      route: "/processes",
      active_article: {
        resource_id: "help-processes-guide",
        uri: "orcia://help/fr/processes",
        title: "Guide des processus (auto)",
        version: "1.1.0",
        lang: "fr",
        layer: "WORKSPACE",
        pack_name: "orcia-core",
        bound_routes: ["/processes"],
        summary_what_for: "Contenu produit en autonomie sous contrat.",
        step_by_step_items: ["Étape A"],
        key_terms_items: [],
        faq_items: [],
        cas_key: "cas/1111",
        sha256: "a".repeat(64),
        previous_version: "1.0.0",
      },
      merged_layers: ["BASE", "PACK", "WORKSPACE"],
      redis_cache_key: "help:route:/processes:orcia-core:fr",
      rollback_available: true,
      is_autonomous_generated: true,
      run_id: RUN_ID_2,
      contract_label: "Contrat Espace Docs",
      trigger_label: "Mise à jour nocturne",
      previous_version_available: true,
    });

    const first = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <ProcessesHubPage />
        </ShellContainer>
      </I18nProvider>,
    );

    const helpBadge = await screen.findByTestId("contextual-help-autonomous-badge");
    expect(helpBadge.textContent).toContain("Mise à jour nocturne");
    const restoreBtn = screen.getByTestId("contextual-help-autonomous-badge-restore-btn");
    fireEvent.click(restoreBtn);

    await waitFor(() => {
      expect(screen.queryByTestId("contextual-help-autonomous-badge")).toBeNull();
    });

    first.unmount();
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <ProcessesHubPage />
        </ShellContainer>
      </I18nProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("contextual-help-version-pill").textContent).toContain("1.0.0");
      expect(screen.queryByTestId("contextual-help-autonomous-badge")).toBeNull();
    });
  });

  it("masque la section autonome dans /finops si 0 run autonome, sinon affiche SM-A1..A3 et permet la validation post-hoc avec survie F5", async () => {
    render(
      <FinopsHumanMasteryTab
        activeFramingRatio={0.85}
        activeFramingAlert={false}
        quickPassRate={0.05}
        quickPassAlert={false}
        architectureDeviationIndex={0.0}
        architectureDeviationAlert={false}
        workflows={[]}
        recommendations={[]}
        labels={frDictionary.finops.humanMastery}
        autonomousGovernance={{
          totalAutonomousRuns: 0,
          escalatedRunsCount: 0,
          killedRunsCount: 0,
          sampledRunsCount: 0,
          pendingSamplesCount: 0,
          invalidatedSamplesCount: 0,
          autonomousEscalationRate: 0,
          postHocInvalidationRate: 0,
          invalidationAlert: false,
          avgAutonomousCostUsd: 0,
          avgTtmGainMinutes: 0,
          pendingSamples: [],
        }}
        autonomousLabels={frDictionary.autonomousSupervision.finops}
        onOpenHelpSection={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("finops-autonomous-governance-section")).toBeNull();
    cleanup();

    seedLeadAuthAndWorkspace();
    let sampleStatus = "PENDING_SAMPLE";
    let invalidatedCount = 0;
    let invalidationRate = 0.0;
    let alertActive = false;

    const origFetch = globalThis.fetch;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/v1/finops/cognitive-impact")) {
        return new Response(
          JSON.stringify({
            scope_type: "GLOBAL",
            scope_id: null,
            active_framing_ratio: 0.9,
            active_framing_target: 0.4,
            active_framing_alert: false,
            quick_pass_rate: 0.04,
            quick_pass_threshold: 0.05,
            quick_pass_alert: false,
            architecture_deviation_index: 0,
            architecture_deviation_target: 0,
            architecture_deviation_alert: false,
            pattern_drift_index: 0,
            pattern_drift_alert: false,
            total_human_hours: 4,
            active_framing_hours: 3,
            review_hours: 1,
            uncovered_deviations_count: 0,
            workflow_breakdowns: [],
            recommendations: [],
            autonomous_governance: {
              total_autonomous_runs: 10,
              escalated_runs_count: 1,
              killed_runs_count: 0,
              sampled_runs_count: 2,
              pending_samples_count: sampleStatus === "PENDING_SAMPLE" ? 1 : 0,
              invalidated_samples_count: invalidatedCount,
              autonomous_escalation_rate: 0.1,
              post_hoc_invalidation_rate: invalidationRate,
              invalidation_alert: alertActive,
              avg_autonomous_cost_usd: 0.15,
              avg_ttm_gain_minutes: 18,
              pending_samples:
                sampleStatus === "PENDING_SAMPLE"
                  ? [
                      {
                        id: "smp-1",
                        run_id: RUN_ID_2,
                        workflow_title: "Synchronisation de l'aide",
                        trigger_label: "Mise à jour nocturne",
                        review_status: "PENDING_SAMPLE",
                        run_status: "COMMITTED_AUTONOMOUS",
                        sampled_at: "2026-11-17T09:05:00Z",
                      },
                    ]
                  : [],
            },
            trace_id: "0195f000000070008000000000000603",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.includes(`/api/v1/runs/${RUN_ID_2}/post-hoc-review`)) {
        sampleStatus = "INVALIDATED_ROLLED_BACK";
        invalidatedCount = 1;
        invalidationRate = 0.5;
        alertActive = true;
        return new Response(
          JSON.stringify({
            run_id: RUN_ID_2,
            review_status: "INVALIDATED_ROLLED_BACK",
            run_status: "ROLLED_BACK",
            restored_version: "1.0.0",
            trace_id: "0195f000000070008000000000007404",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return origFetch(input, init);
    });

    const first = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <FinopsFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const masteryTab = await screen.findByTestId("finops-tab-cognitive-governance");
    fireEvent.click(masteryTab);

    const invBtn = await screen.findByTestId(`finops-sample-restore-btn-${RUN_ID_2}`);
    fireEvent.click(invBtn);

    await waitFor(() => {
      expect(screen.getByTestId("finops-autonomous-invalidation-alert")).toBeDefined();
      expect(screen.getByTestId("finops-autonomous-gauge-invalidation").textContent).toContain(
        "50 %",
      );
    });

    first.unmount();
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <FinopsFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );
    fireEvent.click(await screen.findByTestId("finops-tab-cognitive-governance"));
    await waitFor(() => {
      expect(screen.getByTestId("finops-autonomous-invalidation-alert")).toBeDefined();
      expect(screen.getByTestId("finops-autonomous-gauge-invalidation").textContent).toContain(
        "50 %",
      );
    });
  });
});

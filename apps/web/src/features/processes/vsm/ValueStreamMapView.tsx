import { OrciaAlertBanner } from "@orcia/ui";
import React, { useEffect, useMemo, useState } from "react";
import { useShellNavigation } from "../../../components/ShellContainer";
import { useI18n } from "../../../i18n";
import { formatRfc9457ErrorToBanner } from "../../../lib/formatRfc9457ErrorToBanner";
import { getInitialVsmSpec } from "../processStudioV2Data";
import { createProcessesApiClient } from "../studio/studioLabelsAndMappers";
import { mapApiVsmToUiSpec, type UiVsmSpec } from "./mapApiVsmToUiSpec";
import { ReturnLoopsSvgOverlay, type VsmReturnLoopItem } from "./ReturnLoopsSvgOverlay";
import { StepDetailSheet } from "./StepDetailSheet";
import {
  ValueStreamMapHeaderAndDrawer,
  type VsmComparisonMode,
} from "./ValueStreamMapHeaderAndDrawer";
import { ValueStreamMapPhaseGrid } from "./ValueStreamMapPhaseGrid";

export type { VsmComparisonMode };

export function ValueStreamMapView({ vsmId }: { vsmId?: string }) {
  const { locale, isFr, dictionary } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const copy = dictionary.processVsmExecutionUi.vsm;
  const localizedBaseVsm = useMemo(() => getInitialVsmSpec(locale), [locale]);

  const targetVsmId = vsmId ?? localizedBaseVsm.id;
  const [vsm, setVsm] = useState<UiVsmSpec>(localizedBaseVsm);
  const [vsmErrorBanner, setVsmErrorBanner] = useState<string | null>(null);

  useEffect(() => {
    setVsm(localizedBaseVsm);
  }, [localizedBaseVsm]);

  useEffect(() => {
    let cancelled = false;
    setVsmErrorBanner(null);
    createProcessesApiClient(locale)
      .getValueStreamMap(targetVsmId)
      .then((apiVsm) => {
        if (cancelled || !apiVsm?.id) {
          return;
        }
        setVsm(mapApiVsmToUiSpec(apiVsm, localizedBaseVsm));
      })
      .catch((err: unknown) => {
        if (cancelled) {
          return;
        }
        const formatted = formatRfc9457ErrorToBanner(err, locale, copy.resourceLabel);
        setVsmErrorBanner(formatted.fullText);
      });
    return () => {
      cancelled = true;
    };
  }, [targetVsmId, locale, copy.resourceLabel, localizedBaseVsm]);

  const allSteps = useMemo(
    () => vsm.phases.flatMap((phase) => phase.steps.map((step) => ({ ...step, phase }))),
    [vsm],
  );
  const allLoops = (vsm.return_loops ?? []) as unknown as VsmReturnLoopItem[];

  const [mode, setMode] = useState<VsmComparisonMode>("compare");
  const [selectedStepNum, setSelectedStepNum] = useState<string | null>("01");
  const [highlightedStepNum, setHighlightedStepNum] = useState<string | null>(null);
  const [showOpportunitiesDrawer, setShowOpportunitiesDrawer] = useState<boolean>(false);
  const [presentationMode, setPresentationMode] = useState<boolean>(false);

  const selectedStep = useMemo(
    () => allSteps.find((s) => s.num === selectedStepNum) ?? null,
    [allSteps, selectedStepNum],
  );

  // Keyboard navigation in Presentation Mode (← / → / Escape)
  useEffect(() => {
    const onKeyDown = (ev: KeyboardEvent) => {
      if (!presentationMode && !selectedStepNum) return;
      if (ev.key === "Escape") {
        setPresentationMode(false);
        return;
      }
      if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
        const currentIndex = allSteps.findIndex((s) => s.num === (selectedStepNum ?? "01"));
        if (currentIndex < 0) return;
        const delta = ev.key === "ArrowRight" ? 1 : -1;
        const nextIndex = (currentIndex + delta + allSteps.length) % allSteps.length;
        const nextStep = allSteps[nextIndex];
        if (nextStep) {
          setSelectedStepNum(nextStep.num);
          setHighlightedStepNum(nextStep.num);
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [allSteps, presentationMode, selectedStepNum]);

  return (
    <section
      data-testid="vsm-interactive-view"
      data-vsm-id={vsmId ?? vsm.id}
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {vsmErrorBanner ? (
        <OrciaAlertBanner tone="crimson" role="alert" testId="vsm-error-banner">
          {vsmErrorBanner}
        </OrciaAlertBanner>
      ) : null}

      <ValueStreamMapHeaderAndDrawer
        vsm={vsm}
        mode={mode}
        presentationMode={presentationMode}
        showOpportunitiesDrawer={showOpportunitiesDrawer}
        copy={copy}
        onNavigateHub={() => navigateToRoute("/processes")}
        onChangeMode={setMode}
        onToggleOpportunities={() => setShowOpportunitiesDrawer((prev) => !prev)}
        onTogglePresentation={() => setPresentationMode((prev) => !prev)}
      />

      <ReturnLoopsSvgOverlay
        loops={allLoops}
        highlightedStepNum={highlightedStepNum ?? selectedStepNum}
        onSelectLoopStep={(fromNum, toNum) => {
          setSelectedStepNum(fromNum);
          setHighlightedStepNum(toNum);
        }}
        isFr={isFr}
      />

      <ValueStreamMapPhaseGrid
        phases={vsm.phases}
        mode={mode}
        selectedStepNum={selectedStepNum}
        copy={copy}
        onSelectStep={setSelectedStepNum}
        onHighlightStep={setHighlightedStepNum}
        onNavigateStudio={(wfId) => navigateToRoute(`/processes/studio/${wfId}`)}
      />

      {selectedStep ? (
        <StepDetailSheet
          step={selectedStep}
          allLoops={allLoops}
          onClose={() => setSelectedStepNum(null)}
          onOpenStudio={(wfId) => navigateToRoute(`/processes/studio/${wfId}`)}
          onExecuteWorkflow={(wfId) => navigateToRoute(`/processes/studio/${wfId}`)}
          isFr={isFr}
        />
      ) : null}
    </section>
  );
}

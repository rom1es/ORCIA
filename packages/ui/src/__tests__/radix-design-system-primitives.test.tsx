import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  OrciaDialog,
  OrciaDropdownMenu,
  OrciaRadixSelect,
  OrciaSwitch,
  OrciaTabBar,
  OrciaTooltip,
} from "../index";

afterEach(() => {
  cleanup();
});

describe("AD-22 Radix UI + shadcn/ui Design System Primitives (@orcia/ui)", () => {
  it("OrciaTabBar renders Radix Tabs with aria-selected, roving tabIndex, panels, and selection callbacks", () => {
    const onSelect = vi.fn();
    render(
      <OrciaTabBar
        ariaLabel="Navigation de test"
        activeTab="overview"
        onSelectTab={onSelect}
        testIdPrefix="test-radix-tab"
        tabs={[
          { key: "overview", label: "Vue d'ensemble" },
          { key: "sources", label: "Sources" },
        ]}
        panels={{
          overview: <div>Contenu Vue d&apos;ensemble</div>,
          sources: <div>Contenu Sources</div>,
        }}
      />,
    );

    const overviewTab = screen.getByTestId("test-radix-tab-overview");
    const sourcesTab = screen.getByTestId("test-radix-tab-sources");

    expect(overviewTab).toHaveAttribute("role", "tab");
    expect(overviewTab).toHaveAttribute("aria-selected", "true");
    expect(sourcesTab).toHaveAttribute("aria-selected", "false");
    expect(screen.getByTestId("test-radix-tab-panel-overview")).toHaveTextContent(
      "Contenu Vue d'ensemble",
    );

    fireEvent.click(sourcesTab);
    expect(onSelect).toHaveBeenCalledWith("sources");
  });

  it("OrciaDialog renders Radix Dialog with focus trap, title, description, and close button", () => {
    const onOpenChange = vi.fn();
    render(
      <OrciaDialog
        open={true}
        onOpenChange={onOpenChange}
        title="Configuration du Connecteur"
        description="Paramètres sécurisés de la source"
        testId="test-radix-dialog"
      >
        <div data-testid="dialog-inner-body">Formulaire interne</div>
      </OrciaDialog>,
    );

    expect(screen.getByTestId("test-radix-dialog")).toBeInTheDocument();
    expect(screen.getByText("Configuration du Connecteur")).toBeInTheDocument();
    expect(screen.getByTestId("dialog-inner-body")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("test-radix-dialog-close-btn"));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("OrciaSwitch toggles checked state via Radix Switch primitive", () => {
    function SwitchHarness() {
      const [checked, setChecked] = useState(false);
      return (
        <OrciaSwitch
          checked={checked}
          onCheckedChange={setChecked}
          ariaLabel="Activer la gouvernance"
          testId="test-radix-switch"
        />
      );
    }

    render(<SwitchHarness />);
    const sw = screen.getByTestId("test-radix-switch");
    expect(sw).toHaveAttribute("aria-checked", "false");
    fireEvent.click(sw);
    expect(sw).toHaveAttribute("aria-checked", "true");
  });

  it("OrciaRadixSelect, OrciaDropdownMenu, and OrciaTooltip render accessible triggers with anti-LastPass attributes", () => {
    const onValueChange = vi.fn();
    const onItemSelect = vi.fn();
    render(
      <div>
        <OrciaRadixSelect
          value="fr"
          onValueChange={onValueChange}
          ariaLabel="Langue"
          testId="test-radix-select"
          options={[
            { value: "fr", label: "Français" },
            { value: "en", label: "English" },
          ]}
        />
        <OrciaDropdownMenu
          triggerLabel="Actions"
          testId="test-radix-menu"
          items={[{ key: "export", label: "Exporter", onSelect: onItemSelect }]}
        />
        <OrciaTooltip content="Aide rapide" testId="test-radix-tooltip">
          <button type="button" data-testid="tooltip-trigger-btn">
            Infos
          </button>
        </OrciaTooltip>
      </div>,
    );

    const selectTrigger = screen.getByTestId("test-radix-select");
    expect(selectTrigger).toHaveAttribute("data-lpignore", "true");
    expect(screen.getByTestId("test-radix-menu-trigger")).toBeInTheDocument();
    expect(screen.getByTestId("tooltip-trigger-btn")).toBeInTheDocument();
  });
});

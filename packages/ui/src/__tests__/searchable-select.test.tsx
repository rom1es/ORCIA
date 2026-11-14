import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  OrciaSearchableSelect,
  type OrciaSearchableSelectOption,
} from "../primitives/OrciaSearchableSelect";

afterEach(() => {
  cleanup();
});

const FIFTEEN_ORGS: readonly OrciaSearchableSelectOption[] = [
  { value: "org-1", label: "Direction Produit", subLabel: "BU" },
  { value: "org-2", label: "Direction Stratégie & DS3C", subLabel: "BU" },
  { value: "org-3", label: "DS3C Pôle Ingénierie", subLabel: "BU" },
  { value: "org-4", label: "DS3C Sécurité des Systèmes", subLabel: "BU" },
  { value: "org-5", label: "Pôle Data & IA", subLabel: "BU" },
  { value: "org-6", label: "Direction Financière", subLabel: "BU" },
  { value: "org-7", label: "Direction RH", subLabel: "BU" },
  { value: "org-8", label: "Direction Juridique", subLabel: "BU" },
  { value: "org-9", label: "Direction Marketing", subLabel: "BU" },
  { value: "org-10", label: "Direction Ventes", subLabel: "BU" },
  { value: "org-11", label: "Direction Support", subLabel: "BU" },
  { value: "org-12", label: "Direction Sécurité", subLabel: "BU" },
  { value: "org-13", label: "Direction Exploitation", subLabel: "BU" },
  { value: "org-14", label: "Direction Innovation", subLabel: "BU" },
  { value: "org-15", label: "Direction Achats", subLabel: "BU" },
];

function ControlledSelect(props: {
  readonly maxDisplayedItems?: number;
  readonly onSearchQueryChange?: (query: string) => void;
  readonly options?: readonly OrciaSearchableSelectOption[];
}) {
  const [val, setVal] = useState("scope-global");
  const allOptions: readonly OrciaSearchableSelectOption[] = [
    { value: "scope-global", label: "Organisation Racine (Aucune unité parente)" },
    ...(props.options ?? FIFTEEN_ORGS),
  ];
  return (
    <OrciaSearchableSelect
      testId="parent-unit-select"
      value={val}
      onChange={setVal}
      options={allOptions}
      maxDisplayedItems={props.maxDisplayedItems ?? 10}
      searchPlaceholder="Rechercher une organisation parente..."
      noMatchLabel="Aucune organisation trouvée"
      truncatedHintTemplate={(hidden) => `+${hidden} organisations non affichées. Affinez votre recherche.`}
      onSearchQueryChange={props.onSearchQueryChange}
    />
  );
}

describe("OrciaSearchableSelect (@orcia/ui)", () => {
  it("renders at most 10 options when 16 options exist and displays truncation hint", () => {
    render(<ControlledSelect />);

    // Trigger button shows selected label
    const trigger = screen.getByTestId("parent-unit-select-trigger");
    expect(trigger.textContent).toContain("Organisation Racine");

    // Hidden select is rendered with value for RTL compatibility
    const hiddenSelect = screen.getByTestId("parent-unit-select") as HTMLSelectElement;
    expect(hiddenSelect.value).toBe("scope-global");

    // Click trigger to open popover
    fireEvent.click(trigger);
    expect(screen.getByTestId("parent-unit-select-listbox")).toBeDefined();

    // Max 10 items displayed out of 16
    const optionElements = screen.getAllByRole("option");
    expect(optionElements.length).toBe(10);

    // Truncation hint is visible with remaining count (+6)
    const hint = screen.getByTestId("parent-unit-select-truncated-hint");
    expect(hint.textContent).toContain("+6 organisations non affichées");
  });

  it("calls onSearchQueryChange immediately on every keystroke without debounce and filters list", () => {
    const onSearchQueryChange = vi.fn();
    render(<ControlledSelect onSearchQueryChange={onSearchQueryChange} />);

    // Open popover
    fireEvent.click(screen.getByTestId("parent-unit-select-trigger"));

    const searchInput = screen.getByTestId("parent-unit-select-search-input");

    // Keystroke 1: "d"
    fireEvent.change(searchInput, { target: { value: "d" } });
    expect(onSearchQueryChange).toHaveBeenCalledTimes(1);
    expect(onSearchQueryChange).toHaveBeenLastCalledWith("d");

    // Keystroke 2: "ds"
    fireEvent.change(searchInput, { target: { value: "ds" } });
    expect(onSearchQueryChange).toHaveBeenCalledTimes(2);
    expect(onSearchQueryChange).toHaveBeenLastCalledWith("ds");

    // Keystroke 3: "ds3"
    fireEvent.change(searchInput, { target: { value: "ds3" } });
    expect(onSearchQueryChange).toHaveBeenCalledTimes(3);
    expect(onSearchQueryChange).toHaveBeenLastCalledWith("ds3");

    // Matching options should only be DS3C units
    const currentOptions = screen.getAllByRole("option");
    expect(currentOptions.length).toBe(3); // org-2, org-3, org-4
    expect(screen.getByTestId("parent-unit-select-option-org-2")).toBeDefined();
    expect(screen.getByTestId("parent-unit-select-option-org-3")).toBeDefined();
    expect(screen.getByTestId("parent-unit-select-option-org-4")).toBeDefined();

    // Truncation hint is hidden since count <= 10
    expect(screen.queryByTestId("parent-unit-select-truncated-hint")).toBeNull();
  });

  it("selects option on click and updates trigger label and hidden select value", () => {
    render(<ControlledSelect />);

    fireEvent.click(screen.getByTestId("parent-unit-select-trigger"));
    const optionOrg1 = screen.getByTestId("parent-unit-select-option-org-1");
    fireEvent.mouseDown(optionOrg1);

    expect(screen.getByTestId("parent-unit-select-trigger").textContent).toContain("Direction Produit");
    const hiddenSelect = screen.getByTestId("parent-unit-select") as HTMLSelectElement;
    expect(hiddenSelect.value).toBe("org-1");
    expect(screen.queryByTestId("parent-unit-select-listbox")).toBeNull();
  });

  it("supports keyboard navigation: ArrowDown, Enter to select, and Escape to close", () => {
    render(<ControlledSelect />);

    fireEvent.click(screen.getByTestId("parent-unit-select-trigger"));
    const searchInput = screen.getByTestId("parent-unit-select-search-input");

    // ArrowDown moves highlight to second item
    fireEvent.keyDown(searchInput, { key: "ArrowDown" });
    fireEvent.keyDown(searchInput, { key: "Enter" });

    // Second item is org-1
    expect(screen.getByTestId("parent-unit-select-trigger").textContent).toContain("Direction Produit");

    // Reopen and press Escape
    fireEvent.click(screen.getByTestId("parent-unit-select-trigger"));
    expect(screen.getByTestId("parent-unit-select-listbox")).toBeDefined();
    fireEvent.keyDown(screen.getByTestId("parent-unit-select-search-input"), { key: "Escape" });
    expect(screen.queryByTestId("parent-unit-select-listbox")).toBeNull();
  });

  it("preserves backward compatibility when tests trigger change on hidden native select", () => {
    render(<ControlledSelect />);

    const hiddenSelect = screen.getByTestId("parent-unit-select");
    fireEvent.change(hiddenSelect, { target: { value: "org-2" } });

    expect(screen.getByTestId("parent-unit-select-trigger").textContent).toContain("Direction Stratégie & DS3C");
  });
});

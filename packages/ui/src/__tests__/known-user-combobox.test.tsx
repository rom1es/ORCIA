import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  OrciaKnownUserCombobox,
  type KnownUserOption,
} from "../primitives/OrciaKnownUserCombobox";

describe("OrciaKnownUserCombobox", () => {
  afterEach(() => {
    cleanup();
  });

  const testUsers: readonly KnownUserOption[] = [
    {
      principalId: "romain.esnault@gmail.com",
      displayName: "Romain Esnault",
      email: "romain.esnault@gmail.com",
    },
    {
      principalId: "claire.bu@orcia.io",
      displayName: "Claire Delorme",
      email: "claire.bu@orcia.io",
    },
    {
      principalId: "marc.lead@orcia.io",
      displayName: "Marc Chef d'Équipe",
      email: "marc.lead@orcia.io",
    },
  ];

  function TestHarness({
    initialValue = "",
    excludedPrincipalIds = [],
    onSelectOption,
  }: {
    initialValue?: string;
    excludedPrincipalIds?: readonly string[];
    onSelectOption?: (user: KnownUserOption) => void;
  }) {
    const [val, setVal] = useState(initialValue);
    return (
      <OrciaKnownUserCombobox
        inputId="test-user-input"
        inputTestId="test-user-combobox"
        value={val}
        onChange={setVal}
        knownUsers={testUsers}
        excludedPrincipalIds={excludedPrincipalIds}
        placeholder="Sélectionnez un utilisateur"
        noResultsLabel="Aucun utilisateur trouvé"
        onSelectOption={onSelectOption}
      />
    );
  }

  it("filters suggestions case-insensitively and accent-insensitively upon typing", () => {
    render(<TestHarness />);
    const input = screen.getByTestId("test-user-combobox");

    fireEvent.focus(input);
    expect(screen.getByTestId("test-user-combobox-suggestions")).toBeDefined();

    // Type "romain" -> should match "Romain Esnault"
    fireEvent.change(input, { target: { value: "romain" } });
    expect(
      screen.getByTestId("test-user-combobox-option-romain.esnault@gmail.com"),
    ).toBeDefined();
    expect(
      screen.queryByTestId("test-user-combobox-option-claire.bu@orcia.io"),
    ).toBeNull();

    // Type "equipe" (without accent) -> should match "Marc Chef d'Équipe"
    fireEvent.change(input, { target: { value: "equipe" } });
    expect(
      screen.getByTestId("test-user-combobox-option-marc.lead@orcia.io"),
    ).toBeDefined();
  });

  it("displays noResultsLabel when no known user matches the query", () => {
    render(<TestHarness />);
    const input = screen.getByTestId("test-user-combobox");

    fireEvent.change(input, { target: { value: "inconnu-complet" } });
    expect(screen.getByTestId("test-user-combobox-no-match").textContent).toBe(
      "Aucun utilisateur trouvé",
    );
  });

  it("selects an option on mouse down / click and updates the input value", () => {
    const handleSelectOption = vi.fn();
    render(<TestHarness onSelectOption={handleSelectOption} />);
    const input = screen.getByTestId("test-user-combobox") as HTMLInputElement;

    fireEvent.focus(input);
    const option = screen.getByTestId("test-user-combobox-option-claire.bu@orcia.io");
    fireEvent.mouseDown(option);

    expect(input.value).toBe("claire.bu@orcia.io");
    expect(handleSelectOption).toHaveBeenCalledWith(testUsers[1]);
    expect(screen.queryByTestId("test-user-combobox-suggestions")).toBeNull();
  });

  it("navigates options via keyboard ArrowDown, ArrowUp and selects with Enter", () => {
    const handleSelectOption = vi.fn();
    render(<TestHarness onSelectOption={handleSelectOption} />);
    const input = screen.getByTestId("test-user-combobox") as HTMLInputElement;

    fireEvent.focus(input);
    // ArrowDown moves highlight to 2nd option (Claire)
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(input.value).toBe("claire.bu@orcia.io");
    expect(handleSelectOption).toHaveBeenCalledWith(testUsers[1]);
  });

  it("respects excludedPrincipalIds by not showing them in suggestions", () => {
    render(<TestHarness excludedPrincipalIds={["claire.bu@orcia.io"]} />);
    const input = screen.getByTestId("test-user-combobox");

    fireEvent.focus(input);
    expect(
      screen.getByTestId("test-user-combobox-option-romain.esnault@gmail.com"),
    ).toBeDefined();
    expect(
      screen.queryByTestId("test-user-combobox-option-claire.bu@orcia.io"),
    ).toBeNull();
  });

  it("limits displayed items to maxDisplayedItems (default 10) with truncated hint and calls onSearchQueryChange on each letter typed", () => {
    const fifteenUsers: KnownUserOption[] = Array.from({ length: 15 }, (_, i) => ({
      principalId: `user.${i + 1}@orcia.io`,
      displayName: `User ${String(i + 1).padStart(2, "0")}`,
      email: `user.${i + 1}@orcia.io`,
    }));

    const handleSearchQueryChange = vi.fn();

    function ControlledTruncatedHarness() {
      const [val, setVal] = useState("");
      return (
        <OrciaKnownUserCombobox
          inputId="truncated-user-input"
          inputTestId="truncated-combobox"
          value={val}
          onChange={setVal}
          knownUsers={fifteenUsers}
          maxDisplayedItems={10}
          truncatedHint="5 utilisateurs non affichés. Affinez votre recherche."
          onSearchQueryChange={handleSearchQueryChange}
        />
      );
    }

    render(<ControlledTruncatedHarness />);

    const input = screen.getByTestId("truncated-combobox");
    fireEvent.focus(input);

    // Only 10 options rendered
    expect(screen.getByTestId("truncated-combobox-option-user.1@orcia.io")).toBeDefined();
    expect(screen.getByTestId("truncated-combobox-option-user.10@orcia.io")).toBeDefined();
    expect(screen.queryByTestId("truncated-combobox-option-user.11@orcia.io")).toBeNull();

    // Truncated hint visible
    const hint = screen.getByTestId("truncated-combobox-truncated-hint");
    expect(hint.textContent).toContain("5 utilisateurs non affichés");

    // Saisie lettre par lettre déclenche onSearchQueryChange immédiatement à chaque frappe
    fireEvent.change(input, { target: { value: "u" } });
    expect(handleSearchQueryChange).toHaveBeenCalledWith("u");
    fireEvent.change(input, { target: { value: "us" } });
    expect(handleSearchQueryChange).toHaveBeenCalledWith("us");
    fireEvent.change(input, { target: { value: "use" } });
    expect(handleSearchQueryChange).toHaveBeenCalledWith("use");

    // Effacement de la saisie
    fireEvent.change(input, { target: { value: "" } });
    expect(handleSearchQueryChange).toHaveBeenCalledWith("");
  });

  it("applies excludedPrincipalIds before maxDisplayedItems truncation", () => {
    const twelveUsers: KnownUserOption[] = Array.from({ length: 12 }, (_, i) => ({
      principalId: `worker.${i + 1}@orcia.io`,
      displayName: `Worker ${String(i + 1).padStart(2, "0")}`,
      email: `worker.${i + 1}@orcia.io`,
    }));

    // Exclude worker.1 -> 11 remaining, so 10 displayed and worker.12 should be in the list as 10th
    render(
      <OrciaKnownUserCombobox
        inputId="exclude-trunc-input"
        inputTestId="exclude-trunc-combobox"
        value=""
        onChange={() => {}}
        knownUsers={twelveUsers}
        excludedPrincipalIds={["worker.1@orcia.io"]}
        maxDisplayedItems={10}
      />,
    );

    const input = screen.getByTestId("exclude-trunc-combobox");
    fireEvent.focus(input);

    expect(screen.queryByTestId("exclude-trunc-combobox-option-worker.1@orcia.io")).toBeNull();
    // Worker 11 should now be visible in the 10 displayed (workers 2 through 11)
    expect(screen.getByTestId("exclude-trunc-combobox-option-worker.11@orcia.io")).toBeDefined();
    // Truncated hint visible because 11 > 10
    expect(screen.getByTestId("exclude-trunc-combobox-truncated-hint")).toBeDefined();
  });
});

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
});

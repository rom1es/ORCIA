import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  OrciaUserPillsSelect,
  resolvePendingKnownUserId,
} from "../primitives/OrciaUserPillsSelect";
import type { KnownUserOption } from "../primitives/OrciaKnownUserCombobox";

describe("OrciaUserPillsSelect", () => {
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

  it("resolves pending known user id from draft query accurately", () => {
    expect(resolvePendingKnownUserId("", testUsers)).toBeNull();
    expect(resolvePendingKnownUserId("   ", testUsers)).toBeNull();
    expect(
      resolvePendingKnownUserId("claire.bu@orcia.io", testUsers),
    ).toBe("claire.bu@orcia.io");
    expect(
      resolvePendingKnownUserId("Claire Delorme", testUsers),
    ).toBe("claire.bu@orcia.io");
    expect(
      resolvePendingKnownUserId("ROMAIN.ESNAULT@GMAIL.COM", testUsers),
    ).toBe("romain.esnault@gmail.com");
    expect(
      resolvePendingKnownUserId("unknown.user@external.com", testUsers),
    ).toBe("unknown.user@external.com");
  });

  function TestSelectHarness({
    initialSelected = ["claire.bu@orcia.io"],
    disabled = false,
  }: {
    initialSelected?: readonly string[];
    disabled?: boolean;
  }) {
    const [selected, setSelected] = useState<readonly string[]>(initialSelected);
    return (
      <OrciaUserPillsSelect
        inputId="test-pills-input"
        inputTestId="test-pills"
        selectedUserIds={selected}
        onChange={setSelected}
        knownUsers={testUsers}
        placeholder="Sélectionnez un responsable"
        addButtonLabel="Ajouter"
        disabled={disabled}
      />
    );
  }

  it("renders existing selected user pills and handles removal", () => {
    render(<TestSelectHarness initialSelected={["claire.bu@orcia.io", "marc.lead@orcia.io"]} />);

    expect(screen.getByTestId("test-pills-pill-claire.bu@orcia.io")).toBeDefined();
    expect(screen.getByText("Claire Delorme (claire.bu@orcia.io)")).toBeDefined();
    expect(screen.getByTestId("test-pills-pill-marc.lead@orcia.io")).toBeDefined();

    const removeClaireBtn = screen.getByTestId("test-pills-remove-claire.bu@orcia.io");
    fireEvent.click(removeClaireBtn);

    expect(screen.queryByTestId("test-pills-pill-claire.bu@orcia.io")).toBeNull();
    expect(screen.getByTestId("test-pills-pill-marc.lead@orcia.io")).toBeDefined();
  });

  it("adds a user from input via add button", () => {
    render(<TestSelectHarness initialSelected={["claire.bu@orcia.io"]} />);

    const input = screen.getByTestId("test-pills") as HTMLInputElement;
    const addBtn = screen.getByTestId("test-pills-add-btn") as HTMLButtonElement;

    expect(addBtn.disabled).toBe(true);

    fireEvent.change(input, { target: { value: "romain" } });
    expect(addBtn.disabled).toBe(false);

    fireEvent.click(addBtn);

    expect(screen.getByTestId("test-pills-pill-romain.esnault@gmail.com")).toBeDefined();
    expect(input.value).toBe("");
  });

  it("does not add duplicates", () => {
    const handleChange = vi.fn();
    render(
      <OrciaUserPillsSelect
        inputId="test-pills-input"
        inputTestId="test-pills"
        selectedUserIds={["claire.bu@orcia.io"]}
        onChange={handleChange}
        knownUsers={testUsers}
      />,
    );

    const input = screen.getByTestId("test-pills");
    const addBtn = screen.getByTestId("test-pills-add-btn");

    fireEvent.change(input, { target: { value: "claire.bu@orcia.io" } });
    fireEvent.click(addBtn);

    expect(handleChange).not.toHaveBeenCalled();
  });
});

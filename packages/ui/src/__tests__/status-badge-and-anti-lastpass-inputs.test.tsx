import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { OrciaKnownUserCombobox } from "../primitives/OrciaKnownUserCombobox";
import { OrciaSearchableSelect } from "../primitives/OrciaSearchableSelect";
import { StatusBadge } from "../primitives/StatusBadge";

describe("StatusBadge Cobalt Tone & Anti-LastPass Input Hardening", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders StatusBadge with pastel cobalt CSS variables for tone='cobalt'", () => {
    render(<StatusBadge testId="test-cobalt-badge" label="Direction Produit" tone="cobalt" />);
    const badge = screen.getByTestId("test-cobalt-badge");
    expect(badge.getAttribute("data-tone")).toBe("cobalt");
    expect(badge.style.backgroundColor).toBe("var(--color-badge-cobalt-bg)");
    expect(badge.style.color).toBe("var(--color-badge-cobalt-fg)");
    expect(badge.style.border).toBe("1px solid var(--color-badge-cobalt-border)");
  });

  it("enforces type='search', neutral name, and comprehensive anti-extension attributes on OrciaKnownUserCombobox", () => {
    render(
      <OrciaKnownUserCombobox
        inputId="test-user-input"
        inputTestId="test-user-combobox"
        value=""
        onChange={() => {}}
        knownUsers={[{ principalId: "u1", displayName: "User 1" }]}
      />,
    );
    const input = screen.getByTestId("test-user-combobox");
    expect(input.getAttribute("type")).toBe("search");
    expect(input.getAttribute("name")).toBe("orcia_directory_filter_q");
    expect(input.getAttribute("autoComplete")).toBe("off");
    expect(input.getAttribute("autoCorrect")).toBe("off");
    expect(input.getAttribute("autoCapitalize")).toBe("none");
    expect(input.getAttribute("spellCheck")).toBe("false");
    expect(input.getAttribute("data-lpignore")).toBe("true");
    expect(input.getAttribute("data-1p-ignore")).toBe("true");
    expect(input.getAttribute("data-bwignore")).toBe("true");
    expect(input.getAttribute("data-protonpass-ignore")).toBe("true");
    expect(input.getAttribute("data-form-type")).toBe("other");
  });

  it("enforces type='search', neutral name, and comprehensive anti-extension attributes on OrciaSearchableSelect", () => {
    render(
      <OrciaSearchableSelect
        testId="test-search-select"
        value="opt-1"
        onChange={() => {}}
        options={[{ value: "opt-1", label: "Option 1" }]}
        searchPlaceholder="Rechercher..."
        noMatchLabel="Aucun résultat"
      />,
    );
    fireEvent.click(screen.getByTestId("test-search-select-trigger"));
    const searchInput = screen.getByTestId("test-search-select-search-input");
    expect(searchInput.getAttribute("type")).toBe("search");
    expect(searchInput.getAttribute("name")).toBe("orcia_select_filter_q");
    expect(searchInput.getAttribute("autoComplete")).toBe("off");
    expect(searchInput.getAttribute("autoCorrect")).toBe("off");
    expect(searchInput.getAttribute("autoCapitalize")).toBe("none");
    expect(searchInput.getAttribute("spellCheck")).toBe("false");
    expect(searchInput.getAttribute("data-lpignore")).toBe("true");
    expect(searchInput.getAttribute("data-1p-ignore")).toBe("true");
    expect(searchInput.getAttribute("data-bwignore")).toBe("true");
    expect(searchInput.getAttribute("data-protonpass-ignore")).toBe("true");
    expect(searchInput.getAttribute("data-form-type")).toBe("other");
  });
});

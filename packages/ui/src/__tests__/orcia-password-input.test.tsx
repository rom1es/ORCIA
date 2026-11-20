import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OrciaPasswordInput } from "../primitives/OrciaPasswordInput";

describe("OrciaPasswordInput — mask modes, eye reveal toggle, i18n labels & zero dot placeholder", () => {
  afterEach(() => {
    cleanup();
  });

  it("uses masked-text mode by default with anti-manager attributes, zero dot placeholder, and eye visibility toggle", () => {
    const onChange = vi.fn();
    render(
      <OrciaPasswordInput
        id="secret-field"
        testId="secret-input"
        value="MonSecret!2026"
        onChange={onChange}
        showPasswordLabel="Afficher le mot de passe" // pragma: allowlist secret
        hidePasswordLabel="Masquer le mot de passe" // pragma: allowlist secret
      />,
    );

    const input = screen.getByTestId("secret-input") as HTMLInputElement;
    const toggle = screen.getByTestId("secret-input-toggle-visibility") as HTMLButtonElement;

    expect(input.type).toBe("text");
    expect(input.placeholder).toBe("");
    expect(input.placeholder).not.toContain("•");
    expect(input.className).toContain("orcia-masked-secret-input");
    expect(input.getAttribute("autoComplete")).toBe("off");
    expect(input.getAttribute("data-lpignore")).toBe("true");
    expect(input.getAttribute("data-1p-ignore")).toBe("true");
    expect(input.getAttribute("data-bwignore")).toBe("true");
    expect(input.getAttribute("data-form-type")).toBe("other");

    expect(toggle.getAttribute("aria-pressed")).toBe("false");
    expect(toggle.getAttribute("aria-label")).toBe("Afficher le mot de passe");
    expect(toggle.getAttribute("title")).toBe("Afficher le mot de passe");

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-pressed")).toBe("true");
    expect(toggle.getAttribute("aria-label")).toBe("Masquer le mot de passe");
    expect(toggle.getAttribute("title")).toBe("Masquer le mot de passe");
    expect(input.className).not.toContain("orcia-masked-secret-input");
    expect((input.style as unknown as Record<string, string>).WebkitTextSecurity).toBe("none");

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-pressed")).toBe("false");
    expect(input.className).toContain("orcia-masked-secret-input");

    fireEvent.change(input, { target: { value: "NouveauSecret!2026" } });
    expect(onChange).toHaveBeenCalledWith("NouveauSecret!2026");
  });

  it("supports native maskMode='password' for login forms and custom toggleTestId / disabled state", () => {
    render(
      <OrciaPasswordInput
        testId="login-pw-input"
        toggleTestId="login-pw-toggle"
        maskMode="password"
        value="LoginPass!2026"
        onChange={() => {}}
        showPasswordLabel="Show password" // pragma: allowlist secret
        hidePasswordLabel="Hide password" // pragma: allowlist secret
      />,
    );

    const input = screen.getByTestId("login-pw-input") as HTMLInputElement;
    const toggle = screen.getByTestId("login-pw-toggle") as HTMLButtonElement;

    expect(input.type).toBe("password");
    expect(input.placeholder).toBe("");
    expect(input.getAttribute("autoComplete")).toBe("current-password");
    expect(input.className).not.toContain("orcia-masked-secret-input");

    fireEvent.click(toggle);
    expect(input.type).toBe("text");
    expect(toggle.getAttribute("aria-pressed")).toBe("true");
    expect(toggle.getAttribute("aria-label")).toBe("Hide password");

    fireEvent.click(toggle);
    expect(input.type).toBe("password");
    expect(toggle.getAttribute("aria-pressed")).toBe("false");

    cleanup();

    render(
      <OrciaPasswordInput
        testId="disabled-pw-input"
        value=""
        onChange={() => {}}
        disabled={true}
        showPasswordLabel="Afficher" // pragma: allowlist secret
        hidePasswordLabel="Masquer" // pragma: allowlist secret
      />,
    );
    expect((screen.getByTestId("disabled-pw-input") as HTMLInputElement).disabled).toBe(true);
    expect(
      (screen.getByTestId("disabled-pw-input-toggle-visibility") as HTMLButtonElement).disabled,
    ).toBe(true);
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  TemporaryPasswordInvitationModal,
  UserPasswordChangeCard,
} from "../index";

describe("TemporaryPasswordInvitationModal & UserPasswordChangeCard (@orcia/ui)", () => {
  it("renders TemporaryPasswordInvitationModal with 12-char value, ready-to-copy textarea, and action buttons", () => {
    const handleClose = vi.fn();
    const handleRegenerate = vi.fn().mockResolvedValue("NewSecret123"); // pragma: allowlist secret

    render(
      <TemporaryPasswordInvitationModal
        isOpen={true}
        isFr={true}
        displayName="Claire Martin"
        email="claire.martin@entreprise.fr"
        temporaryPassword="TempSecret12" // pragma: allowlist secret
        orciaUrl="http://localhost:3100"
        onClose={handleClose}
        onRegeneratePassword={handleRegenerate}
      />,
    );

    expect(screen.getByTestId("temp-password-modal")).toBeDefined();
    expect(
      screen.getByTestId("temp-password-generated-value").textContent,
    ).toBe("TempSecret12"); // pragma: allowlist secret

    const textarea = screen.getByTestId(
      "temp-password-invitation-textarea",
    ) as HTMLTextAreaElement;
    expect(textarea.value).toContain("Bonjour Claire Martin,");
    expect(textarea.value).toContain("Identifiant : claire.martin@entreprise.fr");
    expect(textarea.value).toContain("Mot de passe temporaire : TempSecret12"); // pragma: allowlist secret
    expect(textarea.value).toContain("Connectez-vous sur http://localhost:3100");
    expect(textarea.value).toContain(
      "N'oubliez pas de changer votre mot de passe dès votre première connexion.",
    );

    fireEvent.click(screen.getByTestId("temp-password-regenerate-btn"));
    expect(handleRegenerate).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId("temp-password-close-btn"));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("renders UserPasswordChangeCard with anti-LastPass masked inputs and validates submission", async () => {
    const handleChangePassword = vi.fn().mockResolvedValue({ success: true });

    render(
      <UserPasswordChangeCard
        mustChangePassword={true}
        onChangePassword={handleChangePassword}
      />,
    );

    const card = screen.getByTestId("user-password-change-card");
    expect(card).toBeDefined();

    const currentInput = screen.getByTestId(
      "user-current-password-input",
    ) as HTMLInputElement;
    const newInput = screen.getByTestId(
      "user-new-password-input",
    ) as HTMLInputElement;
    const confirmInput = screen.getByTestId(
      "user-confirm-password-input",
    ) as HTMLInputElement;

    // Anti-LastPass attributes
    expect(currentInput.getAttribute("type")).toBe("text");
    expect(currentInput.className).toContain("orcia-masked-secret-input");
    expect(currentInput.getAttribute("data-lpignore")).toBe("true");

    // Passwords mismatch validation
    fireEvent.change(currentInput, { target: { value: "OldPassword123" } }); // pragma: allowlist secret
    fireEvent.change(newInput, { target: { value: "NewSecurePassword2026" } }); // pragma: allowlist secret
    fireEvent.change(confirmInput, { target: { value: "Mismatch12345" } }); // pragma: allowlist secret

    fireEvent.click(screen.getByTestId("user-change-password-submit-btn"));
    expect(handleChangePassword).not.toHaveBeenCalled();

    // Matching valid passwords
    fireEvent.change(confirmInput, { target: { value: "NewSecurePassword2026" } }); // pragma: allowlist secret
    fireEvent.click(screen.getByTestId("user-change-password-submit-btn"));
    expect(handleChangePassword).toHaveBeenCalledWith(
      "OldPassword123", // pragma: allowlist secret
      "NewSecurePassword2026", // pragma: allowlist secret
    );
  });
});

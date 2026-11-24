import { fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import {
  OrciaModelCombobox,
  type DiscoveredModelOption,
  type OrciaModelComboboxLabels,
} from "../primitives/OrciaModelCombobox";

const mockLabels: OrciaModelComboboxLabels = {
  noModelsFound: "Aucun modèle trouvé",
  refreshLabel: "Découvrir les modèles",
  loadingLabel: "Découverte...",
  toggleListAriaLabel: "Toggle models list",
  freeformHint: "Vous pouvez saisir un identifiant librement",
  chatBadge: "Chat",
  embeddingBadge: "Embedding",
};

const sampleModels: readonly DiscoveredModelOption[] = [
  { id: "gpt-4o", displayName: "GPT-4o Omnimodel", usageHint: "chat" },
  { id: "gpt-4o-mini", displayName: "GPT-4o Mini", usageHint: "chat" },
  { id: "text-embedding-3-small", displayName: "Embedding Small", usageHint: "embedding" },
  { id: "custom-generic-model", displayName: "Generic Model", usageHint: "unknown" },
];

function TestHarness({
  initialValue = "",
  models = sampleModels,
  targetUsage,
  isLoading = false,
  errorMessage = null,
  onRefresh,
}: {
  initialValue?: string;
  models?: readonly DiscoveredModelOption[];
  targetUsage?: "chat" | "embedding";
  isLoading?: boolean;
  errorMessage?: string | null;
  onRefresh?: () => void;
}) {
  const [val, setVal] = useState(initialValue);
  return (
    <OrciaModelCombobox
      testId="test-model-combobox"
      value={val}
      onChange={setVal}
      models={models}
      targetUsage={targetUsage}
      isLoading={isLoading}
      errorMessage={errorMessage}
      onRefresh={onRefresh}
      placeholder="Sélectionner ou saisir un modèle..."
      labels={mockLabels}
    />
  );
}

describe("OrciaModelCombobox", () => {
  it("renders input field and allows freeform typing", () => {
    render(<TestHarness initialValue="" />);
    const input = screen.getByTestId("test-model-combobox") as HTMLInputElement;
    expect(input).toBeDefined();
    expect(input.value).toBe("");

    fireEvent.change(input, { target: { value: "my-custom-unlisted-model" } });
    expect(input.value).toBe("my-custom-unlisted-model");
  });

  it("filters suggestions by targetUsage chat vs embedding", () => {
    // Chat usage should show chat and unknown models, but NOT embedding
    const { rerender } = render(<TestHarness targetUsage="chat" initialValue="" />);
    const input = screen.getByTestId("test-model-combobox");
    fireEvent.focus(input);

    expect(screen.getByTestId("test-model-combobox-option-gpt-4o")).toBeDefined();
    expect(screen.getByTestId("test-model-combobox-option-custom-generic-model")).toBeDefined();
    expect(screen.queryByTestId("test-model-combobox-option-text-embedding-3-small")).toBeNull();

    // Embedding usage should show embedding and unknown models, but NOT chat
    rerender(<TestHarness targetUsage="embedding" initialValue="" />);
    fireEvent.focus(input);

    expect(screen.getByTestId("test-model-combobox-option-text-embedding-3-small")).toBeDefined();
    expect(screen.getByTestId("test-model-combobox-option-custom-generic-model")).toBeDefined();
    expect(screen.queryByTestId("test-model-combobox-option-gpt-4o")).toBeNull();
  });

  it("selects model option on click and updates value", () => {
    render(<TestHarness initialValue="" />);
    const input = screen.getByTestId("test-model-combobox") as HTMLInputElement;
    fireEvent.focus(input);

    const option = screen.getByTestId("test-model-combobox-option-gpt-4o");
    fireEvent.mouseDown(option);

    expect(input.value).toBe("gpt-4o");
    // Dropdown should be closed after selection
    expect(screen.queryByTestId("test-model-combobox-suggestions")).toBeNull();
  });

  it("displays loading indicator and triggers onRefresh callback", () => {
    const handleRefresh = vi.fn();
    const { rerender } = render(
      <TestHarness isLoading={true} onRefresh={handleRefresh} initialValue="" />,
    );

    expect(screen.getByTestId("test-model-combobox-loading-indicator")).toBeDefined();
    expect(screen.getByText("Découverte...")).toBeDefined();

    const refreshBtn = screen.getByTestId("test-model-combobox-refresh-btn");
    // When loading, refresh button is disabled
    expect((refreshBtn as HTMLButtonElement).disabled).toBe(true);

    rerender(<TestHarness isLoading={false} onRefresh={handleRefresh} initialValue="" />);
    const activeRefreshBtn = screen.getByTestId("test-model-combobox-refresh-btn");
    expect((activeRefreshBtn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(activeRefreshBtn);
    expect(handleRefresh).toHaveBeenCalledTimes(1);
  });

  it("displays error message explicitly without hiding manual input", () => {
    render(<TestHarness errorMessage="Clé d'API invalide" initialValue="" />);
    expect(screen.getByTestId("test-model-combobox-error-msg")).toBeDefined();
    expect(screen.getByText("Clé d'API invalide")).toBeDefined();

    // Input remains perfectly usable
    const input = screen.getByTestId("test-model-combobox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "fallback-model" } });
    expect(input.value).toBe("fallback-model");
  });
});

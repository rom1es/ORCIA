import { describe, expect, it } from "vitest";
import { resolveEffectiveLlmProtocolMode } from "../routes/settingsAiModelsPresets";

describe("resolveEffectiveLlmProtocolMode", () => {
  it("resolves Gemini Mode B (/v1beta) to gemini_native", () => {
    expect(
      resolveEffectiveLlmProtocolMode(
        "Google Gemini",
        "https://generativelanguage.googleapis.com/v1beta",
      ),
    ).toBe("gemini_native");
  });

  it("resolves Gemini Mode A (/v1beta/openai) to openai_compatible", () => {
    expect(
      resolveEffectiveLlmProtocolMode(
        "Google Gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
      ),
    ).toBe("openai_compatible");
  });

  it("resolves Anthropic family or endpoint to anthropic_messages", () => {
    expect(
      resolveEffectiveLlmProtocolMode("Anthropic", "https://api.anthropic.com/v1"),
    ).toBe("anthropic_messages");
    expect(
      resolveEffectiveLlmProtocolMode("Custom", "https://proxy.example.com/v1/messages"),
    ).toBe("anthropic_messages");
  });

  it("falls back to provided mode for OpenAI-compatible providers", () => {
    expect(
      resolveEffectiveLlmProtocolMode("OpenAI", "https://api.openai.com/v1"),
    ).toBe("openai_compatible");
    expect(
      resolveEffectiveLlmProtocolMode("Custom", "http://localhost:11434/v1", "gemini_native"),
    ).toBe("gemini_native");
  });
});

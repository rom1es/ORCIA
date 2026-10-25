#!/usr/bin/env python3
"""Optional AI Security & Architecture Pre-Commit Reviewer for ORCIA (adapted from StoreMirror).

Controlled via environment variable:
- AI_MODE="OFF" (default): no-op, exits 0 immediately.
- AI_MODE="OLLAMA": queries local Ollama instance (OLLAMA_MODEL, default 'gemma-security').
- AI_MODE="GEMINI": queries Gemini API (requires GEMINI_API_KEY).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)

AI_MODE = os.environ.get("AI_MODE", "OFF").upper()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma-security")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = os.environ.get("OLLAMA_PORT", "11434")
OLLAMA_URL = os.environ.get("OLLAMA_URL", f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate")


def get_git_diff() -> str:
    """Retrieve staged changes (or unstaged changes as fallback) for review."""
    try:
        diff = subprocess.check_output(["git", "diff", "--cached"], text=True)
        if not diff.strip():
            diff = subprocess.check_output(["git", "diff"], text=True)
        return diff
    except Exception as exc:
        return f"Git Error: {exc}"


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def ask_ollama(diff: str, prompt: str) -> str:
    """Query local Ollama instance."""
    url = OLLAMA_URL
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{prompt}\n\nDIFF TO ANALYZE:\n{diff}",
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=300)
        data = response.json()
        return str(data.get("response", "Error: No response from Ollama."))
    except Exception as exc:
        return f"Ollama Error: {exc}. Is Ollama running and model '{OLLAMA_MODEL}' created?"


def ask_gemini(diff: str, prompt: str) -> str:
    """Query Google Gemini Cloud API."""
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY environment variable is not set."
    try:
        from google import genai  # type: ignore[import-not-found]

        client = genai.Client(api_key=GEMINI_API_KEY)
        model_id = "gemini-2.0-flash"
        response = client.models.generate_content(
            model=model_id,
            contents=f"{prompt}\n\nDIFF TO ANALYZE:\n{diff}",
        )
        return str(response.text)
    except Exception as exc:
        return f"Gemini API Error: {exc}"


def main() -> int:
    if AI_MODE == "OFF":
        print("[IA] Review disabled (AI_MODE=OFF). Skipping...")
        return 0

    diff_content = get_git_diff()
    if not diff_content or len(diff_content.strip()) < 10:
        print("No significant changes to review.")
        return 0

    tokens = estimate_tokens(diff_content)
    model_name = OLLAMA_MODEL if AI_MODE == "OLLAMA" else "gemini-2.0-flash"

    print(f"\n[IA] Mode: {AI_MODE}")
    print(f"[IA] Model: {model_name}")
    print(f"[IA] Estimated size: ~{tokens} tokens")
    print("[IA] Reviewing code...\n")

    system_prompt = (
        "You are a Senior Security & Hexagonal Architecture Engineer on ORCIA. "
        "Review this git diff for SQL injection, append-only ledger/snapshot violations, "
        "RBAC ScopeAccessGuard bypasses, hexagonal boundary leaks, and performance. "
        "Be very technical and concise."
    )

    result = (
        ask_gemini(diff_content, system_prompt)
        if AI_MODE == "GEMINI"
        else ask_ollama(diff_content, system_prompt)
    )

    print("=" * 50)
    print("            AI SECURITY REVIEW REPORT")
    print("=" * 50)
    print(result)
    print("=" * 50 + "\n")

    Path("IA_REVIEW.md").write_text(
        f"# 🔍 AI Security Review Report\n\n*Mode: {AI_MODE} | Tokens: ~{tokens}*\n\n"
        f"---\n\n{result}",
        encoding="utf-8",
    )
    print("✅ AI Review generated in IA_REVIEW.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

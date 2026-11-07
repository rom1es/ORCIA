import React, { useState } from "react";

export interface FormattedMarkdownContentProps {
  readonly content: string;
  readonly className?: string;
  readonly testId?: string;
}

interface ParsedMarkdownBlock {
  readonly kind: "heading" | "code" | "ul" | "ol" | "paragraph";
  readonly level?: 1 | 2 | 3 | 4;
  readonly language?: string;
  readonly text?: string;
  readonly items?: readonly string[];
}

function normalizeCodeBlockContent(rawCode: string, language: string): string {
  const trimmed = rawCode.trim();
  if (!trimmed) {
    return "";
  }
  if (trimmed.includes("\n")) {
    return trimmed;
  }

  const lang = language.toLowerCase();
  if (lang === "python" || lang === "py" || !lang) {
    let expanded = trimmed
      // Ensure comment markers start on a new line when preceded by code
      .replace(/\s+(#\s+)/g, "\n$1")
      // Ensure top-level keywords start on a new line
      .replace(/\s+(def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\()/g, "\n$1")
      .replace(/\s+(class\s+[a-zA-Z_][a-zA-Z0-9_]*)/g, "\n$1")
      .replace(/\s+(import\s+[a-zA-Z_])/g, "\n$1")
      .replace(/\s+(from\s+[a-zA-Z_])/g, "\n$1")
      .replace(/\s+(print\s*\()/g, "\n$1")
      // Ensure suite statements after a colon are placed on indented new lines
      .replace(/:\s+(if\s+|elif\s+|else\s*:|for\s+|while\s+|return\b|resultat\s*=)/g, ":\n    $1")
      .replace(/\s+(else\s*:)/g, "\n    $1")
      .replace(/\s+(elif\s+)/g, "\n    $1")
      .replace(/\s+(return\s+)/g, "\n        return ");

    // Normalize indentation cleanly line by line
    const rawLines = expanded
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    let indentLevel = 0;
    const formattedLines: string[] = [];

    for (const line of rawLines) {
      if (
        line.startsWith("def ") ||
        line.startsWith("class ") ||
        line.startsWith("import ") ||
        line.startsWith("from ") ||
        line.startsWith("print(") ||
        line.startsWith("# Exemple") ||
        line.startsWith("# Cas")
      ) {
        if (line.startsWith("def ") || line.startsWith("class ") || line.startsWith("print(")) {
          indentLevel = 0;
        }
      } else if (line.startsWith("else:") || line.startsWith("elif ")) {
        indentLevel = Math.max(1, indentLevel - 1);
      }

      const prefix = "    ".repeat(indentLevel);
      formattedLines.push(`${prefix}${line}`);

      if (line.endsWith(":")) {
        indentLevel = Math.min(3, indentLevel + 1);
      } else if (line.startsWith("return ")) {
        indentLevel = Math.max(1, indentLevel - 1);
      }
    }

    return formattedLines.join("\n");
  }

  return trimmed;
}

function normalizeInlineMarkdownSpacing(raw: string): string {
  // Extract fenced code blocks first so we don't alter `#` comments inside code
  const codePlaceholders: string[] = [];
  const withPlaceholders = raw.replace(/```([a-zA-Z0-9_-]*)\s*([\s\S]*?)```/g, (_match, lang, body) => {
    const idx = codePlaceholders.length;
    const normalizedCode = normalizeCodeBlockContent(String(body ?? ""), String(lang ?? ""));
    codePlaceholders.push(`\`\`\`${String(lang ?? "").trim()}\n${normalizedCode}\n\`\`\``);
    return `\n@@ORCIA_CODE_BLOCK_${idx}@@\n`;
  });

  const normalizedText = withPlaceholders
    // Split headings that appear mid-line (e.g. `... optimisée. ### 1. Méthode`)
    .replace(/([^\n])\s+(#{1,4}\s+)/g, "$1\n\n$2")
    // Split bullet items `* **Terme**`, `* *Terme*`, `- **Terme**`, `- *Terme*` glued on the same line
    .replace(/([^\n])\s+(\*\s+\*{1,2}[A-Za-zÀ-ÖØ-öø-ÿ0-9])/g, "$1\n$2")
    .replace(/([^\n])\s+(-\s+\*{1,2}[A-Za-zÀ-ÖØ-öø-ÿ0-9])/g, "$1\n$2");

  return normalizedText.replace(/@@ORCIA_CODE_BLOCK_(\d+)@@/g, (_m, idxStr) => {
    const idx = Number(idxStr);
    return codePlaceholders[idx] ?? "";
  });
}

export function parseMarkdownBlocks(rawContent: string): ParsedMarkdownBlock[] {
  if (!rawContent || !rawContent.trim()) {
    return [];
  }

  const normalized = normalizeInlineMarkdownSpacing(rawContent);
  const segments = normalized.split(/(```[a-zA-Z0-9_-]*\n[\s\S]*?\n```)/g);
  const blocks: ParsedMarkdownBlock[] = [];

  for (const segment of segments) {
    if (!segment.trim()) {
      continue;
    }

    const codeMatch = /^```([a-zA-Z0-9_-]*)\n([\s\S]*?)\n```$/.exec(segment.trim());
    if (codeMatch) {
      blocks.push({
        kind: "code",
        language: (codeMatch[1] || "code").trim(),
        text: (codeMatch[2] || "").trimEnd(),
      });
      continue;
    }

    const lines = segment.split("\n");
    let currentParagraph: string[] = [];
    let currentListKind: "ul" | "ol" | null = null;
    let currentListItems: string[] = [];

    const flushParagraph = () => {
      if (currentParagraph.length > 0) {
        const joined = currentParagraph.join(" ").trim();
        if (joined) {
          blocks.push({ kind: "paragraph", text: joined });
        }
        currentParagraph = [];
      }
    };

    const flushList = () => {
      if (currentListKind && currentListItems.length > 0) {
        blocks.push({
          kind: currentListKind,
          items: [...currentListItems],
        });
      }
      currentListKind = null;
      currentListItems = [];
    };

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) {
        flushParagraph();
        flushList();
        continue;
      }

      const headingMatch = /^(#{1,4})\s+(.+)$/.exec(line);
      if (headingMatch) {
        flushParagraph();
        flushList();
        const hashes = headingMatch[1]?.length ?? 3;
        const level = Math.min(4, Math.max(1, hashes)) as 1 | 2 | 3 | 4;
        blocks.push({
          kind: "heading",
          level,
          text: (headingMatch[2] ?? "").trim(),
        });
        continue;
      }

      const ulMatch = /^(?:[-*•])\s+(.+)$/.exec(line);
      if (ulMatch) {
        flushParagraph();
        if (currentListKind && currentListKind !== "ul") {
          flushList();
        }
        currentListKind = "ul";
        currentListItems.push((ulMatch[1] ?? "").trim());
        continue;
      }

      const olMatch = /^\d+\.\s+(.+)$/.exec(line);
      if (olMatch) {
        flushParagraph();
        if (currentListKind && currentListKind !== "ol") {
          flushList();
        }
        currentListKind = "ol";
        currentListItems.push((olMatch[1] ?? "").trim());
        continue;
      }

      flushList();
      currentParagraph.push(line);
    }

    flushParagraph();
    flushList();
  }

  return blocks;
}

export function renderInlineMarkdownNodes(text: string): React.ReactNode[] {
  if (!text) {
    return [];
  }
  const tokenPattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*\n]+\*)/g;
  const parts = text.split(tokenPattern);
  return parts
    .filter((part) => part.length > 0)
    .map((part, idx) => {
      if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
        return (
          <code
            key={`code-${idx}`}
            className="rounded border border-border-subtle bg-surface-secondary px-1.5 py-0.5 font-mono text-[11px] text-text-primary"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return (
          <strong key={`strong-${idx}`} className="font-semibold text-text-primary">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
        return (
          <em key={`em-${idx}`} className="italic">
            {part.slice(1, -1)}
          </em>
        );
      }
      return <React.Fragment key={`txt-${idx}`}>{part}</React.Fragment>;
    });
}

export function FormattedMarkdownContent({
  content,
  className = "",
  testId = "formatted-markdown-content",
}: FormattedMarkdownContentProps): React.JSX.Element {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const blocks = parseMarkdownBlocks(content);

  const handleCopyCode = (codeText: string, index: number) => {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(codeText).catch(() => undefined);
    }
    setCopiedIndex(index);
  };

  return (
    <div
      data-testid={testId}
      className={`space-y-2.5 text-xs leading-relaxed text-text-primary ${className}`.trim()}
    >
      {blocks.map((block, idx) => {
        if (block.kind === "heading") {
          if (block.level === 1 || block.level === 2) {
            return (
              <h2
                key={`h2-${idx}`}
                className="pt-1 text-sm font-semibold tracking-tight text-text-primary"
              >
                {renderInlineMarkdownNodes(block.text ?? "")}
              </h2>
            );
          }
          if (block.level === 3) {
            return (
              <h3
                key={`h3-${idx}`}
                className="pt-1 text-xs font-semibold text-text-primary"
              >
                {renderInlineMarkdownNodes(block.text ?? "")}
              </h3>
            );
          }
          return (
            <h4
              key={`h4-${idx}`}
              className="pt-0.5 text-xs font-semibold text-text-secondary"
            >
              {renderInlineMarkdownNodes(block.text ?? "")}
            </h4>
          );
        }

        if (block.kind === "code") {
          const langLabel = block.language || "code";
          const codeBody = block.text ?? "";
          return (
            <div
              key={`codeblock-${idx}`}
              data-testid="markdown-code-block"
              className="overflow-hidden rounded-lg border border-border-subtle bg-surface-elevated"
            >
              <div className="flex items-center justify-between border-b border-border-subtle bg-surface-secondary px-3 py-1 text-[11px] font-mono text-text-secondary">
                <span>{langLabel}</span>
                <button
                  type="button"
                  data-testid={`markdown-copy-code-btn-${idx}`}
                  onClick={() => handleCopyCode(codeBody, idx)}
                  className="rounded border border-border-subtle bg-surface-primary px-2 py-0.5 font-sans text-[10px] font-medium text-text-primary hover:bg-surface-elevated"
                >
                  {copiedIndex === idx ? "✓ Copié" : "Copier"}
                </button>
              </div>
              <pre className="overflow-x-auto p-3 font-mono text-[11px] leading-relaxed text-text-primary">
                <code>{codeBody}</code>
              </pre>
            </div>
          );
        }

        if (block.kind === "ul") {
          return (
            <ul key={`ul-${idx}`} className="list-disc space-y-1 pl-5">
              {(block.items ?? []).map((item, itemIdx) => (
                <li key={`uli-${itemIdx}`}>{renderInlineMarkdownNodes(item)}</li>
              ))}
            </ul>
          );
        }

        if (block.kind === "ol") {
          return (
            <ol key={`ol-${idx}`} className="list-decimal space-y-1 pl-5">
              {(block.items ?? []).map((item, itemIdx) => (
                <li key={`oli-${itemIdx}`}>{renderInlineMarkdownNodes(item)}</li>
              ))}
            </ol>
          );
        }

        return (
          <p key={`p-${idx}`} className="leading-relaxed">
            {renderInlineMarkdownNodes(block.text ?? "")}
          </p>
        );
      })}
    </div>
  );
}

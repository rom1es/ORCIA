export interface ParsedMarkdownBlock {
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
    const expanded = trimmed
      .replace(/\s+(#\s+)/g, "\n$1")
      .replace(/\s+(def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\()/g, "\n$1")
      .replace(/\s+(class\s+[a-zA-Z_][a-zA-Z0-9_]*)/g, "\n$1")
      .replace(/\s+(import\s+[a-zA-Z_])/g, "\n$1")
      .replace(/\s+(from\s+[a-zA-Z_])/g, "\n$1")
      .replace(/\s+(print\s*\()/g, "\n$1")
      .replace(/:\s+(if\s+|elif\s+|else\s*:|for\s+|while\s+|return\b|resultat\s*=)/g, ":\n    $1")
      .replace(/\s+(else\s*:)/g, "\n    $1")
      .replace(/\s+(elif\s+)/g, "\n    $1")
      .replace(/\s+(return\s+)/g, "\n        return ");

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
  const codePlaceholders: string[] = [];
  const withPlaceholders = raw.replace(/```([a-zA-Z0-9_-]*)\s*([\s\S]*?)```/g, (_match, lang, body) => {
    const idx = codePlaceholders.length;
    const normalizedCode = normalizeCodeBlockContent(String(body ?? ""), String(lang ?? ""));
    codePlaceholders.push(`\`\`\`${String(lang ?? "").trim()}\n${normalizedCode}\n\`\`\``);
    return `\n@@ORCIA_CODE_BLOCK_${idx}@@\n`;
  });

  const normalizedText = withPlaceholders
    .replace(/([^\n])\s+(#{1,4}\s+)/g, "$1\n\n$2")
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

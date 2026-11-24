import React, { useState } from "react";
import { OrciaIcon } from "./icons";
import { parseMarkdownBlocks } from "./markdownBlockParser";

export { parseMarkdownBlocks };

export interface FormattedMarkdownContentProps {
  readonly content: string;
  readonly className?: string;
  readonly testId?: string;
  readonly copyLabel?: string;
  readonly copiedLabel?: string;
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
  copyLabel,
  copiedLabel,
}: FormattedMarkdownContentProps): React.JSX.Element {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const blocks = parseMarkdownBlocks(content);

  const handleCopyCode = (codeText: string, index: number) => {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(codeText).catch((err: unknown) => {
        if (typeof console !== "undefined") {
          console.debug("[orcia:clipboard]", err instanceof Error ? err.message : String(err));
        }
      });
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
                  {copiedIndex === idx ? (
                    <>
                      <OrciaIcon name="check" />
                      {copiedLabel ? ` ${copiedLabel}` : null}
                    </>
                  ) : (
                    <>
                      <OrciaIcon name="copy" />
                      {copyLabel ? ` ${copyLabel}` : null}
                    </>
                  )}
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

export function ignoreBenignStorageError(scope: string, error: unknown): void {
  if (typeof process === "undefined" || process.env?.NODE_ENV !== "test") {
    console.debug(`[orcia:${scope}]`, error instanceof Error ? error.message : String(error));
  }
}

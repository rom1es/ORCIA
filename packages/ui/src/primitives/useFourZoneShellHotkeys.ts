import { useEffect } from "react";

export function useFourZoneShellHotkeys(params: {
  readonly onToggleRailCollapsed: () => void;
  readonly onEscapeClose: () => void;
}): void {
  const { onToggleRailCollapsed, onEscapeClose } = params;

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement | null;
      const isEditable =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        Boolean(target?.isContentEditable);
      const hasOpenModalDialog = Array.from(
        document.querySelectorAll('[aria-modal="true"]'),
      ).some((el) => el.getAttribute("role") === "dialog");
      if (event.key === "[" && !isEditable && !hasOpenModalDialog) {
        onToggleRailCollapsed();
      } else if (event.key === "Escape") {
        onEscapeClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onToggleRailCollapsed, onEscapeClose]);
}

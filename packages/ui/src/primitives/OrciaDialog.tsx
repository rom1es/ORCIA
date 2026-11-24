import * as DialogPrimitive from "@radix-ui/react-dialog";
import React from "react";

export interface OrciaDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly title: string;
  readonly description?: string;
  readonly testId?: string;
  readonly closeLabel?: string;
  readonly closeButtonTestId?: string;
  readonly hideHeaderCloseButton?: boolean;
  readonly headerExtra?: React.ReactNode;
  readonly contentClassName?: string;
  readonly modal?: boolean;
  readonly onEscapeKeyDown?: (event: KeyboardEvent) => void;
  readonly onInteractOutside?: (event: Event) => void;
  readonly children: React.ReactNode;
}

export function OrciaDialog({
  open,
  onOpenChange,
  title,
  description,
  testId = "orcia-radix-dialog",
  closeLabel = "",
  closeButtonTestId,
  hideHeaderCloseButton = false,
  headerExtra,
  contentClassName,
  modal = true,
  onEscapeKeyDown,
  onInteractOutside,
  children,
}: OrciaDialogProps): React.ReactElement {
  const descriptionId = React.useId();
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange} modal={modal}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="orcia-ds-dialog-overlay" />
        <DialogPrimitive.Content
          data-testid={testId}
          aria-modal={modal ? "true" : undefined}
          aria-describedby={description ? descriptionId : undefined}
          onEscapeKeyDown={onEscapeKeyDown}
          onInteractOutside={onInteractOutside}
          className={
            contentClassName
              ? `orcia-ds-dialog-content ${contentClassName}`
              : "orcia-ds-dialog-content"
          }
        >
          <div className="orcia-ds-header" style={{ flexShrink: 0 }}>
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <DialogPrimitive.Title className="orcia-ds-dialog-title">
                {title}
              </DialogPrimitive.Title>
              {headerExtra}
            </div>
            {!hideHeaderCloseButton && closeLabel ? (
              <DialogPrimitive.Close
                type="button"
                data-testid={closeButtonTestId ?? `${testId}-close-btn`}
                className="orcia-ds-btn orcia-ds-btn-secondary"
              >
                {closeLabel}
              </DialogPrimitive.Close>
            ) : null}
          </div>
          {description ? (
            <DialogPrimitive.Description
              id={descriptionId}
              className="orcia-ds-dialog-description"
              style={{ flexShrink: 0 }}
            >
              {description}
            </DialogPrimitive.Description>
          ) : null}
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

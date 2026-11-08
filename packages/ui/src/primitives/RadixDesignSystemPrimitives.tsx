import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import * as SelectPrimitive from "@radix-ui/react-select";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import React from "react";

export interface OrciaTabItem<T extends string = string> {
  readonly key: T;
  readonly label: string;
  readonly testId?: string;
}

export interface OrciaTabBarProps<T extends string = string> {
  readonly tabs: readonly OrciaTabItem<T>[];
  readonly activeTab: T;
  readonly onSelectTab: (tabKey: T) => void;
  readonly ariaLabel: string;
  readonly testIdPrefix?: string;
  readonly panels?: Partial<Record<T, React.ReactNode>>;
}

export function OrciaTabBar<T extends string = string>({
  tabs,
  activeTab,
  onSelectTab,
  ariaLabel,
  testIdPrefix = "orcia-tab",
  panels,
}: OrciaTabBarProps<T>): React.ReactElement {
  return (
    <TabsPrimitive.Root
      value={activeTab}
      onValueChange={(nextValue) => onSelectTab(nextValue as T)}
    >
      <TabsPrimitive.List aria-label={ariaLabel} className="orcia-ds-tabs">
        {tabs.map((tab) => {
          const isSelected = tab.key === activeTab;
          return (
            <TabsPrimitive.Trigger
              key={tab.key}
              value={tab.key}
              aria-selected={isSelected}
              data-testid={tab.testId ?? `${testIdPrefix}-${tab.key}`}
              onClick={() => {
                if (tab.key !== activeTab) {
                  onSelectTab(tab.key);
                }
              }}
              className="orcia-ds-tab"
            >
              {tab.label}
            </TabsPrimitive.Trigger>
          );
        })}
      </TabsPrimitive.List>
      {panels
        ? tabs.map((tab) =>
            panels[tab.key] !== undefined ? (
              <TabsPrimitive.Content
                key={tab.key}
                value={tab.key}
                data-testid={`${testIdPrefix}-panel-${tab.key}`}
                className="orcia-ds-tab-panel"
              >
                {panels[tab.key]}
              </TabsPrimitive.Content>
            ) : null,
          )
        : null}
    </TabsPrimitive.Root>
  );
}

export interface OrciaDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly title: string;
  readonly description?: string;
  readonly testId?: string;
  readonly closeLabel?: string;
  readonly children: React.ReactNode;
}

export function OrciaDialog({
  open,
  onOpenChange,
  title,
  description,
  testId = "orcia-radix-dialog",
  closeLabel = "Fermer",
  children,
}: OrciaDialogProps): React.ReactElement {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="orcia-ds-dialog-overlay" />
        <DialogPrimitive.Content
          data-testid={testId}
          aria-describedby={description ? undefined : undefined}
          className="orcia-ds-dialog-content"
        >
          <div className="orcia-ds-header">
            <DialogPrimitive.Title className="orcia-ds-dialog-title">
              {title}
            </DialogPrimitive.Title>
            <DialogPrimitive.Close
              type="button"
              data-testid={`${testId}-close-btn`}
              className="orcia-ds-btn orcia-ds-btn-secondary"
            >
              {closeLabel}
            </DialogPrimitive.Close>
          </div>
          {description ? (
            <DialogPrimitive.Description className="orcia-ds-dialog-description">
              {description}
            </DialogPrimitive.Description>
          ) : null}
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export interface OrciaRadixSelectOption<T extends string = string> {
  readonly value: T;
  readonly label: string;
}

export interface OrciaRadixSelectProps<T extends string = string> {
  readonly value: T;
  readonly onValueChange: (value: T) => void;
  readonly options: readonly OrciaRadixSelectOption<T>[];
  readonly ariaLabel: string;
  readonly placeholder?: string;
  readonly testId?: string;
  readonly disabled?: boolean;
}

export function OrciaRadixSelect<T extends string = string>({
  value,
  onValueChange,
  options,
  ariaLabel,
  placeholder,
  testId = "orcia-radix-select",
  disabled = false,
}: OrciaRadixSelectProps<T>): React.ReactElement {
  return (
    <SelectPrimitive.Root
      value={value}
      onValueChange={(val) => onValueChange(val as T)}
      disabled={disabled}
    >
      <SelectPrimitive.Trigger
        aria-label={ariaLabel}
        data-testid={testId}
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        className="orcia-ds-select orcia-ds-radix-select-trigger"
      >
        <SelectPrimitive.Value placeholder={placeholder} />
        <SelectPrimitive.Icon aria-hidden="true">▾</SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content className="orcia-ds-dropdown-content">
          <SelectPrimitive.Viewport>
            {options.map((opt) => (
              <SelectPrimitive.Item
                key={opt.value}
                value={opt.value}
                data-testid={`${testId}-option-${opt.value}`}
                className="orcia-ds-dropdown-item"
              >
                <SelectPrimitive.ItemText>{opt.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}

export interface OrciaDropdownMenuItem {
  readonly key: string;
  readonly label: string;
  readonly onSelect: () => void;
  readonly disabled?: boolean;
  readonly testId?: string;
}

export interface OrciaDropdownMenuProps {
  readonly triggerLabel: React.ReactNode;
  readonly items: readonly OrciaDropdownMenuItem[];
  readonly testId?: string;
}

export function OrciaDropdownMenu({
  triggerLabel,
  items,
  testId = "orcia-dropdown-menu",
}: OrciaDropdownMenuProps): React.ReactElement {
  return (
    <DropdownMenuPrimitive.Root>
      <DropdownMenuPrimitive.Trigger
        type="button"
        data-testid={`${testId}-trigger`}
        className="orcia-ds-btn orcia-ds-btn-secondary"
      >
        {triggerLabel}
      </DropdownMenuPrimitive.Trigger>
      <DropdownMenuPrimitive.Portal>
        <DropdownMenuPrimitive.Content
          data-testid={`${testId}-content`}
          sideOffset={4}
          className="orcia-ds-dropdown-content"
        >
          {items.map((item) => (
            <DropdownMenuPrimitive.Item
              key={item.key}
              disabled={item.disabled}
              data-testid={item.testId ?? `${testId}-item-${item.key}`}
              onSelect={item.onSelect}
              className="orcia-ds-dropdown-item"
            >
              {item.label}
            </DropdownMenuPrimitive.Item>
          ))}
        </DropdownMenuPrimitive.Content>
      </DropdownMenuPrimitive.Portal>
    </DropdownMenuPrimitive.Root>
  );
}

export interface OrciaTooltipProps {
  readonly content: React.ReactNode;
  readonly children: React.ReactElement;
  readonly testId?: string;
}

export function OrciaTooltip({
  content,
  children,
  testId = "orcia-tooltip",
}: OrciaTooltipProps): React.ReactElement {
  return (
    <TooltipPrimitive.Provider delayDuration={150}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            data-testid={testId}
            sideOffset={4}
            className="orcia-ds-tooltip-content"
          >
            {content}
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}

export interface OrciaSwitchProps {
  readonly checked: boolean;
  readonly onCheckedChange: (checked: boolean) => void;
  readonly ariaLabel: string;
  readonly disabled?: boolean;
  readonly testId?: string;
}

export function OrciaSwitch({
  checked,
  onCheckedChange,
  ariaLabel,
  disabled = false,
  testId = "orcia-switch",
}: OrciaSwitchProps): React.ReactElement {
  return (
    <SwitchPrimitive.Root
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      aria-label={ariaLabel}
      data-testid={testId}
      className="orcia-ds-switch-root"
    >
      <SwitchPrimitive.Thumb className="orcia-ds-switch-thumb" />
    </SwitchPrimitive.Root>
  );
}

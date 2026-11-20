import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import type {
  SidebarAccountPopoverLabels,
  UiUserSettingsTabKey,
} from "./UserAccountDropdownTypes";
import { computeUserInitials } from "./UserRoleDisplayLabels";

export interface SidebarAccountPopoverProps {
  readonly railCollapsed: boolean;
  readonly userDisplayName: string;
  readonly userEmail: string;
  readonly userRoleLabel: string;
  readonly labels: SidebarAccountPopoverLabels;
  readonly onOpenSettingsTab: (tab: UiUserSettingsTabKey) => void;
  readonly onNavigateProfile: () => void;
  readonly onNavigateHelp: () => void;
  readonly onNavigateShowcase: () => void;
  readonly onLogout: () => void;
}

export function SidebarAccountPopover({
  railCollapsed,
  userDisplayName,
  userEmail,
  userRoleLabel,
  labels,
  onOpenSettingsTab,
  onNavigateProfile,
  onNavigateHelp,
  onNavigateShowcase,
  onLogout,
}: SidebarAccountPopoverProps): React.ReactElement {
  const [open, setOpen] = useState(false);
  const [helpSubOpen, setHelpSubOpen] = useState(false);
  const initials = computeUserInitials(userDisplayName);

  const handleOpenChange = (next: boolean): void => {
    setOpen(next);
    if (!next) {
      setHelpSubOpen(false);
    }
  };

  return (
    <DropdownMenuPrimitive.Root open={open} onOpenChange={handleOpenChange}>
      <DropdownMenuPrimitive.Trigger asChild>
        <button
          type="button"
          data-testid="sidebar-open-my-account-btn"
          aria-label={
            railCollapsed
              ? `${userDisplayName} · ${userRoleLabel}`
              : labels.triggerAriaLabel
          }
          title={railCollapsed ? `${userDisplayName} · ${userRoleLabel}` : undefined}
          className={`orcia-sidebar-nav-btn w-full ${
            railCollapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2 py-2"
          }`}
        >
          <span
            data-testid="sidebar-account-initials-avatar"
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold"
            style={{
              backgroundColor: "var(--color-action-primary-subtle)",
              color: "var(--color-action-primary)",
            }}
          >
            {initials}
          </span>
          {!railCollapsed && (
            <>
              <span className="flex min-w-0 flex-1 flex-col text-left leading-tight">
                <span
                  data-testid="sidebar-account-display-name"
                  className="truncate text-xs font-semibold"
                  style={{ color: "var(--color-text-primary)" }}
                >
                  {userDisplayName}
                </span>
                <span
                  data-testid="sidebar-account-role-label"
                  className="whitespace-normal break-words text-[11px] leading-snug"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {userRoleLabel}
                </span>
              </span>
              <OrciaIcon name="chevronDown" size={14} />
            </>
          )}
        </button>
      </DropdownMenuPrimitive.Trigger>

      <DropdownMenuPrimitive.Portal>
        <DropdownMenuPrimitive.Content
          side="top"
          align="start"
          sideOffset={8}
          data-testid="sidebar-account-popover-menu"
          className="z-50 w-[256px] rounded-xl border p-1.5 text-xs shadow-xl"
          style={{
            zIndex: "var(--z-popover)",
            backgroundColor: "var(--color-bg-surface)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
            boxShadow: "var(--shadow-dropdown)",
          }}
        >
          <DropdownMenuPrimitive.Item
            data-testid="account-popover-identity-header"
            onSelect={() => {
              setOpen(false);
              onNavigateProfile();
            }}
            className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 outline-none hover:bg-surface-hover focus:bg-surface-hover"
          >
            <span
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold"
              style={{
                backgroundColor: "var(--color-action-primary-subtle)",
                color: "var(--color-action-primary)",
              }}
            >
              {initials}
            </span>
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-xs font-semibold">{userDisplayName}</span>
              <span
                className="truncate text-[11px]"
                style={{ color: "var(--color-text-secondary)" }}
              >
                {userEmail}
              </span>
            </span>
            <OrciaIcon name="chevronRight" size={14} />
          </DropdownMenuPrimitive.Item>

          <DropdownMenuPrimitive.Separator
            className="my-1 h-px"
            style={{ backgroundColor: "var(--color-border-subtle)" }}
          />

          <DropdownMenuPrimitive.Item
            data-testid="account-popover-personalization-btn"
            onSelect={() => {
              setOpen(false);
              onOpenSettingsTab("PERSONALIZATION");
            }}
            className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 outline-none hover:bg-surface-hover focus:bg-surface-hover"
          >
            <OrciaIcon name="sparkles" size={15} />
            <span className="flex-1">{labels.personalizationLabel}</span>
          </DropdownMenuPrimitive.Item>

          <DropdownMenuPrimitive.Item
            data-testid="account-popover-profile-btn"
            onSelect={() => {
              setOpen(false);
              onNavigateProfile();
            }}
            className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 outline-none hover:bg-surface-hover focus:bg-surface-hover"
          >
            <OrciaIcon name="user" size={15} />
            <span className="flex-1">{labels.profileLabel}</span>
          </DropdownMenuPrimitive.Item>

          <DropdownMenuPrimitive.Separator
            className="my-1 h-px"
            style={{ backgroundColor: "var(--color-border-subtle)" }}
          />

          <DropdownMenuPrimitive.Item
            data-testid="account-popover-help-trigger"
            onSelect={(event) => {
              event.preventDefault();
              setHelpSubOpen((prev) => !prev);
            }}
            className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 outline-none hover:bg-surface-hover focus:bg-surface-hover"
          >
            <OrciaIcon name="help" size={15} />
            <span className="flex-1">{labels.helpMenuLabel}</span>
            <OrciaIcon name={helpSubOpen ? "chevronDown" : "chevronRight"} size={14} />
          </DropdownMenuPrimitive.Item>

          {helpSubOpen && (
            <div
              data-testid="account-popover-help-submenu"
              className="ml-4 mt-0.5 flex flex-col gap-0.5 border-l pl-2"
              style={{ borderColor: "var(--color-border-subtle)" }}
            >
              <DropdownMenuPrimitive.Item
                data-testid="account-popover-help-center-btn"
                onSelect={() => {
                  setOpen(false);
                  onNavigateHelp();
                }}
                className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 outline-none hover:bg-surface-hover focus:bg-surface-hover"
              >
                <OrciaIcon name="bookOpen" size={14} />
                <span>{labels.helpCenterLabel}</span>
              </DropdownMenuPrimitive.Item>
              <DropdownMenuPrimitive.Item
                data-testid="account-popover-showcase-btn"
                onSelect={() => {
                  setOpen(false);
                  onNavigateShowcase();
                }}
                className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 outline-none hover:bg-surface-hover focus:bg-surface-hover"
              >
                <OrciaIcon name="globe" size={14} />
                <span>{labels.showcaseLabel}</span>
              </DropdownMenuPrimitive.Item>
            </div>
          )}

          <DropdownMenuPrimitive.Separator
            className="my-1 h-px"
            style={{ backgroundColor: "var(--color-border-subtle)" }}
          />

          <DropdownMenuPrimitive.Item
            data-testid="account-popover-logout-btn"
            onSelect={() => {
              setOpen(false);
              onLogout();
            }}
            className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 font-medium outline-none hover:bg-surface-hover focus:bg-surface-hover"
            style={{ color: "var(--color-stale-crimson)" }}
          >
            <OrciaIcon name="arrowRight" size={15} />
            <span className="flex-1">{labels.logoutLabel}</span>
          </DropdownMenuPrimitive.Item>
        </DropdownMenuPrimitive.Content>
      </DropdownMenuPrimitive.Portal>
    </DropdownMenuPrimitive.Root>
  );
}

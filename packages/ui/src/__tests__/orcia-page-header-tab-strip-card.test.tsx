import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  OrciaAlertBanner,
  OrciaButton,
  OrciaDataCard,
  OrciaPageHeader,
  OrciaTabStrip,
  StatusBadge,
} from "../index";

describe("Story 29.4 — Canonical OrciaPageHeader, OrciaTabStrip & OrciaDataCard primitives", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders OrciaPageHeader with semantic h1, monochrome OrciaIcon, contextBadge, Tier-2 slots, and aligned alertSlot beneath header", () => {
    render(
      <OrciaPageHeader
        testId="canon-header"
        icon="spaces"
        title="Workspaces"
        subtitle="Organize spaces, sources, and team rules."
        contextBadge={<StatusBadge testId="canon-badge" label="Team Scope" tone="cobalt" />}
        secondaryActions={
          <OrciaButton testId="canon-secondary" variant="secondary" disabled>
            Export
          </OrciaButton>
        }
        primaryAction={
          <OrciaButton testId="canon-primary" variant="primary">
            + New Workspace
          </OrciaButton>
        }
        tabs={
          <OrciaTabStrip
            testId="canon-tabs"
            ariaLabel="Workspace sections"
            activeTabId="overview"
            onSelectTab={vi.fn()}
            tabs={[
              { key: "overview", label: "Overview", count: 3 },
              { key: "sources", label: "Sources", count: 0 },
            ]}
          />
        }
        scopeBar={<span data-testid="canon-scope">Active scope</span>}
        alertSlot={
          <OrciaAlertBanner testId="canon-alert" tone="crimson">
            Synchronization failed.
          </OrciaAlertBanner>
        }
      />,
    );

    const header = screen.getByTestId("canon-header");
    expect(header.tagName).toBe("HEADER");
    expect(header.className).toContain("orcia-bento-card");
    expect(header.className).toContain("orcia-ds-page-header");

    const heading = screen.getByRole("heading", { level: 1, name: "Workspaces" });
    expect(heading.className).toContain("orcia-ds-page-header-title");
    expect(screen.getByTestId("canon-header-subtitle").textContent).toBe(
      "Organize spaces, sources, and team rules.",
    );
    expect(screen.getByTestId("canon-badge").textContent).toBe("Team Scope");
    expect(header.querySelector('[data-orcia-icon="spaces"]')).not.toBeNull();
    expect(screen.getByTestId("canon-secondary").hasAttribute("disabled")).toBe(true);
    expect(screen.getByTestId("canon-primary").className).toContain("orcia-ds-btn-primary");
    expect(screen.getByTestId("canon-header-tier2")).toBeTruthy();
    expect(screen.getByTestId("canon-scope")).toBeTruthy();

    const alertSlot = screen.getByTestId("canon-header-alert-slot");
    expect(alertSlot.contains(screen.getByTestId("canon-alert"))).toBe(true);
    expect(header.contains(alertSlot)).toBe(false);
    expect(header.nextElementSibling).toBe(alertSlot);
  });

  it("renders OrciaTabStrip in underline and segmented variants with aria-selected, counts, disabled state, trailingSlot, and keyboard navigation", () => {
    const onSelect = vi.fn();
    function ControlledStrip() {
      const [active, setActive] = React.useState<"agents" | "skills" | "mcp">("agents");
      return (
        <OrciaTabStrip
          testId="strip"
          ariaLabel="Primary modules"
          activeTabId={active}
          onSelectTab={(next) => {
            setActive(next);
            onSelect(next);
          }}
          trailingSlot={<span data-testid="strip-trailing-content">3 items</span>}
          tabs={[
            { key: "agents", label: "Agents", icon: "agents", count: 4 },
            { key: "skills", label: "Skills", disabled: true, disabledReason: "Admin only" },
            { key: "mcp", label: "MCP Servers", count: 2, tooltip: "External tools" },
          ]}
        />
      );
    }

    const { rerender } = render(<ControlledStrip />);

    const tablist = screen.getByTestId("strip");
    expect(tablist.getAttribute("role")).toBe("tablist");
    expect(tablist.getAttribute("aria-orientation")).toBe("horizontal");
    expect(tablist.className).toContain("orcia-ds-tab-strip--underline");
    const headersCss = fs.readFileSync(
      path.resolve(__dirname, "../styles/tokens-headers.css"),
      "utf-8",
    );
    expect(headersCss).toMatch(/\.orcia-ds-tab-strip\s*\{[^}]*flex-wrap:\s*nowrap;/s);
    expect(screen.getByTestId("strip-trailing-content").textContent).toBe("3 items");
    expect(screen.getByTestId("strip-trailing")).toBeTruthy();

    const agentsTab = screen.getByTestId("orcia-tab-strip-agents");
    const skillsTab = screen.getByTestId("orcia-tab-strip-skills");
    const mcpTab = screen.getByTestId("orcia-tab-strip-mcp");

    expect(agentsTab.getAttribute("aria-selected")).toBe("true");
    expect(agentsTab.textContent).toContain("4");
    expect(skillsTab.hasAttribute("disabled")).toBe(true);
    expect(skillsTab.getAttribute("title")).toBe("Admin only");
    expect(mcpTab.getAttribute("aria-selected")).toBe("false");

    // Disabled tab click does not trigger onSelect
    fireEvent.click(skillsTab);
    expect(onSelect).not.toHaveBeenCalled();

    // ArrowRight skips disabled middle tab and activates MCP Servers
    fireEvent.keyDown(agentsTab, { key: "ArrowRight" });
    expect(onSelect).toHaveBeenCalledWith("mcp");

    // Home returns to first enabled tab
    fireEvent.keyDown(mcpTab, { key: "Home" });
    expect(onSelect).toHaveBeenCalledWith("agents");

    // End selects last enabled tab
    fireEvent.keyDown(agentsTab, { key: "End" });
    expect(onSelect).toHaveBeenLastCalledWith("mcp");

    rerender(
      <OrciaTabStrip
        testId="strip"
        variant="segmented"
        ariaLabel="Primary modules"
        activeTabId="mcp"
        onSelectTab={onSelect}
        tabs={[
          { key: "agents", label: "Agents" },
          { key: "mcp", label: "MCP Servers" },
        ]}
      />,
    );
    expect(screen.getByTestId("strip").className).toContain("orcia-ds-tab-strip--segmented");
    expect(screen.getByTestId("orcia-tab-strip-mcp").getAttribute("aria-selected")).toBe("true");
  });

  it("renders OrciaDataCard with canonical surface classes, header metadata, actions, body, and footer", () => {
    render(
      <OrciaDataCard
        testId="data-card"
        icon="finops"
        title="Process Consumption"
        subtitle="Aggregated cost across authorized workspaces."
        metaBadge={<StatusBadge testId="data-card-badge" label="Live" tone="emerald" />}
        actions={
          <OrciaButton testId="data-card-action" variant="secondary" size="sm">
            Refresh
          </OrciaButton>
        }
        footer={<span data-testid="data-card-footer-text">Updated 1m ago</span>}
      >
        <div data-testid="data-card-content">Table rows</div>
      </OrciaDataCard>,
    );

    const card = screen.getByTestId("data-card");
    expect(card.tagName).toBe("SECTION");
    expect(card.className).toContain("orcia-bento-card");
    expect(card.className).toContain("orcia-ds-data-card");
    expect(screen.getByRole("heading", { level: 2, name: "Process Consumption" })).toBeTruthy();
    expect(screen.getByTestId("data-card-badge").textContent).toBe("Live");
    expect(screen.getByTestId("data-card-action")).toBeTruthy();
    expect(screen.getByTestId("data-card-content").textContent).toBe("Table rows");
    expect(screen.getByTestId("data-card-footer-text").textContent).toBe("Updated 1m ago");
  });
});

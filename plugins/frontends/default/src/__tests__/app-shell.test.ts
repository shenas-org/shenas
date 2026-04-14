import { describe, it, expect, beforeEach, vi } from "vitest";
import { mockResponse } from "./setup.ts";

// Mock fetch before importing the component
globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../app-shell.ts";

describe("shenas-app", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    window.history.replaceState({}, "", "/");
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse([]));
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-app");
    expect(el).toBeDefined();
    expect(el.tagName.toLowerCase()).toBe("shenas-app");
  });

  it("has default api-base", () => {
    const el = document.createElement("shenas-app") as HTMLElement & { apiBase: string };
    expect(el.apiBase).toBe("/api");
  });

  it("fetches data on connect", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse([]));

    const el = document.createElement("shenas-app");
    document.body.appendChild(el);

    // Wait for async fetch
    await new Promise((r) => setTimeout(r, 50));

    expect(globalThis.fetch).toHaveBeenCalled();
  });
});

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-app") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("routing", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    window.history.replaceState({}, "", "/");
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse([]));
  });

  it("initializes a Router instance", () => {
    const el = mount();
    expect(el._router).toBeDefined();
    expect(typeof el._router.goto).toBe("function");
  });

  it("navigates via _navigateTo, updating tabs and history", async () => {
    const el = mount();
    await el.updateComplete;
    // Seed a tab so _navigateTo takes the "update active tab" branch
    el._openTab("/settings", "Settings");
    await el.updateComplete;
    el._navigateTo("/settings/source", "Sources");
    await el.updateComplete;
    const active = el._tabs.find((t: any) => t.id === el._activeTabId);
    expect(active.path).toBe("/settings/source");
    expect(active.label).toBe("Sources");
    expect(window.location.pathname).toBe("/settings/source");
  });

  it("responds to popstate events without throwing", async () => {
    const el = mount();
    await el.updateComplete;
    window.history.pushState({}, "", "/settings");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await el.updateComplete;
    expect(el._router).toBeDefined();
  });
});

describe("tab management", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    window.history.replaceState({}, "", "/");
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse([]));
  });

  it("renders dashboard nav items when _dashboards is set", async () => {
    const el = mount();
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 30));
    el._loading = false;
    el._dashboards = [
      { name: "fitness", displayName: "Fitness", tag: "shenas-fitness", js: "/x.js" },
      { name: "finance", displayName: "Finance", tag: "shenas-finance", js: "/y.js" },
    ];
    await el.updateComplete;
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Fitness");
    expect(text).toContain("Finance");
  });

  it("_openTab adds a tab entry and activates it", async () => {
    const el = mount();
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 20));
    // Reset any tabs restored from workspace after async load settles
    el._tabs = [];
    el._activeTabId = null;
    el._nextTabId = 1;
    el._openTab("/settings/source", "Sources");
    await el.updateComplete;
    expect(el._tabs.length).toBe(1);
    const added = el._tabs[0];
    expect(added.path).toBe("/settings/source");
    expect(el._activeTabId).toBe(added.id);
  });

  it("_closeTab removes a tab entry", async () => {
    const el = mount();
    await el.updateComplete;
    el._openTab("/a", "A");
    el._openTab("/b", "B");
    await el.updateComplete;
    const countAfterOpen = el._tabs.length;
    const idToClose = el._tabs[el._tabs.length - 1].id;
    el._closeTab(idToClose);
    await el.updateComplete;
    expect(el._tabs.length).toBe(countAfterOpen - 1);
    expect(el._tabs.find((t: any) => t.id === idToClose)).toBeUndefined();
  });
});

describe("command palette", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    window.history.replaceState({}, "", "/");
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse([]));
  });

  it("_togglePalette opens then closes the palette", async () => {
    const el = mount();
    await el.updateComplete;
    expect(el._paletteOpen).toBe(false);
    el._togglePalette();
    await el.updateComplete;
    expect(el._paletteOpen).toBe(true);
    el._togglePalette();
    await el.updateComplete;
    expect(el._paletteOpen).toBe(false);
  });

  it("closes the palette when set back to false (Escape path)", async () => {
    const el = mount();
    await el.updateComplete;
    el._paletteOpen = true;
    await el.updateComplete;
    el._paletteOpen = false;
    await el.updateComplete;
    expect(el._paletteOpen).toBe(false);
  });

  it("captures register-command custom events from child elements", async () => {
    const el = mount();
    await el.updateComplete;
    const commands = [{ id: "my-action", label: "My Action", category: "Test", action: () => {} }];
    el.dispatchEvent(
      new CustomEvent("register-command", {
        detail: { componentId: "child-1", commands },
        bubbles: true,
      }),
    );
    await el.updateComplete;
    expect(el._registeredCommands.get("child-1")).toEqual(commands);
    // Unregister by passing empty commands
    el.dispatchEvent(
      new CustomEvent("register-command", {
        detail: { componentId: "child-1", commands: [] },
        bubbles: true,
      }),
    );
    expect(el._registeredCommands.has("child-1")).toBe(false);
  });
});

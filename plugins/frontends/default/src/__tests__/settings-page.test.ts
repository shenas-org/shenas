import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

vi.mock("shenas-frontends", async (importOriginal) => {
  const mod = (await importOriginal()) as Record<string, unknown>;
  return {
    ...mod,
    registerCommands: vi.fn(),
  };
});

import "../settings-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

const MOCK_CATEGORIES = [
  {
    id: "general",
    name: "General",
    description: "General application settings",
    settings: [
      {
        id: "theme",
        key: "theme",
        display_name: "Theme",
        value: "light",
        type: "select",
        description: "Choose a color theme",
        options: [
          { label: "Light", value: "light" },
          { label: "Dark", value: "dark" },
        ],
        required: false,
        default: "light",
      },
      {
        id: "notifications",
        key: "notifications",
        display_name: "Notifications",
        value: true,
        type: "boolean",
        description: "Enable desktop notifications",
        required: false,
        default: true,
      },
    ],
  },
  {
    id: "sync",
    name: "Sync",
    description: "Data synchronization settings",
    settings: [
      {
        id: "sync_interval",
        key: "sync_interval",
        display_name: "Sync Interval",
        value: 60,
        type: "number",
        description: "Minutes between syncs",
        required: true,
        default: 60,
      },
    ],
  },
];

/**
 * gql() unwraps the top-level { data } envelope, so the component receives
 * whatever is nested inside `data`. The component then reads
 * `response.data?.settings`, which means it expects gql() to return an
 * object with a `.data` property. To satisfy that, the fetch mock must
 * double-nest: json = { data: { data: { settings: { ... } } } } so that
 * gql() (which returns json.data) hands back { data: { settings: ... } }.
 */
function mockSettingsResponse() {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        data: { data: { settings: { categories: MOCK_CATEGORIES } } },
      }),
  };
}

function mockEmptySettingsResponse() {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        data: { data: { settings: { categories: [] } } },
      }),
  };
}

function mount(): AnyEl {
  const el = document.createElement("shenas-settings") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-settings", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockSettingsResponse());
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-settings");
    expect(el.tagName.toLowerCase()).toBe("shenas-settings");
  });

  it("has default property values", () => {
    const el = document.createElement("shenas-settings") as AnyEl;
    expect(el.apiBase).toBe("http://localhost:3000");
    expect(el._settings).toEqual({});
    expect(el._categories).toEqual([]);
    expect(el._loading).toBe(false);
    expect(el._saving).toBe(false);
    expect(el._message).toBeNull();
    expect(el._expandedCategories).toBeInstanceOf(Set);
    expect(el._expandedCategories.size).toBe(0);
    expect(el._changedSettings).toBeInstanceOf(Map);
    expect(el._changedSettings.size).toBe(0);
  });

  it("loads settings on connect", async () => {
    mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toContain("/graphql");
    expect(JSON.parse(call[1].body).query).toContain("settings");
  });

  it("populates categories and settings after load", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(el._categories).toHaveLength(2);
    expect(el._categories[0].id).toBe("general");
    expect(el._settings.theme).toBe("light");
    expect(el._settings.notifications).toBe(true);
    expect(el._settings.sync_interval).toBe(60);
    expect(el._loading).toBe(false);
  });

  it("expands first category by default after load", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(el._expandedCategories.has("general")).toBe(true);
    expect(el._expandedCategories.has("sync")).toBe(false);
  });

  it("sets error message when load fails", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("network error"));
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(el._message).toBeTruthy();
    expect(el._message.type).toBe("error");
    expect(el._message.text).toContain("network error");
    expect(el._loading).toBe(false);
  });

  it("renders loading state", async () => {
    const el = mount();
    el._loading = true;
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Loading settings");
  });

  it("renders empty state when no categories", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockEmptySettingsResponse());
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("No settings available");
  });

  it("renders categories after loading", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    await el.updateComplete;
    const headers = el.shadowRoot?.querySelectorAll(".category-header");
    expect(headers?.length).toBe(2);
  });

  it("renders page title", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    await el.updateComplete;
    const title = el.shadowRoot?.querySelector(".page-title");
    expect(title?.textContent).toContain("Settings");
  });

  it("toggles category expansion", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(el._expandedCategories.has("general")).toBe(true);
    expect(el._expandedCategories.has("sync")).toBe(false);

    el._toggleCategory("sync");
    expect(el._expandedCategories.has("sync")).toBe(true);

    el._toggleCategory("sync");
    expect(el._expandedCategories.has("sync")).toBe(false);
  });

  it("toggles off an already expanded category", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(el._expandedCategories.has("general")).toBe(true);

    el._toggleCategory("general");
    expect(el._expandedCategories.has("general")).toBe(false);
  });

  it("updates a setting value", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));

    el._updateSetting("theme", "dark");
    expect(el._settings.theme).toBe("dark");
    expect(el._changedSettings.has("theme")).toBe(true);
    expect(el._changedSettings.get("theme")).toBe("dark");
  });

  it("tracks multiple changed settings", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));

    el._updateSetting("theme", "dark");
    el._updateSetting("notifications", false);
    expect(el._changedSettings.size).toBe(2);
  });

  it("saves changed settings via GraphQL mutation", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    (globalThis.fetch as any).mockClear();
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: {
            updateSettings: { success: true, message: "Settings saved" },
          },
        }),
    });

    el._updateSetting("theme", "dark");
    await el._saveSettings();

    const calls = (globalThis.fetch as any).mock.calls;
    expect(calls.length).toBeGreaterThanOrEqual(1);
    const body = JSON.parse(calls[0][1].body);
    expect(body.query).toContain("updateSettings");
    expect(body.variables.updates).toEqual([{ id: "theme", value: "dark" }]);
  });

  it("shows success message after save", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    (globalThis.fetch as any).mockClear();
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: {
            updateSettings: { success: true, message: "Settings saved" },
          },
        }),
    });

    el._updateSetting("theme", "dark");
    await el._saveSettings();

    expect(el._message?.type).toBe("success");
    expect(el._message?.text).toContain("Settings saved");
    expect(el._changedSettings.size).toBe(0);
  });

  it("shows error message on save failure", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    (globalThis.fetch as any).mockClear();
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: {
            updateSettings: { success: false, message: "Validation error" },
          },
        }),
    });

    el._updateSetting("theme", "invalid");
    await el._saveSettings();

    expect(el._message?.type).toBe("error");
    expect(el._message?.text).toContain("Validation error");
  });

  it("shows error message on save network failure", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    (globalThis.fetch as any).mockClear();
    (globalThis.fetch as any).mockRejectedValue(new Error("timeout"));

    el._updateSetting("theme", "dark");
    await el._saveSettings();

    expect(el._message?.type).toBe("error");
    expect(el._message?.text).toContain("timeout");
  });

  it("no-ops save when no changes", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    (globalThis.fetch as any).mockClear();

    await el._saveSettings();

    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(el._message?.type).toBe("info");
    expect(el._message?.text).toContain("No changes");
  });

  it("resets settings to last saved state", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));

    el._updateSetting("theme", "dark");
    expect(el._changedSettings.size).toBe(1);

    (globalThis.fetch as any).mockClear();
    (globalThis.fetch as any).mockResolvedValue(mockSettingsResponse());

    el._resetSettings();

    expect(el._changedSettings.size).toBe(0);
    expect(el._message?.type).toBe("info");
    expect(el._message?.text).toContain("reset");
  });

  it("shows unsaved indicator when changes exist", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    await el.updateComplete;

    el._updateSetting("theme", "dark");
    await el.updateComplete;

    const indicator = el.shadowRoot?.querySelector(".unsaved-indicator");
    expect(indicator).toBeTruthy();
    expect(indicator?.textContent).toContain("unsaved");
  });

  it("renders action bar with save and reset buttons", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    await el.updateComplete;

    const actionBar = el.shadowRoot?.querySelector(".action-bar");
    expect(actionBar).toBeTruthy();
    const buttons = actionBar?.querySelectorAll("button");
    expect(buttons?.length).toBe(2);
  });

  it("renders setting inputs for expanded category", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    await el.updateComplete;

    // "general" is expanded by default
    const content = el.shadowRoot?.querySelector(".category-content.expanded");
    expect(content).toBeTruthy();
    const formGroups = content?.querySelectorAll(".form-group");
    expect(formGroups?.length).toBe(2);
  });

  it("renders select input for select-type setting", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    await el.updateComplete;

    const select = el.shadowRoot?.querySelector("select");
    expect(select).toBeTruthy();
    const options = select?.querySelectorAll("option");
    expect(options?.length).toBe(2);
  });

  it("renders checkbox for boolean-type setting", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    await el.updateComplete;

    const checkbox = el.shadowRoot?.querySelector('input[type="checkbox"]');
    expect(checkbox).toBeTruthy();
  });

  it("clears saving flag after save completes", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    (globalThis.fetch as any).mockClear();
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: {
            updateSettings: { success: true, message: "ok" },
          },
        }),
    });

    el._updateSetting("theme", "dark");
    await el._saveSettings();
    expect(el._saving).toBe(false);
  });

  it("reloads settings after successful save", async () => {
    const el = mount();
    await new Promise((r) => setTimeout(r, 20));
    (globalThis.fetch as any).mockClear();
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: {
            updateSettings: { success: true, message: "ok" },
          },
        }),
    });

    el._updateSetting("theme", "dark");
    await el._saveSettings();
    await new Promise((r) => setTimeout(r, 20));

    // Save triggers a reload, so fetch is called at least twice:
    // once for the mutation, once for the reload
    expect((globalThis.fetch as any).mock.calls.length).toBeGreaterThanOrEqual(2);
  });
});

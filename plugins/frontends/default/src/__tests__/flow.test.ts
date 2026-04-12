import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

vi.mock("cytoscape", () => {
  const fn: any = vi.fn(() => ({
    destroy: vi.fn(),
    resize: vi.fn(),
    fit: vi.fn(),
    on: vi.fn(),
    nodes: vi.fn(() => ({ length: 0 })),
    edges: vi.fn(() => ({ length: 0 })),
    add: vi.fn(),
    elements: vi.fn(() => ({ remove: vi.fn() })),
    layout: vi.fn(() => ({ run: vi.fn() })),
  }));
  fn.use = vi.fn();
  return { default: fn, dagre: vi.fn() };
});

import "../flow.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-pipeline-overview") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-pipeline-overview", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: {} }),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-pipeline-overview");
    expect(el.tagName.toLowerCase()).toBe("shenas-pipeline-overview");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("/api");
    expect(el.allPlugins).toEqual({});
    expect(el.schemaPlugins).toEqual({});
    expect(el._loading).toBe(true);
    expect(el._empty).toBe(false);
  });

  it("fetches data on connect", async () => {
    mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("renders cy container in shadow DOM", async () => {
    const el = mount();
    el._loading = false;
    await el.updateComplete;
    const container = el.shadowRoot?.querySelector("#cy");
    expect(container).toBeTruthy();
  });

  it("renders legend items", async () => {
    const el = mount();
    el._loading = false;
    await el.updateComplete;
    const legend = el.shadowRoot?.querySelector(".legend");
    expect(legend).toBeTruthy();
  });
});

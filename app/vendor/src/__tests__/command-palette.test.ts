import { describe, it, expect, beforeEach, vi } from "vitest";
import "../shenas-frontends/command-palette.ts";

type CmdPalette = HTMLElement & {
  open: boolean;
  commands: Array<{ id: string; label: string; category: string; description?: string }>;
  _query: string;
  _filtered: unknown[];
  _selectedIndex: number;
  _filter(): void;
  _onInput(e: Event): void;
  _onKeydown(e: KeyboardEvent): void;
  _execute(cmd: unknown): void;
  _close(): void;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): CmdPalette {
  return document.createElement("shenas-command-palette") as CmdPalette;
}

const sampleCommands = [
  { id: "a", label: "Apple", category: "Fruit", description: "red" },
  { id: "b", label: "Banana", category: "Fruit", description: "yellow" },
  { id: "c", label: "Carrot", category: "Veg", description: "orange" },
];

describe("shenas-command-palette", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the custom element", () => {
    expect(customElements.get("shenas-command-palette")).toBeTruthy();
    const el = makeEl();
    expect(el.tagName.toLowerCase()).toBe("shenas-command-palette");
  });

  it("has default property values", () => {
    const el = makeEl();
    expect(el.open).toBe(false);
    expect(el.commands).toEqual([]);
  });

  it("renders nothing when closed", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector(".panel")).toBeNull();
  });

  it("renders panel when open", async () => {
    const el = makeEl();
    el.open = true;
    el.commands = sampleCommands;
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector(".panel")).toBeTruthy();
    expect(el.shadowRoot.querySelectorAll(".item").length).toBe(3);
  });

  it("filters commands by query", async () => {
    const el = makeEl();
    el.commands = sampleCommands;
    el.open = true;
    document.body.appendChild(el);
    await el.updateComplete;
    const input = el.shadowRoot.querySelector("input")! as HTMLInputElement;
    input.value = "ban";
    input.dispatchEvent(new Event("input"));
    await el.updateComplete;
    expect(el._filtered.length).toBe(1);
  });

  it("filters by category and description", async () => {
    const el = makeEl();
    el.commands = sampleCommands;
    el.open = true;
    document.body.appendChild(el);
    await el.updateComplete;
    el._query = "veg";
    el._filter();
    expect(el._filtered.length).toBe(1);
    el._query = "yellow";
    el._filter();
    expect(el._filtered.length).toBe(1);
  });

  it("shows empty state when no matches", async () => {
    const el = makeEl();
    el.commands = sampleCommands;
    el.open = true;
    document.body.appendChild(el);
    await el.updateComplete;
    el._query = "zzz";
    el._filter();
    await el.updateComplete;
    expect(el.shadowRoot.querySelector(".empty")).toBeTruthy();
  });

  it("ArrowDown/ArrowUp adjust selected index", async () => {
    const el = makeEl();
    el.commands = sampleCommands;
    el.open = true;
    document.body.appendChild(el);
    await el.updateComplete;
    el._onKeydown(new KeyboardEvent("keydown", { key: "ArrowDown" }));
    expect(el._selectedIndex).toBe(1);
    el._onKeydown(new KeyboardEvent("keydown", { key: "ArrowDown" }));
    expect(el._selectedIndex).toBe(2);
    el._onKeydown(new KeyboardEvent("keydown", { key: "ArrowDown" }));
    expect(el._selectedIndex).toBe(2);
    el._onKeydown(new KeyboardEvent("keydown", { key: "ArrowUp" }));
    expect(el._selectedIndex).toBe(1);
  });

  it("Enter dispatches execute event with selected command", async () => {
    const el = makeEl();
    el.commands = sampleCommands;
    el.open = true;
    document.body.appendChild(el);
    await el.updateComplete;
    const handler = vi.fn();
    el.addEventListener("execute", handler);
    el._onKeydown(new KeyboardEvent("keydown", { key: "Enter" }));
    expect(handler).toHaveBeenCalledTimes(1);
    expect((handler.mock.calls[0][0] as CustomEvent).detail.id).toBe("a");
  });

  it("Escape dispatches close event", async () => {
    const el = makeEl();
    el.commands = sampleCommands;
    el.open = true;
    document.body.appendChild(el);
    await el.updateComplete;
    const handler = vi.fn();
    el.addEventListener("close", handler);
    el._onKeydown(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(handler).toHaveBeenCalled();
  });

  it("clicking backdrop closes", async () => {
    const el = makeEl();
    el.commands = sampleCommands;
    el.open = true;
    document.body.appendChild(el);
    await el.updateComplete;
    const handler = vi.fn();
    el.addEventListener("close", handler);
    (el.shadowRoot.querySelector(".backdrop") as HTMLElement).click();
    expect(handler).toHaveBeenCalled();
  });

  it("clicking an item executes it", async () => {
    const el = makeEl();
    el.commands = sampleCommands;
    el.open = true;
    document.body.appendChild(el);
    await el.updateComplete;
    const handler = vi.fn();
    el.addEventListener("execute", handler);
    (el.shadowRoot.querySelectorAll(".item")[1] as HTMLElement).click();
    expect((handler.mock.calls[0][0] as CustomEvent).detail.id).toBe("b");
  });

  it("resets query and selection when opened", async () => {
    const el = makeEl();
    el.commands = sampleCommands;
    document.body.appendChild(el);
    await el.updateComplete;
    el._query = "stale";
    el._selectedIndex = 5;
    el.open = true;
    await el.updateComplete;
    expect(el._query).toBe("");
    expect(el._selectedIndex).toBe(0);
  });
});

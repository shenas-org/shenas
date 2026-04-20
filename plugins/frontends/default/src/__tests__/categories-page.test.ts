import { describe, it, expect, beforeEach, vi } from "vitest";
import { mockResponse } from "./setup.ts";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../categories-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-categories") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-categories", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({
        data: {
          categorySets: [
            {
              id: "mood",
              displayName: "Mood",
              description: "Daily mood",
              values: [
                { value: "great", sortOrder: 0, color: "#22c55e" },
                { value: "ok", sortOrder: 1, color: "#eab308" },
              ],
            },
          ],
        },
      }),
    );
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-categories");
    expect(el.tagName.toLowerCase()).toBe("shenas-categories");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("/api");
    expect(el._editing).toBeNull();
    expect(el._creating).toBe(false);
    expect(el._message).toBeNull();
    expect(el._newId).toBe("");
    expect(el._newName).toBe("");
    expect(el._newDesc).toBe("");
    expect(el._editValues).toEqual([]);
    expect(el._editName).toBe("");
    expect(el._editDesc).toBe("");
    expect(el._addValue).toBe("");
  });

  // -- slugify -----------------------------------------------------------

  it("slugifies names correctly", () => {
    const el = mount();
    expect(el._slugify("My Category Set")).toBe("my-category-set");
    expect(el._slugify("  leading/trailing  ")).toBe("leading-trailing");
    expect(el._slugify("UPPERCASE")).toBe("uppercase");
    expect(el._slugify("with--dashes")).toBe("with-dashes");
    expect(el._slugify("special!@#chars")).toBe("special-chars");
  });

  // -- create flow -------------------------------------------------------

  it("enters create mode", () => {
    const el = mount();
    el._startCreate();
    expect(el._creating).toBe(true);
    expect(el._editing).toBeNull();
    expect(el._newId).toBe("");
    expect(el._newName).toBe("");
  });

  it("cancels create mode", () => {
    const el = mount();
    el._startCreate();
    el._cancelCreate();
    expect(el._creating).toBe(false);
  });

  it("auto-generates slug from name", () => {
    const el = mount();
    el._startCreate();
    el._newName = "Activity Type";
    el._autoSlug();
    expect(el._newId).toBe("activity-type");
  });

  it("rejects create when id or name missing", async () => {
    const el = mount();
    el._startCreate();
    el._newId = "";
    el._newName = "";
    await el._saveCreate();
    expect(el._message?.type).toBe("error");
    expect(el._message?.text).toContain("required");
  });

  // -- edit flow ---------------------------------------------------------

  it("enters edit mode for an existing set", async () => {
    const el = mount();
    // Wait for query to resolve
    await new Promise((resolve) => setTimeout(resolve, 50));

    el._startEdit("mood");
    expect(el._editing).toBe("mood");
    expect(el._creating).toBe(false);
    expect(el._editName).toBe("Mood");
    expect(el._editDesc).toBe("Daily mood");
    expect(el._editValues.length).toBe(2);
  });

  it("does nothing when editing a non-existent set", () => {
    const el = mount();
    el._startEdit("nonexistent");
    expect(el._editing).toBeNull();
  });

  it("cancels edit mode", () => {
    const el = mount();
    el._editing = "mood";
    el._cancelEdit();
    expect(el._editing).toBeNull();
  });

  // -- value management --------------------------------------------------

  it("adds a value to the edit list", () => {
    const el = mount();
    el._editValues = [{ value: "a", sortOrder: 0, color: null }];
    el._addValue = "b";
    el._addValueToList();
    expect(el._editValues.length).toBe(2);
    expect(el._editValues[1].value).toBe("b");
    expect(el._editValues[1].sortOrder).toBe(1);
    expect(el._addValue).toBe("");
  });

  it("does not add duplicate values", () => {
    const el = mount();
    el._editValues = [{ value: "a", sortOrder: 0, color: null }];
    el._addValue = "a";
    el._addValueToList();
    expect(el._editValues.length).toBe(1);
  });

  it("does not add empty values", () => {
    const el = mount();
    el._editValues = [];
    el._addValue = "   ";
    el._addValueToList();
    expect(el._editValues.length).toBe(0);
  });

  it("removes a value from the edit list", () => {
    const el = mount();
    el._editValues = [
      { value: "a", sortOrder: 0, color: null },
      { value: "b", sortOrder: 1, color: null },
    ];
    el._removeValue("a");
    expect(el._editValues.length).toBe(1);
    expect(el._editValues[0].value).toBe("b");
  });

  it("updates value color", () => {
    const el = mount();
    el._editValues = [{ value: "good", sortOrder: 0, color: null }];
    el._updateValueColor("good", "#ff0000");
    expect(el._editValues[0].color).toBe("#ff0000");
  });

  it("does not modify other values when updating color", () => {
    const el = mount();
    el._editValues = [
      { value: "a", sortOrder: 0, color: "#111" },
      { value: "b", sortOrder: 1, color: "#222" },
    ];
    el._updateValueColor("a", "#999");
    expect(el._editValues[0].color).toBe("#999");
    expect(el._editValues[1].color).toBe("#222");
  });
});

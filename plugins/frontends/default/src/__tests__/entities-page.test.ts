import { describe, it, expect, beforeEach, vi } from "vitest";
import { mockResponse } from "./setup.ts";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../entities-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

const ENTITY_DATA = {
  entities: [
    { uuid: "e1", type: "human", name: "Alice", description: "Test user", status: "enabled", isMe: true, sources: [] },
    {
      uuid: "e2",
      type: "device",
      name: "Garmin Watch",
      description: "",
      status: "enabled",
      isMe: false,
      sources: ["garmin"],
    },
    { uuid: "e3", type: "human", name: "Bob", description: "", status: "disabled", isMe: false, sources: [] },
  ],
  entityRelationships: [{ fromUuid: "e1", toUuid: "e2", type: "owns", description: "" }],
  entityTypes: [
    { name: "human", displayName: "Human", description: "", icon: "", parent: null, isAbstract: false },
    { name: "device", displayName: "Device", description: "", icon: "", parent: null, isAbstract: false },
    { name: "thing", displayName: "Thing", description: "", icon: "", parent: null, isAbstract: true },
  ],
  entityRelationshipTypes: [
    {
      name: "owns",
      displayName: "Owns",
      inverseName: "owned_by",
      isSymmetric: false,
      domainTypes: ["human"],
      rangeTypes: ["device"],
    },
  ],
};

function mount(): AnyEl {
  const el = document.createElement("shenas-entities") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-entities", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse({ data: ENTITY_DATA }));
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-entities");
    expect(el.tagName.toLowerCase()).toBe("shenas-entities");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el._message).toBeNull();
    expect(el._view).toBe("entities");
  });

  it("sets view from activeView attribute", () => {
    const el = mount();
    el.activeView = "types";
    el.willUpdate(new Map([["activeView", undefined]]));
    expect(el._view).toBe("types");
  });

  it("defaults to entities view for unknown activeView", () => {
    const el = mount();
    el.activeView = "unknown";
    el.willUpdate(new Map([["activeView", undefined]]));
    expect(el._view).toBe("entities");
  });

  // -- delete guard -------------------------------------------------------

  it("prevents deleting the 'me' entity", async () => {
    const el = mount();
    const meEntity = { uuid: "e1", type: "human", name: "Alice", isMe: true };
    await el._delete(meEntity);
    expect(el._message?.type).toBe("error");
    expect(el._message?.text).toContain("Cannot delete your own entity");
  });

  // -- create entity validation -------------------------------------------

  it("rejects creating entity with empty name", async () => {
    const el = mount();
    await el._saveEntityCreate({ name: "  ", type: "human", description: "", pickedUuid: null });
    expect(el._message?.type).toBe("error");
    expect(el._message?.text).toContain("Name is required");
  });
});

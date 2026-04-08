import { describe, it, expect } from "vitest";
import { parseHotkey, formatHotkey, matchesHotkey, sortActions, PLUGIN_KINDS } from "../shenas-frontends/constants.ts";
import type { ActionDescriptor } from "../shenas-frontends/constants.ts";

describe("parseHotkey", () => {
  it("returns null for empty input", () => {
    expect(parseHotkey("")).toBeNull();
    expect(parseHotkey(null)).toBeNull();
    expect(parseHotkey(undefined)).toBeNull();
  });

  it("parses single key", () => {
    expect(parseHotkey("k")).toEqual({ ctrl: false, shift: false, alt: false, key: "k" });
  });

  it("parses ctrl+key", () => {
    expect(parseHotkey("Ctrl+P")).toEqual({ ctrl: true, shift: false, alt: false, key: "p" });
  });

  it("treats cmd as ctrl", () => {
    expect(parseHotkey("Cmd+S")).toEqual({ ctrl: true, shift: false, alt: false, key: "s" });
  });

  it("parses ctrl+shift+key", () => {
    expect(parseHotkey("Ctrl+Shift+X")).toEqual({ ctrl: true, shift: true, alt: false, key: "x" });
  });

  it("parses all modifiers", () => {
    expect(parseHotkey("Ctrl+Shift+Alt+T")).toEqual({ ctrl: true, shift: true, alt: true, key: "t" });
  });

  it("returns empty key when only modifiers", () => {
    const result = parseHotkey("Ctrl+Shift");
    expect(result?.key).toBe("");
  });
});

describe("formatHotkey", () => {
  it("formats simple key event", () => {
    const e = new KeyboardEvent("keydown", { key: "p" });
    expect(formatHotkey(e)).toBe("P");
  });

  it("formats ctrl+key event", () => {
    const e = new KeyboardEvent("keydown", { key: "p", ctrlKey: true });
    expect(formatHotkey(e)).toBe("Ctrl+P");
  });

  it("treats meta as ctrl", () => {
    const e = new KeyboardEvent("keydown", { key: "p", metaKey: true });
    expect(formatHotkey(e)).toBe("Ctrl+P");
  });

  it("formats shift+alt event", () => {
    const e = new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, altKey: true });
    expect(formatHotkey(e)).toBe("Shift+Alt+Tab");
  });

  it("ignores modifier-only keys", () => {
    const e = new KeyboardEvent("keydown", { key: "Control", ctrlKey: true });
    expect(formatHotkey(e)).toBe("Ctrl");
  });
});

describe("matchesHotkey", () => {
  it("returns false for empty hotkey string", () => {
    const e = new KeyboardEvent("keydown", { key: "p" });
    expect(matchesHotkey(e, "")).toBe(false);
    expect(matchesHotkey(e, null)).toBe(false);
  });

  it("matches ctrl+p", () => {
    const e = new KeyboardEvent("keydown", { key: "p", ctrlKey: true });
    expect(matchesHotkey(e, "Ctrl+P")).toBe(true);
  });

  it("matches meta+p as ctrl+p", () => {
    const e = new KeyboardEvent("keydown", { key: "p", metaKey: true });
    expect(matchesHotkey(e, "Ctrl+P")).toBe(true);
  });

  it("does not match different keys", () => {
    const e = new KeyboardEvent("keydown", { key: "q", ctrlKey: true });
    expect(matchesHotkey(e, "Ctrl+P")).toBe(false);
  });

  it("does not match without modifiers", () => {
    const e = new KeyboardEvent("keydown", { key: "p" });
    expect(matchesHotkey(e, "Ctrl+P")).toBe(false);
  });
});

describe("sortActions", () => {
  const actions: ActionDescriptor[] = [
    { id: "b", label: "Bravo", category: "Cat2" },
    { id: "a", label: "Alpha", category: "Cat1" },
    { id: "c", label: "Charlie", category: "Cat1" },
  ];

  it("sorts by category then label", () => {
    const result = sortActions(actions);
    expect(result.map((a) => a.id)).toEqual(["a", "c", "b"]);
  });

  it("does not mutate input", () => {
    const copy = [...actions];
    sortActions(actions);
    expect(actions).toEqual(copy);
  });

  it("puts bound actions first when hotkeys provided", () => {
    const hotkeys = { b: "Ctrl+B" };
    const result = sortActions(actions, hotkeys);
    expect(result[0]?.id).toBe("b");
  });
});

describe("PLUGIN_KINDS", () => {
  it("contains all 6 kinds", () => {
    expect(PLUGIN_KINDS).toHaveLength(6);
    expect(PLUGIN_KINDS.map((k) => k.id)).toEqual(["source", "dataset", "dashboard", "model", "frontend", "theme"]);
  });
});

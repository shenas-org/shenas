export interface Hotkey {
  ctrl: boolean;
  shift: boolean;
  alt: boolean;
  key: string;
}

export interface ActionDescriptor {
  id: string;
  label: string;
  category: string;
  [key: string]: unknown;
}

export interface PluginKind {
  id: string;
  label: string;
}

export function parseHotkey(str: string | null | undefined): Hotkey | null {
  if (!str) return null;
  const parts = str.split("+").map((s) => s.trim().toLowerCase());
  return {
    ctrl: parts.includes("ctrl") || parts.includes("cmd"),
    shift: parts.includes("shift"),
    alt: parts.includes("alt"),
    key: parts.filter((p) => !["ctrl", "cmd", "shift", "alt"].includes(p))[0] || "",
  };
}

export function formatHotkey(e: KeyboardEvent): string {
  const parts: string[] = [];
  if (e.ctrlKey || e.metaKey) parts.push("Ctrl");
  if (e.shiftKey) parts.push("Shift");
  if (e.altKey) parts.push("Alt");
  const key = e.key.length === 1 ? e.key.toUpperCase() : e.key;
  if (!["Control", "Shift", "Alt", "Meta"].includes(e.key)) parts.push(key);
  return parts.join("+");
}

export function matchesHotkey(e: KeyboardEvent, hotkeyStr: string | null | undefined): boolean {
  const hk = parseHotkey(hotkeyStr);
  if (!hk || !hk.key) return false;
  const ctrl = e.ctrlKey || e.metaKey;
  return ctrl === hk.ctrl && e.shiftKey === hk.shift && e.altKey === hk.alt && e.key.toLowerCase() === hk.key;
}

/**
 * Sort actions: bound (has hotkey) first, then by category, then by label.
 * Pass hotkeys as a {actionId: binding} map, or null to skip bound-first.
 */
export function sortActions<T extends ActionDescriptor>(
  actions: T[],
  hotkeys: Record<string, unknown> | null = null,
): T[] {
  return [...actions].sort((a, b) => {
    if (hotkeys) {
      const aHas = hotkeys[a.id] ? 0 : 1;
      const bHas = hotkeys[b.id] ? 0 : 1;
      if (aHas !== bHas) return aHas - bHas;
    }
    if (a.category !== b.category) return (a.category || "").localeCompare(b.category || "");
    return (a.label || "").localeCompare(b.label || "");
  });
}

export const PLUGIN_KINDS: PluginKind[] = [
  { id: "source", label: "Sources" },
  { id: "dataset", label: "Datasets" },
  { id: "dashboard", label: "Dashboards" },
  { id: "model", label: "Models" },
  { id: "frontend", label: "Frontends" },
  { id: "theme", label: "Themes" },
];

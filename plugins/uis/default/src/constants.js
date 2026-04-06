export function parseHotkey(str) {
  if (!str) return null;
  const parts = str.split("+").map((s) => s.trim().toLowerCase());
  return {
    ctrl: parts.includes("ctrl") || parts.includes("cmd"),
    shift: parts.includes("shift"),
    alt: parts.includes("alt"),
    key: parts.filter((p) => !["ctrl", "cmd", "shift", "alt"].includes(p))[0] || "",
  };
}

export function formatHotkey(e) {
  const parts = [];
  if (e.ctrlKey || e.metaKey) parts.push("Ctrl");
  if (e.shiftKey) parts.push("Shift");
  if (e.altKey) parts.push("Alt");
  const key = e.key.length === 1 ? e.key.toUpperCase() : e.key;
  if (!["Control", "Shift", "Alt", "Meta"].includes(e.key)) parts.push(key);
  return parts.join("+");
}

export function matchesHotkey(e, hotkeyStr) {
  const hk = parseHotkey(hotkeyStr);
  if (!hk || !hk.key) return false;
  const ctrl = e.ctrlKey || e.metaKey;
  return ctrl === hk.ctrl && e.shiftKey === hk.shift && e.altKey === hk.alt && e.key.toLowerCase() === hk.key;
}

export const PLUGIN_KINDS = [
  { id: "pipe", label: "Pipes" },
  { id: "schema", label: "Schemas" },
  { id: "component", label: "Components" },
  { id: "model", label: "Models" },
  { id: "ui", label: "UI" },
  { id: "theme", label: "Themes" },
];

import { describe, it, expect, vi } from "vitest";

// Mock fetch for the component's connectedCallback
globalThis.fetch = vi.fn().mockResolvedValue({
  ok: true,
  arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
  json: () => Promise.resolve([]),
}) as unknown as typeof fetch;

import { categoryColor, formatTime, formatDate, dayKey } from "../event-gantt.ts";
import "../event-gantt.ts";

describe("categoryColor", () => {
  it("returns a color for known categories", () => {
    expect(categoryColor("meeting")).toBe("#6c5ce7");
    expect(categoryColor("workout")).toBe("#00b894");
    expect(categoryColor("focus")).toBe("#0984e3");
  });

  it("is case insensitive", () => {
    expect(categoryColor("MEETING")).toBe("#6c5ce7");
  });

  it("returns fallback color for unknown categories", () => {
    expect(categoryColor("unknown-thing")).toBe("#636e72");
  });

  it("returns fallback for undefined", () => {
    expect(categoryColor(undefined)).toBe("#636e72");
  });
});

describe("formatTime", () => {
  it("returns a non-empty string for a Date", () => {
    const s = formatTime(new Date(2024, 0, 15, 14, 30));
    expect(typeof s).toBe("string");
    expect(s.length).toBeGreaterThan(0);
  });
});

describe("formatDate", () => {
  it("returns a non-empty string for a Date", () => {
    const s = formatDate(new Date(2024, 0, 15));
    expect(typeof s).toBe("string");
    expect(s.length).toBeGreaterThan(0);
  });
});

describe("dayKey", () => {
  it("returns a YYYY-MM-DD string", () => {
    expect(dayKey(new Date(2024, 0, 5))).toBe("2024-01-05");
    expect(dayKey(new Date(2024, 11, 31))).toBe("2024-12-31");
  });

  it("returns the same key for the same date", () => {
    const a = new Date(2024, 5, 15, 10, 0);
    const b = new Date(2024, 5, 15, 23, 59);
    expect(dayKey(a)).toBe(dayKey(b));
  });

  it("returns different keys for different dates", () => {
    expect(dayKey(new Date(2024, 0, 1))).not.toBe(dayKey(new Date(2024, 0, 2)));
  });
});

describe("shenas-event-gantt element", () => {
  it("renders without errors", async () => {
    const el = document.createElement("shenas-event-gantt") as HTMLElement & {
      updateComplete: Promise<boolean>;
    };
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot).toBeTruthy();
    expect(el.shadowRoot!.innerHTML.length).toBeGreaterThan(0);
    el.remove();
  });
});

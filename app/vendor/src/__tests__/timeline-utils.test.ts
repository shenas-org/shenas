import { describe, it, expect } from "vitest";
import { formatTime, formatDate, dayKey, computeBarPosition } from "../shenas-frontends/timeline-utils.ts";

describe("timeline-utils", () => {
  describe("formatTime", () => {
    it("returns a non-empty time string", () => {
      const date = new Date("2026-04-12T14:30:00");
      const result = formatTime(date);
      expect(typeof result).toBe("string");
      expect(result.length).toBeGreaterThan(0);
    });

    it("handles midnight", () => {
      const date = new Date("2026-04-12T00:00:00");
      const result = formatTime(date);
      expect(typeof result).toBe("string");
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe("formatDate", () => {
    it("returns a non-empty date string", () => {
      const date = new Date("2026-04-12T14:30:00");
      const result = formatDate(date);
      expect(typeof result).toBe("string");
      expect(result).toContain("Apr");
    });
  });

  describe("dayKey", () => {
    it("returns a string key for the date (YYYY-MM-DD)", () => {
      const date = new Date("2026-04-12T14:30:00");
      const key = dayKey(date);
      expect(key).toBe("2026-04-12");
    });

    it("handles different dates", () => {
      const date1 = new Date("2026-01-01T00:00:00");
      const date2 = new Date("2026-12-31T23:59:59");
      expect(dayKey(date1)).toBe("2026-01-01");
      expect(dayKey(date2)).toBe("2026-12-31");
    });
  });

  describe("computeBarPosition", () => {
    it("computes position for a full-day event", () => {
      const start = new Date("2026-04-12T00:00:00");
      const position = computeBarPosition(start, 24 * 60);
      expect(position.leftPct).toBe(0);
      expect(position.widthPct).toBeCloseTo(100, 1);
    });

    it("computes position for a morning event", () => {
      const start = new Date("2026-04-12T08:00:00");
      const position = computeBarPosition(start, 60);
      expect(position.leftPct).toBeCloseTo((8 / 24) * 100, 1);
      expect(position.widthPct).toBeCloseTo((1 / 24) * 100, 1);
    });

    it("computes position for an afternoon event", () => {
      const start = new Date("2026-04-12T14:00:00");
      const position = computeBarPosition(start, 90);
      expect(position.leftPct).toBeCloseTo((14 / 24) * 100, 1);
      expect(position.widthPct).toBeCloseTo((1.5 / 24) * 100, 1);
    });
  });
});

import { describe, it, expect, beforeEach, vi } from "vitest";
import { mockResponse } from "./setup.ts";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../hypotheses-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

describe("shenas-hypotheses", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({
        data: {
          hypotheses: [
            {
              id: 1,
              question: "Does sleep affect HRV?",
              plan: "Compare sleep duration with next-day HRV",
              inputs: null,
              interpretation: "Strong positive correlation",
              model: "claude-sonnet",
              mode: "hypothesis",
              promotedTo: null,
              createdAt: "2025-01-15",
              recipeJson: "{}",
              resultJson: '{"rows": []}',
            },
            {
              id: 2,
              question: "Caffeine and sleep quality",
              plan: "Correlate caffeine intake with sleep score",
              inputs: null,
              interpretation: "Moderate negative",
              model: "claude-sonnet",
              mode: "exploration",
              promotedTo: "caffeine_sleep",
              createdAt: "2025-01-16",
              recipeJson: "{}",
              resultJson: null,
            },
          ],
          analysisModes: [
            { name: "hypothesis", display_name: "Hypothesis", description: "" },
            { name: "exploration", display_name: "Exploration", description: "" },
          ],
        },
      }),
    );
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-hypotheses");
    expect(el.tagName.toLowerCase()).toBe("shenas-hypotheses");
  });

  it("has default property values", () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    expect(el._selectedId).toBeNull();
    expect(el._question).toBe("");
    expect(el._busy).toBe(false);
    expect(el._error).toBe("");
    expect(el._promoteName).toBe("");
    expect(el._selectedMode).toBe("hypothesis");
  });

  // -- _select -----------------------------------------------------------

  it("selects a hypothesis by id", () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    el._select(42);
    expect(el._selectedId).toBe(42);
    expect(el._error).toBe("");
  });

  it("clears error when selecting", () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    el._error = "old error";
    el._select(1);
    expect(el._error).toBe("");
  });

  // -- _ask validation ---------------------------------------------------

  it("does nothing when asking empty question", async () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    el._question = "  ";
    await el._ask();
    expect(el._busy).toBe(false);
  });

  // -- _promote validation -----------------------------------------------

  it("does nothing when promoting without selected id", async () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    el._selectedId = null;
    el._promoteName = "test";
    await el._promote();
    // Should return early without error
    expect(el._error).toBe("");
  });

  it("does nothing when promoting without name", async () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    el._selectedId = 1;
    el._promoteName = "";
    await el._promote();
    expect(el._error).toBe("");
  });

  // -- _fork validation --------------------------------------------------

  it("does nothing when forking without selected id", async () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    el._selectedId = null;
    await el._fork();
    expect(el._error).toBe("");
  });

  // -- _renderResult -----------------------------------------------------

  it("renders no-result message for null resultJson", () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    const result = el._renderResult(null);
    expect(result).toBeTruthy();
  });

  it("renders parsed JSON for valid resultJson", () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    const result = el._renderResult('{"summary": "test"}');
    expect(result).toBeTruthy();
  });

  it("handles invalid JSON gracefully", () => {
    const el = document.createElement("shenas-hypotheses") as AnyEl;
    const result = el._renderResult("{bad json");
    expect(result).toBeTruthy();
  });
});

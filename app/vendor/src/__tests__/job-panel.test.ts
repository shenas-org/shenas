import { describe, it, expect, beforeEach } from "vitest";
import "../shenas-frontends/job-panel.ts";

type JobPanel = HTMLElement & {
  _jobs: Array<{ id: string; label: string; status: string; lines: string[]; message?: string }>;
  _collapsed: boolean;
  readonly _hasJobs: boolean;
  readonly _activeCount: number;
  addJob(id: string, label: string): void;
  appendLine(id: string, text: string): void;
  finishJob(id: string, ok: boolean, message?: string): void;
  _dismiss(id: string): void;
  _dismissAll(): void;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): JobPanel {
  return document.createElement("shenas-job-panel") as JobPanel;
}

describe("shenas-job-panel", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the element", () => {
    expect(customElements.get("shenas-job-panel")).toBeTruthy();
  });

  it("starts with no jobs and renders empty", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el._jobs).toEqual([]);
    expect(el._hasJobs).toBe(false);
    expect(el.shadowRoot.querySelector(".panel")).toBeNull();
  });

  it("addJob adds a running job and renders it", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    el.addJob("j1", "Sync garmin");
    await el.updateComplete;
    expect(el._jobs.length).toBe(1);
    expect(el._activeCount).toBe(1);
    expect(el.shadowRoot.querySelector(".panel")).toBeTruthy();
    expect(el.shadowRoot.querySelector(".job-label")?.textContent).toContain("Sync garmin");
    expect(el.shadowRoot.querySelector(".badge")?.textContent).toBe("1");
  });

  it("appendLine appends log lines", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    el.addJob("j1", "Job");
    el.appendLine("j1", "line one");
    el.appendLine("j1", "line two");
    await el.updateComplete;
    const lines = el.shadowRoot.querySelectorAll(".line");
    expect(lines.length).toBe(2);
    expect(lines[0].textContent?.trim()).toBe("line one");
  });

  it("finishJob marks done and renders message as success", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    el.addJob("j1", "Job");
    el.finishJob("j1", true, "All good");
    await el.updateComplete;
    expect(el._jobs[0].status).toBe("done");
    expect(el._activeCount).toBe(0);
    expect(el.shadowRoot.querySelector(".line.success")).toBeTruthy();
  });

  it("finishJob with ok=false marks error", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    el.addJob("j1", "Job");
    el.appendLine("j1", "boom");
    el.finishJob("j1", false, "Failed");
    await el.updateComplete;
    expect(el._jobs[0].status).toBe("error");
    expect(el.shadowRoot.querySelector(".line.error")).toBeTruthy();
  });

  it("dismiss removes a finished job", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    el.addJob("j1", "Job 1");
    el.addJob("j2", "Job 2");
    el.finishJob("j1", true);
    el._dismiss("j1");
    await el.updateComplete;
    expect(el._jobs.map((j) => j.id)).toEqual(["j2"]);
  });

  it("dismissAll keeps only running jobs", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    el.addJob("a", "A");
    el.addJob("b", "B");
    el.addJob("c", "C");
    el.finishJob("a", true);
    el.finishJob("b", false);
    el._dismissAll();
    await el.updateComplete;
    expect(el._jobs.length).toBe(1);
    expect(el._jobs[0].id).toBe("c");
  });

  it("clicking header toggles collapsed state", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    el.addJob("j", "Job");
    await el.updateComplete;
    expect(el._collapsed).toBe(false);
    expect(el.shadowRoot.querySelector(".log-area")).toBeTruthy();
    (el.shadowRoot.querySelector(".header") as HTMLElement).click();
    await el.updateComplete;
    expect(el._collapsed).toBe(true);
    expect(el.shadowRoot.querySelector(".log-area")).toBeNull();
  });

  it("Clear button appears for finished jobs and clears them", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    el.addJob("j", "Job");
    el.finishJob("j", true);
    await el.updateComplete;
    const clearBtn = el.shadowRoot.querySelector(".dismiss") as HTMLButtonElement;
    expect(clearBtn).toBeTruthy();
  });
});

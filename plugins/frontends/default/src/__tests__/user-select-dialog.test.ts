import { describe, it, expect, beforeEach, vi } from "vitest";
import { mockResponse } from "./setup.ts";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../user-select-dialog.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-user-select-dialog") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-user-select-dialog", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse([
        { id: 1, username: "alice" },
        { id: 2, username: "bob" },
      ]),
    );
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-user-select-dialog");
    expect(el.tagName.toLowerCase()).toBe("shenas-user-select-dialog");
  });

  it("has default property values", () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    expect(el.apiBase).toBe("/api");
    expect(el.cancellable).toBe(false);
    expect(el._users).toEqual([]);
    expect(el._expandedUserId).toBeNull();
    expect(el._password).toBe("");
    expect(el._regUsername).toBe("");
    expect(el._regPassword).toBe("");
    expect(el._error).toBeNull();
    expect(el._loading).toBe(false);
  });

  // -- expand / collapse user --------------------------------------------

  it("expands a user row", () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._expandUser(1);
    expect(el._expandedUserId).toBe(1);
    expect(el._password).toBe("");
    expect(el._error).toBeNull();
  });

  it("collapses user row when clicking same user", () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._expandUser(1);
    expect(el._expandedUserId).toBe(1);
    el._expandUser(1);
    expect(el._expandedUserId).toBeNull();
  });

  it("switches to different user", () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._expandUser(1);
    el._expandUser(2);
    expect(el._expandedUserId).toBe(2);
    expect(el._password).toBe("");
  });

  // -- login validation ---------------------------------------------------

  it("requires password for login", async () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._password = "";
    await el._login({ id: 1, username: "alice" });
    expect(el._error).toBe("Enter your password");
  });

  it("dispatches user-selected on successful login", async () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._password = "secret";
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockResponse({ id: 1, username: "alice", token: "tok123" }),
    );
    const handler = vi.fn();
    el.addEventListener("user-selected", handler);
    await el._login({ id: 1, username: "alice" });
    expect(handler).toHaveBeenCalled();
    const detail = handler.mock.calls[0][0].detail;
    expect(detail.userId).toBe(1);
    expect(detail.username).toBe("alice");
    expect(detail.token).toBe("tok123");
  });

  it("shows error on failed login", async () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._password = "wrong";
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockResponse({ detail: "Invalid credentials" }, false),
    );
    await el._login({ id: 1, username: "alice" });
    expect(el._error).toBe("Invalid credentials");
    expect(el._loading).toBe(false);
  });

  it("shows generic error on login network failure", async () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._password = "pass";
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("network"));
    await el._login({ id: 1, username: "alice" });
    expect(el._error).toBe("Login failed");
    expect(el._loading).toBe(false);
  });

  // -- register validation ------------------------------------------------

  it("requires username for registration", async () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._regUsername = "   ";
    el._regPassword = "pass";
    await el._register();
    expect(el._error).toBe("Enter a username");
  });

  it("requires password for registration", async () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._regUsername = "newuser";
    el._regPassword = "";
    await el._register();
    expect(el._error).toBe("Enter a password");
  });

  it("dispatches user-selected on successful registration", async () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._regUsername = "newuser";
    el._regPassword = "pass";
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockResponse({ id: 3, username: "newuser", token: "newtok" }),
    );
    const handler = vi.fn();
    el.addEventListener("user-selected", handler);
    await el._register();
    expect(handler).toHaveBeenCalled();
    const detail = handler.mock.calls[0][0].detail;
    expect(detail.userId).toBe(3);
    expect(detail.username).toBe("newuser");
    expect(detail.token).toBe("newtok");
  });

  it("shows error on failed registration", async () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._regUsername = "taken";
    el._regPassword = "pass";
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockResponse({ detail: "Username already exists" }, false),
    );
    await el._register();
    expect(el._error).toBe("Username already exists");
    expect(el._loading).toBe(false);
  });

  it("shows generic error on register network failure", async () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    el._regUsername = "newuser";
    el._regPassword = "pass";
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("network"));
    await el._register();
    expect(el._error).toBe("Registration failed");
    expect(el._loading).toBe(false);
  });

  // -- _dispatch ----------------------------------------------------------

  it("dispatches user-selected with correct detail", () => {
    const el = document.createElement("shenas-user-select-dialog") as AnyEl;
    const handler = vi.fn();
    el.addEventListener("user-selected", handler);
    el._dispatch(5, "testuser", "token-abc");
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler.mock.calls[0][0].detail).toEqual({
      userId: 5,
      username: "testuser",
      token: "token-abc",
    });
  });

  // -- _loadUsers ---------------------------------------------------------

  it("loads users from API on connect", async () => {
    const el = mount();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(el._users.length).toBe(2);
    expect(el._users[0].username).toBe("alice");
  });

  it("handles load users failure gracefully", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("offline"));
    const el = mount();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(el._users).toEqual([]);
  });
});

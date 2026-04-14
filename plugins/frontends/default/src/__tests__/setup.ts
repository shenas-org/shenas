// Suppress Lit dev mode warning in tests -- tests run in dev mode by default
// but the warning is noisy and not actionable.
(globalThis as Record<string, unknown>).litIssuedWarnings ??= new Set(["dev-mode"]);

import "urlpattern-polyfill";

/**
 * Apollo's HttpLink expects Response objects with .text(), .clone(), and
 * .headers.get(). Test files mock fetch with bare ``{ ok, json }`` objects.
 *
 * Export ``mockResponse()`` so test files can wrap their mock values.
 */
export function mockResponse(data: unknown, ok = true) {
  const body = JSON.stringify(typeof data === "string" ? data : data);
  return {
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Error",
    headers: new Headers({ "Content-Type": "application/json" }),
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(body),
    clone() {
      return mockResponse(data, ok);
    },
    body: null,
  };
}

// happy-dom 17.6.3 has a Lit template parser bug on data-list's <tr class="${...}">
// template ("Detected duplicate attribute bindings"). This shows up as unhandled
// rejections from background renders during tests. Suppress them so the test process
// doesn't exit non-zero from a known-benign happy-dom bug.
if (typeof process !== "undefined" && process.on) {
  process.on("unhandledRejection", (reason: unknown) => {
    const msg = String(reason);
    if (msg.includes("Detected duplicate attribute bindings")) {
      return;
    }
    throw reason;
  });
}

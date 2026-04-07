import "urlpattern-polyfill";

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

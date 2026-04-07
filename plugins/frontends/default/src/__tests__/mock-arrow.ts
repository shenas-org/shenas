// Mock for /vendor/apache-arrow.js in tests
export function tableFromIPC(): { toArray: () => unknown[] } {
  return { toArray: () => [] };
}

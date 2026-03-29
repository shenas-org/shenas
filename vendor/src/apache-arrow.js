// Re-export arrow functions used by components.
// Using dynamic import to prevent Vite from tree-shaking away the exports.
import * as arrow from "apache-arrow";
export const { tableFromIPC, tableFromArrays, tableToIPC } = arrow;

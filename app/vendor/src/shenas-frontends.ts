/**
 * shenas-frontends -- shared utilities and components for frontend plugins.
 *
 * Provides API helpers, styling, constants, and reusable Lit components
 * used by both the default and focus frontends (and available to dashboards).
 */

// Utilities
export {
  apiFetch,
  apiFetchFull,
  arrowQuery,
  gql,
  gqlFull,
  openExternal,
  registerCommands,
  renderMessage,
} from "./shenas-frontends/api.ts";

export { formatHotkey, matchesHotkey, parseHotkey, PLUGIN_KINDS, sortActions } from "./shenas-frontends/constants.ts";

export { arrowDatesToUnix, arrowToColumns, arrowToRows, query } from "./shenas-frontends/arrow.ts";
export type { RowData, Table } from "./shenas-frontends/arrow.ts";

export {
  buttonStyles,
  formStyles,
  linkStyles,
  messageStyles,
  tableStyles,
  tabStyles,
  utilityStyles,
} from "./shenas-frontends/shared-styles.ts";

// Components (self-register custom elements)
import "./shenas-frontends/command-palette.ts";
import "./shenas-frontends/job-panel.ts";
import "./shenas-frontends/shenas-page.ts";
import "./shenas-frontends/status-toggle.ts";
import "./shenas-frontends/data-list.ts";
import "./shenas-frontends/form-panel.ts";

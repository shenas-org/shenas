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
  registerCommands,
  renderMessage,
} from "./shenas-frontends/api.js";

export {
  formatHotkey,
  matchesHotkey,
  parseHotkey,
  PLUGIN_KINDS,
  sortActions,
} from "./shenas-frontends/constants.js";

export {
  buttonStyles,
  formStyles,
  linkStyles,
  messageStyles,
  tableStyles,
  tabStyles,
  utilityStyles,
} from "./shenas-frontends/shared-styles.js";

// Components (self-register custom elements)
import "./shenas-frontends/command-palette.js";
import "./shenas-frontends/job-panel.js";
import "./shenas-frontends/shenas-page.js";
import "./shenas-frontends/status-toggle.js";
import "./shenas-frontends/data-list.js";
import "./shenas-frontends/form-panel.js";

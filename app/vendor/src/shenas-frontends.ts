/**
 * shenas-frontends -- shared utilities and components for frontend plugins.
 *
 * Provides API helpers, styling, constants, and reusable Lit components
 * used by both the default and focus frontends (and available to dashboards).
 */

// Apollo Client
export { getClient, gql as gqlTag } from "./shenas-frontends/apollo.ts";
export { ApolloQueryController, ApolloMutationController } from "@apollo-elements/core";

// Utilities
export {
  apiFetch,
  apiFetchFull,
  arrowQuery,
  openExternal,
  registerCommands,
  renderMessage,
} from "./shenas-frontends/api.ts";

export { formatHotkey, matchesHotkey, parseHotkey, sortActions } from "./shenas-frontends/constants.ts";

export { arrowDatesToUnix, arrowToColumns, arrowToRows, query } from "./shenas-frontends/arrow.ts";
export type { RowData, Table } from "./shenas-frontends/arrow.ts";

export type { MessageBanner } from "./shenas-frontends/api.ts";

export {
  CATEGORY_COLORS,
  categoryColor,
  computeBarPosition,
  dayKey,
  formatDate,
  formatTime,
} from "./shenas-frontends/timeline-utils.ts";
export type { BarPosition, EventItem } from "./shenas-frontends/timeline-utils.ts";

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
import "./shenas-frontends/field.ts";
import "./shenas-frontends/dropdown.ts";

/**
 * Shared Cytoscape style definitions for entity graphs.
 *
 * Used by both the Flow page (entity-centric view) and the Entities page
 * to ensure consistent node/edge appearance.
 */

/** Node styles for entity graphs, keyed by entity type. */
export const ENTITY_NODE_COLORS: Record<string, string> = {
  human: "#728f67",
  animal: "#c98a5c",
  residence: "#6b8ab0",
  vehicle: "#7a7a9c",
  device: "#9a6b8a",
  organization: "#8a7a6b",
};

/** Default entity node color when the type has no specific mapping. */
export const ENTITY_NODE_DEFAULT_COLOR = "#8a9a84";

/** Style for the "Me" entity node -- larger, bordered, stands out. */
export const ME_NODE_STYLE = {
  "border-width": 3,
  "border-color": "#2c2c28",
  "font-weight": "bold",
};

/** Base entity node style definitions for Cytoscape. */
export function entityNodeStyles(): Array<{ selector: string; style: Record<string, unknown> }> {
  const styles: Array<{ selector: string; style: Record<string, unknown> }> = [];
  for (const [kind, color] of Object.entries(ENTITY_NODE_COLORS)) {
    styles.push({ selector: `node[kind="${kind}"]`, style: { "background-color": color } });
  }
  styles.push({ selector: 'node[isMe="yes"]', style: ME_NODE_STYLE });
  return styles;
}

/** Base edge styles for entity relationship graphs. */
export const ENTITY_EDGE_STYLES: Array<{ selector: string; style: Record<string, unknown> }> = [
  {
    selector: "edge",
    style: {
      "curve-style": "bezier",
      "target-arrow-shape": "triangle",
      "target-arrow-color": "#999",
      "line-color": "#999",
      width: 2,
      label: "data(label)",
      "font-size": 9,
      color: "#666",
      "text-rotation": "autorotate",
      "text-margin-y": -8,
    },
  },
];

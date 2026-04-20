/** Minimal cytoscape mock for tests that import entities-page. */
function cytoscape() {
  return {
    add: () => {},
    layout: () => ({ run: () => {} }),
    on: () => {},
    destroy: () => {},
    resize: () => {},
    fit: () => {},
    nodes: () => ({ length: 0 }),
    edges: () => ({ length: 0 }),
    elements: () => ({ length: 0 }),
    style: () => ({ update: () => {} }),
  };
}

cytoscape.use = () => {};

export default cytoscape;
export const dagre = {};

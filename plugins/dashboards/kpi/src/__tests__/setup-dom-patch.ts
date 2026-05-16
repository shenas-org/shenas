// happy-dom strips table-specific elements (<tr>, <td>, <th>, etc.) from
// HTMLTemplateElement.innerHTML when they appear without a surrounding <table>.
// Lit relies on template.innerHTML to parse its template strings, so class/event
// attribute bindings on table elements become ChildParts instead of AttributeParts,
// causing "Detected duplicate attribute bindings" in dev mode and incorrect rendering.
//
// This patch intercepts the innerHTML setter: when the HTML begins with a table
// element, it wraps the content in proper table context for parsing, then moves
// the correctly-preserved nodes back into the template content fragment.

const TABLE_START = /^\s*<(tr|td|th|col|colgroup|thead|tbody|tfoot)[\s>\/]/i;

function patchHtmlTemplateElement(): void {
  const descriptor = Object.getOwnPropertyDescriptor(HTMLTemplateElement.prototype, "innerHTML");
  if (!descriptor?.set) return;

  const origSet = descriptor.set;

  Object.defineProperty(HTMLTemplateElement.prototype, "innerHTML", {
    ...descriptor,
    set(this: HTMLTemplateElement, value: string) {
      const m = TABLE_START.exec(value);
      if (!m) {
        origSet.call(this, value);
        return;
      }

      const tag = m[1].toLowerCase();
      let wrapped: string;
      if (tag === "td" || tag === "th" || tag === "col") {
        wrapped = `<table><tbody><tr>${value}</tr></tbody></table>`;
      } else if (tag === "tr" || tag === "colgroup") {
        wrapped = `<table><tbody>${value}</tbody></table>`;
      } else {
        // thead, tbody, tfoot
        wrapped = `<table>${value}</table>`;
      }

      // Parse with full table context so elements and attributes are preserved
      origSet.call(this, wrapped);

      // Identify the container whose children are the original content nodes
      const content = this.content;
      const table = content.firstChild as Element | null;
      if (!table || table.nodeName !== "TABLE") return;

      let source: Element | null;
      if (tag === "td" || tag === "th" || tag === "col") {
        // children live inside <table><tbody><tr>
        source = ((table.firstChild as Element)?.firstChild as Element) ?? null;
      } else if (tag === "tr" || tag === "colgroup") {
        // children live inside <table><tbody>
        source = (table.firstChild as Element) ?? null;
      } else {
        // thead/tbody/tfoot children live directly inside <table>
        source = table;
      }

      if (!source) return;

      // Replace the wrapper-wrapped content with just the unwrapped children
      while (content.firstChild) content.removeChild(content.firstChild);
      while (source.firstChild) content.appendChild(source.firstChild);
    },
  });
}

patchHtmlTemplateElement();

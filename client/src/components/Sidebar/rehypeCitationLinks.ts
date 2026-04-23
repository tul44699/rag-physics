import type { Element, Root, Text } from 'hast';
import { CONTINUE, SKIP, visit } from 'unist-util-visit';

/**
 * Rehype plugin that transforms [N] patterns in text nodes into
 * <cite-link n="N">[N]</cite-link> elements for clickable citations.
 */
export default function rehypeCitationLinks() {
  return (tree: Root) => {
    visit(tree, 'text', (node, index, parent) => {
      const textNode = node as Text;
      const parentEl = parent as Element | null;
      const idx = index as number | null;
      if (!parentEl || idx == null) return CONTINUE;

      const parts = textNode.value.split(/(\[\d+\])/g);
      if (parts.length === 1) return CONTINUE;

      const children: (Text | Element)[] = [];
      for (const part of parts) {
        const m = part.match(/^\[(\d+)\]$/);
        if (m) {
          children.push({
            type: 'element',
            tagName: 'cite-link',
            properties: { n: String(m[1]) },
            children: [{ type: 'text', value: part }],
          });
        } else if (part) {
          children.push({ type: 'text', value: part });
        }
      }

      parentEl.children.splice(idx, 1, ...children);
      return [SKIP, idx + children.length];
    });
  };
}

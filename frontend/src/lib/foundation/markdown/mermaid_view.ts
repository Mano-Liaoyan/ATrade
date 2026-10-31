// The diagram of a markdown Mermaid block: pele (a Mermaid renderer to SVG with CSS variable colors, no runtime
// dependencies). The page loads pele and each diagram type only when a closed Mermaid block needs it.
// The diagram text is untrusted. pele escapes the text and limits the size; ATrade also turns off links and images,
// and the SVG goes through sanitizeSvg before it enters the page.

export interface MermaidView {
  destroy: () => void;
}

const SVG_NAMESPACE = 'http://www.w3.org/2000/svg';
const UNSAFE_ELEMENTS = 'script, foreignObject, iframe, object, embed, use[href^="http"], image, a';

/** The SVG of pele without scripts, event attributes, external references, or links. */
export function sanitizeSvg(svg: string): Node {
  const parsed = new DOMParser().parseFromString(svg, 'image/svg+xml');
  const root = parsed.documentElement;
  if (root.namespaceURI !== SVG_NAMESPACE || root.querySelector('parsererror') !== null) {
    throw new Error('The diagram is not an SVG image.');
  }
  for (const element of root.querySelectorAll(UNSAFE_ELEMENTS)) {
    element.replaceWith(...element.childNodes);
  }
  for (const element of [root, ...root.querySelectorAll('*')]) {
    for (const attribute of [...element.attributes]) {
      const name = attribute.name.toLowerCase();
      const isEvent = name.startsWith('on');
      const isExternalReference = (name === 'href' || name === 'xlink:href') && !attribute.value.startsWith('#');
      if (isEvent || isExternalReference) {
        element.removeAttribute(attribute.name);
      }
    }
  }
  return document.importNode(root, true);
}

/** Draws the diagram in the element. Rejects when pele cannot read the text: the caller shows the code block. */
export async function mountMermaid(element: HTMLElement, text: string, idPrefix: string): Promise<MermaidView> {
  const { mountAsync } = await import('pele/lazy');
  const mounted = await mountAsync(element, text, {
    idPrefix,
    links: false,
    images: false,
    zoom: false,
    sanitize: sanitizeSvg,
    onError: () => {
      // The error is in `mounted.error`.
    },
  });
  if (mounted.error !== undefined && mounted.error !== null) {
    mounted.destroy();
    throw mounted.error instanceof Error ? mounted.error : new Error('The diagram did not render.');
  }
  return {
    destroy: () => {
      mounted.destroy();
    },
  };
}

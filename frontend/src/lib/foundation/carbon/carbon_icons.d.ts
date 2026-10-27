// @carbon/icons has no TypeScript declarations. Each module under es/<icon name>/<size>.js exports one icon
// descriptor: the svg element, its attributes, and its child elements.
declare module '@carbon/icons/es/*' {
  export interface CarbonIconNode {
    elem: string;
    attrs: Record<string, string | number>;
    content?: CarbonIconNode[];
  }
  const icon: CarbonIconNode & { name: string; size: number };
  export default icon;
}

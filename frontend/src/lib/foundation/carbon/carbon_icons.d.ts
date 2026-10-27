// Types of the @carbon/icons ES modules. The package has no TypeScript declarations.
// The shape is the same as CarbonIcon in icon_types.ts.
declare module '@carbon/icons/es/*' {
  interface CarbonIconNode {
    elem: string;
    attrs: Record<string, string | number>;
    content?: CarbonIconNode[];
  }

  const icon: CarbonIconNode & { name: string; size: number };
  export default icon;
}

// The shape of an icon descriptor of @carbon/icons (`@carbon/icons/es/<name>/<size>.js`): an svg node with its child
// nodes. carbon_icons.d.ts declares the icon modules with this type, and the Icon component renders it.

export interface CarbonIconNode {
  elem: string;
  attrs: Record<string, string | number>;
  content?: CarbonIconNode[];
}

export interface CarbonIcon extends CarbonIconNode {
  name: string;
  size: number;
}

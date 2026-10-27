// The shape of one @carbon/icons icon: an SVG element and its child elements.
export interface CarbonIconNode {
  elem: string;
  attrs: Record<string, string | number>;
  content?: CarbonIconNode[];
}

export interface CarbonIcon extends CarbonIconNode {
  name: string;
  size: number;
}

// The shape of an icon descriptor of @carbon/icons: an svg element with child elements (paths, circles, rects).
export interface CarbonIconElement {
  elem: string;
  attrs: Record<string, string | number>;
  content?: CarbonIconElement[];
}

export interface CarbonIconDescriptor extends CarbonIconElement {
  name: string;
  size: number;
}

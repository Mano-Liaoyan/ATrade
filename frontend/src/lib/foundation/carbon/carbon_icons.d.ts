// @carbon/icons has no type declarations. Each file @carbon/icons/es/<name>/<size>.js exports one icon descriptor.
declare module '@carbon/icons/es/*' {
  import type { CarbonIconDescriptor } from './carbon_icon';

  const icon: CarbonIconDescriptor;
  export default icon;
}

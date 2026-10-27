// @carbon/icons has no TypeScript declarations. An icon module (`@carbon/icons/es/<name>/<size>.js`) exports one
// icon descriptor. Render it with the Icon component.
declare module '@carbon/icons/es/*' {
  const icon: import('./carbon_icon').CarbonIcon;
  export default icon;
}

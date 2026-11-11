// pi-web-access has no type declarations. Its pi extension is the default export of dist/index.js.
declare module 'pi-web-access/dist/index.js' {
  import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';

  const extension: ExtensionFactory;
  export default extension;
}

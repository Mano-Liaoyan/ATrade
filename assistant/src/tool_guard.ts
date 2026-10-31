// The second guard of 25.2.1: a pi `tool_call` handler that refuses each tool that is not in the tool list.
// The first guard is that pi has no built-in tools. The main control is the allow-list of port 8001 of web.
import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';

export function createToolGuard(allowedToolNames: readonly string[]): ExtensionFactory {
  return (pi) => {
    pi.on('tool_call', (event) => {
      if (allowedToolNames.includes(event.toolName)) {
        return undefined;
      }
      return { block: true, reason: `${event.toolName} is not an ATrade assistant tool.` };
    });
  };
}

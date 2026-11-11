// The second guard of 25.2.1: a pi `tool_call` handler that refuses each tool that is not in the tool list.
// The first guard is that pi has no built-in tools. The main control is the allow-list of port 8001 of web.
// It also refuses the arguments of the web tools that ATrade does not permit (25.4.5).
import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';

export function createToolGuard(allowedToolNames: readonly string[], refusedArguments: readonly string[] = []): ExtensionFactory {
  return (pi) => {
    pi.on('tool_call', (event) => {
      if (!allowedToolNames.includes(event.toolName)) {
        return { block: true, reason: `${event.toolName} is not an ATrade assistant tool.` };
      }
      const refused = refusedArguments.find((name) => name in event.input);
      if (refused !== undefined) {
        return { block: true, reason: `ATrade does not permit the argument ${refused}.` };
      }
      return undefined;
    });
  };
}

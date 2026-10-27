// Reads a parsed live socket message as a generated message type of #lib/api.
// The frontend trusts the backend message models and checks only the "type" field.

/** Returns the message when its type is one of messageTypes, else null. */
export function readSocketMessage<Message extends { type: string }>(
  message: unknown,
  messageTypes: readonly Message['type'][],
): Message | null {
  if (typeof message !== 'object' || message === null || !('type' in message) || typeof message.type !== 'string') {
    return null;
  }
  const messageType: string = message.type;
  if (!messageTypes.some((expectedType) => expectedType === messageType)) {
    return null;
  }
  return message as Message;
}

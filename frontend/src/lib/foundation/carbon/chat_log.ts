// Adapted from carbon-components-svelte (https://github.com/carbon-design-system/carbon-components-svelte/tree/main/src/Chat).
// Copyright 2019 IBM. Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0).
// ATrade changes: the grouping, the date dividers, and the scroll rule of ChatLog are pure functions here.
//
// The order of a message log: groups of one author, a divider for each new UTC date, and the decision to follow new
// messages. ChatLog, ChatMessage, and ChatDivider show the result.

export interface ChatLogMessage {
  author: string;
  /** ISO 8601 time in UTC. */
  sentAtUtc: string;
}

export type ChatLogEntry<Message extends ChatLogMessage> =
  | { kind: 'divider'; dateUtc: string }
  | { kind: 'message'; message: Message; continued: boolean };

// YYYY-MM-DD of an ISO 8601 time.
const ISO_DATE_LENGTH = 10;

/** Puts a divider before the first message of each UTC date and marks a message that continues a group. */
export function arrangeChatLog<Message extends ChatLogMessage>(
  messages: readonly Message[],
): ChatLogEntry<Message>[] {
  const entries: ChatLogEntry<Message>[] = [];
  let previous: { author: string; dateUtc: string } | undefined;
  for (const message of messages) {
    const dateUtc = new Date(message.sentAtUtc).toISOString().slice(0, ISO_DATE_LENGTH);
    const isNewDate = previous?.dateUtc !== dateUtc;
    if (isNewDate) {
      entries.push({ kind: 'divider', dateUtc });
    }
    entries.push({ kind: 'message', message, continued: !isNewDate && previous?.author === message.author });
    previous = { author: message.author, dateUtc };
  }
  return entries;
}

export interface LogScrollMetrics {
  scrollTopPixels: number;
  contentHeightPixels: number;
  viewportHeightPixels: number;
}

/** Up to this distance from the end, the user still reads the newest messages (as in ChatLog). */
export const LOG_END_THRESHOLD_PIXELS = 48;

/**
 * Decides if the log scrolls to new content. The log follows new content while the user is at the end. While the user
 * reads older messages, it does not follow. After the user scrolls back to the end, it follows again.
 */
export class LogFollower {
  followsNewContent = true;

  /** Call this at each scroll of the log. */
  measure(metrics: LogScrollMetrics): void {
    const distanceToEndPixels = metrics.contentHeightPixels - metrics.scrollTopPixels - metrics.viewportHeightPixels;
    this.followsNewContent = distanceToEndPixels <= LOG_END_THRESHOLD_PIXELS;
  }
}

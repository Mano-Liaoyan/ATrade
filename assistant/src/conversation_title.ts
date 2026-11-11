// The title of a conversation (docs/architecture/assistant.md 25.8.3).
// One model call without tools. The call is not a part of the conversation, so it is not in the JSONL file.
import type { ConversationMessage } from './conversation_files.ts';
import type { OpenedModel } from './model_selection.ts';

const ANSWER_INPUT_LENGTH = 2000;
const MAX_CHINESE_TITLE_CHARACTERS = 20;
const MAX_TITLE_WORDS = 8;
const CHINESE_CHARACTER = /\p{Script=Han}/u;
const QUOTES = /^["'“”‘’「」『』]+|["'“”‘’「」『』]+$/gu;

const TITLE_SYSTEM_PROMPT = [
  'Write a short title for a conversation between a user and an AI assistant about trading strategies.',
  'Use the language of the user message.',
  `A Chinese title has at most ${String(MAX_CHINESE_TITLE_CHARACTERS)} characters.`,
  `An English title has at most ${String(MAX_TITLE_WORDS)} words.`,
  'Answer with the title only.',
].join(' ');

/** The first line of the model answer, without quotes, cut to 20 Chinese characters or 8 words. */
export function shortenTitle(answer: string): string {
  const firstLine = answer.trim().split('\n')[0] ?? '';
  const title = firstLine.trim().replace(QUOTES, '').trim();
  if (CHINESE_CHARACTER.test(title)) {
    return Array.from(title).slice(0, MAX_CHINESE_TITLE_CHARACTERS).join('');
  }
  return title.split(/\s+/u).slice(0, MAX_TITLE_WORDS).join(' ');
}

/** One model call without tools: the system prompt and the input give the answer text. */
export type CompleteText = (systemPrompt: string, input: string) => Promise<string>;

/** The CompleteText of a pi model. */
export function completeWithPi(opened: OpenedModel): CompleteText {
  return async (systemPrompt, input) => {
    const result = await opened.modelRuntime.completeSimple(opened.model, {
      systemPrompt,
      messages: [{ role: 'user', content: input, timestamp: Date.now() }],
    });
    if (result.stopReason === 'error' || result.stopReason === 'aborted') {
      throw new Error(result.errorMessage ?? 'The model gave no title.');
    }
    return result.content
      .filter((part) => part.type === 'text')
      .map((part) => part.text)
      .join('');
  };
}

export async function generateTitle(messages: ConversationMessage[], complete: CompleteText): Promise<string> {
  const userMessage = messages.find((message) => message.role === 'user');
  const answer = messages.find((message) => message.role === 'assistant');
  if (userMessage === undefined || answer === undefined) {
    throw new Error('The conversation has no answer yet.');
  }
  const input = `User message:\n${userMessage.text}\n\nAI assistant answer:\n${answer.text.slice(0, ANSWER_INPUT_LENGTH)}`;
  const title = shortenTitle(await complete(TITLE_SYSTEM_PROMPT, input));
  if (title === '') {
    throw new Error('The model gave an empty title.');
  }
  return title;
}

import { describe, expect, it } from 'vite-plus/test';
import type { Credential, Provider } from './credentials';
import { changeProvider, describeSendButton, findDefaultSelection, listSelectItems } from './model_selection';

const PROVIDERS: Provider[] = [
  { id: 'openai', name: 'OpenAI', login_methods: ['api_key'], models: [{ id: 'gpt-a', name: 'GPT A' }, { id: 'gpt-b', name: 'GPT B' }] },
  { id: 'anthropic', name: 'Anthropic', login_methods: ['oauth'], models: [{ id: 'claude-x', name: 'Claude X' }] },
  { id: 'google', name: 'Google', login_methods: ['api_key'], models: [] },
];

function credential(id: string, name: string, provider: string): Credential {
  return { id, name, provider, type: 'api_key', key_last4: '1234', state: 'ready', state_message: null };
}

const CREDENTIALS = [credential('c1', 'Work key', 'openai'), credential('c2', 'Home key', 'openai'), credential('c3', 'Claude login', 'anthropic')];

describe('the model selection of the assistant side column', () => {
  it('starts with the last model and credential of the conversation', () => {
    expect(
      findDefaultSelection(PROVIDERS, CREDENTIALS, { provider: 'openai', model: 'gpt-b', credentialName: 'Home key' }),
    ).toEqual({ provider: 'openai', model: 'gpt-b', credentialId: 'c2' });
  });

  it('starts with the first credential and its first model for a conversation without an answer', () => {
    expect(findDefaultSelection(PROVIDERS, CREDENTIALS, { provider: null, model: null, credentialName: null })).toEqual({
      provider: 'openai',
      model: 'gpt-a',
      credentialId: 'c1',
    });
  });

  it('has no selection without a credential', () => {
    expect(findDefaultSelection(PROVIDERS, [], { provider: null, model: null, credentialName: null })).toEqual({
      provider: '',
      model: '',
      credentialId: '',
    });
  });

  it('lists only the providers with a credential, and the models and credentials of the selected provider', () => {
    const items = listSelectItems(PROVIDERS, CREDENTIALS, 'anthropic');

    expect(items.providers).toEqual([
      { value: 'openai', label: 'OpenAI' },
      { value: 'anthropic', label: 'Anthropic' },
    ]);
    expect(items.models).toEqual([{ value: 'claude-x', label: 'Claude X' }]);
    expect(items.credentials).toEqual([{ value: 'c3', label: 'Claude login' }]);
  });

  it('selects the first model and credential of a new provider', () => {
    expect(changeProvider(PROVIDERS, CREDENTIALS, 'anthropic')).toEqual({
      provider: 'anthropic',
      model: 'claude-x',
      credentialId: 'c3',
    });
  });
});

describe('the Send button', () => {
  const ready = { hasConversation: true, hasCredential: true, isConnected: true, isRunning: false };

  it('sends when a conversation, a credential, and the connection are ready', () => {
    expect(describeSendButton(ready)).toEqual({ action: 'send', label: 'Send', disabledReason: null });
  });

  it('becomes Stop while the AI assistant runs', () => {
    expect(describeSendButton({ ...ready, isRunning: true })).toEqual({ action: 'stop', label: 'Stop', disabledReason: null });
  });

  it('says why it is disabled', () => {
    expect(describeSendButton({ ...ready, hasConversation: false }).disabledReason).toBe('Start a new conversation to send.');
    expect(describeSendButton({ ...ready, hasCredential: false }).disabledReason).toBe('Add a credential to send.');
    expect(describeSendButton({ ...ready, isConnected: false }).disabledReason).toBe('Connecting to the AI assistant.');
  });
});

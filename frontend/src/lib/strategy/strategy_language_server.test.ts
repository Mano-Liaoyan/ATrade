// The WebSocket transport between the editor's language server client and /ws/strategy-language-server.
import { describe, expect, it } from 'vite-plus/test';
import { connectLanguageServerTransport, readLanguageServerUrl } from './strategy_language_server';

class FakeSocket extends EventTarget {
  readonly sentMessages: string[] = [];

  send(message: string): void {
    this.sentMessages.push(message);
  }

  receive(message: string): void {
    // eslint-disable-next-line @typescript-eslint/naming-convention -- readability-exception: the DOM names this field.
    this.dispatchEvent(new MessageEvent('message', { data: message }));
  }
}

describe('readLanguageServerUrl', () => {
  it('uses ws on an http page', () => {
    expect(readLanguageServerUrl({ protocol: 'http:', host: '127.0.0.1:8000' })).toBe(
      'ws://127.0.0.1:8000/ws/strategy-language-server',
    );
  });

  it('uses wss on an https page', () => {
    expect(readLanguageServerUrl({ protocol: 'https:', host: 'atrade.example.com' })).toBe(
      'wss://atrade.example.com/ws/strategy-language-server',
    );
  });
});

describe('connectLanguageServerTransport', () => {
  it('sends client messages and gives server messages to each subscriber', async () => {
    const socket = new FakeSocket();
    const connecting = connectLanguageServerTransport(socket);
    socket.dispatchEvent(new Event('open'));
    const transport = await connecting;
    const received: string[] = [];
    const handler = (message: string): void => {
      received.push(message);
    };

    transport.subscribe(handler);
    transport.send('{"id":1}');
    socket.receive('{"id":1,"result":null}');
    transport.unsubscribe(handler);
    socket.receive('{"id":2,"result":null}');

    expect(socket.sentMessages).toEqual(['{"id":1}']);
    expect(received).toEqual(['{"id":1,"result":null}']);
  });

  it('fails when the connection closes before it opens', async () => {
    const socket = new FakeSocket();
    const connecting = connectLanguageServerTransport(socket);

    socket.dispatchEvent(new Event('close'));

    await expect(connecting).rejects.toThrow('The language server connection did not open.');
  });
});

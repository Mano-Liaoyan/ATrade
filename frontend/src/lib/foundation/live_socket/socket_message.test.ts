// Reads a message of a live socket as the generated message type when its type matches.
import { describe, expect, it } from 'vitest';
import type { components } from '#lib/api';
import { readSocketMessage } from './index';

type HeartbeatMessage = components['schemas']['HeartbeatMessage'];
type LiveBarErrorMessage = components['schemas']['LiveBarErrorMessage'];
type LiveBarMessage = components['schemas']['LiveBarMessage'];

describe('readSocketMessage', () => {
  it('returns the message when its type is one of the expected types', () => {
    const errorMessage = { type: 'error', detail: 'IB Gateway is not connected.' };

    expect(readSocketMessage<HeartbeatMessage>({ type: 'heartbeat' }, ['heartbeat'])).toEqual({ type: 'heartbeat' });
    expect(readSocketMessage<LiveBarMessage | LiveBarErrorMessage>(errorMessage, ['bar', 'error'])).toEqual(errorMessage);
  });

  it('returns null for a different type or a message that is not an object', () => {
    expect(readSocketMessage<HeartbeatMessage>({ type: 'account' }, ['heartbeat'])).toBeNull();
    expect(readSocketMessage<HeartbeatMessage>({ kind: 'heartbeat' }, ['heartbeat'])).toBeNull();
    expect(readSocketMessage<HeartbeatMessage>('heartbeat', ['heartbeat'])).toBeNull();
    expect(readSocketMessage<HeartbeatMessage>(null, ['heartbeat'])).toBeNull();
  });
});

// The order of a message log (groups and date dividers) and the decision to follow new messages.
import { describe, expect, it } from 'vite-plus/test';
import { arrangeChatLog, LogFollower } from './chat_log';

describe('arrangeChatLog', () => {
  it('groups consecutive messages of one author', () => {
    const entries = arrangeChatLog([
      { author: 'You', sentAtUtc: '2026-10-30T09:00:00Z' },
      { author: 'You', sentAtUtc: '2026-10-30T09:01:00Z' },
      { author: 'AI assistant', sentAtUtc: '2026-10-30T09:02:00Z' },
      { author: 'AI assistant', sentAtUtc: '2026-10-30T09:03:00Z' },
      { author: 'You', sentAtUtc: '2026-10-30T09:04:00Z' },
    ]);

    expect(entries.filter((entry) => entry.kind === 'message').map((entry) => entry.continued)).toEqual([
      false,
      true,
      false,
      true,
      false,
    ]);
  });
});

describe('arrangeChatLog dates', () => {
  it('puts a divider before the first message of each new UTC date and starts a new group there', () => {
    const entries = arrangeChatLog([
      { author: 'You', sentAtUtc: '2026-10-29T23:59:00Z' },
      { author: 'You', sentAtUtc: '2026-10-30T00:01:00Z' },
      { author: 'You', sentAtUtc: '2026-10-30T00:02:00Z' },
    ]);

    expect(
      entries.map((entry) => (entry.kind === 'divider' ? entry.dateUtc : `${entry.message.sentAtUtc} ${String(entry.continued)}`)),
    ).toEqual([
      '2026-10-29',
      '2026-10-29T23:59:00Z false',
      '2026-10-30',
      '2026-10-30T00:01:00Z false',
      '2026-10-30T00:02:00Z true',
    ]);
  });

  it('has no entries for no messages', () => {
    expect(arrangeChatLog([])).toEqual([]);
  });
});

describe('LogFollower', () => {
  const viewport = { contentHeightPixels: 1000, viewportHeightPixels: 400 };

  it('follows new messages when the log opens', () => {
    expect(new LogFollower().followsNewContent).toBe(true);
  });

  it('follows new messages while the log is scrolled to the end', () => {
    const follower = new LogFollower();
    follower.measure({ ...viewport, scrollTopPixels: 600 });
    expect(follower.followsNewContent).toBe(true);
  });

  it('counts a position near the end as the end', () => {
    const follower = new LogFollower();
    follower.measure({ ...viewport, scrollTopPixels: 560 });
    expect(follower.followsNewContent).toBe(true);
  });

  it('does not follow new messages while the user reads older messages', () => {
    const follower = new LogFollower();
    follower.measure({ ...viewport, scrollTopPixels: 200 });
    expect(follower.followsNewContent).toBe(false);
  });

  it('follows new messages again after the user scrolls back to the end', () => {
    const follower = new LogFollower();
    follower.measure({ ...viewport, scrollTopPixels: 200 });
    follower.measure({ ...viewport, scrollTopPixels: 600 });
    expect(follower.followsNewContent).toBe(true);
  });
});

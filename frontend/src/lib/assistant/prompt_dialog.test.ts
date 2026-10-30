// The logic of the "Prompt" dialog (docs/architecture/assistant.md 25.9.2): the version Select, the text area,
// "Restore default", and "Save as new version".
import { describe, expect, it } from 'vite-plus/test';
import {
  addSavedVersion,
  describeSaveProblem,
  listPromptVersions,
  openPromptDialog,
  restoreDefault,
  savePromptVersion,
  selectPromptVersion,
  type PromptVersionList,
} from './index';

const VERSION_1 = { id: 11, version_number: 1, text: 'Default text.', created_at_utc: '2026-01-02T03:04:05Z' };
const VERSION_2 = { id: 12, version_number: 2, text: 'Answer in short sentences.', created_at_utc: '2026-01-03T03:04:05Z' };
const LIST: PromptVersionList = {
  prompt_versions: [VERSION_2, VERSION_1],
  default_text: 'Default text.',
  fixed_part: 'Do not send a paper order.',
};

interface RecordedRequest {
  url: string;
  method: string;
  body: string | null;
}

function recordRequests(status: number, body: unknown): { fetchFunction: typeof fetch; requests: RecordedRequest[] } {
  const requests: RecordedRequest[] = [];
  const fetchFunction: typeof fetch = (input, init) => {
    requests.push({
      url: typeof input === 'string' ? input : '',
      method: init?.method ?? 'GET',
      body: typeof init?.body === 'string' ? init.body : null,
    });
    return Promise.resolve(new Response(JSON.stringify(body), { status }));
  };
  return { fetchFunction, requests };
}

describe('the prompt dialog state', () => {
  it('opens with the latest version selected and its text in the text area', () => {
    const state = openPromptDialog(LIST);

    expect(state.selectedVersionId).toBe('12');
    expect(state.text).toBe('Answer in short sentences.');
    expect(state.fixedPart).toBe('Do not send a paper order.');
    expect(state.versionItems).toEqual([
      { value: '12', label: 'v2' },
      { value: '11', label: 'v1' },
    ]);
  });

  it('puts the text of the selected version in the text area', () => {
    const state = selectPromptVersion(openPromptDialog(LIST), '11');

    expect(state.selectedVersionId).toBe('11');
    expect(state.text).toBe('Default text.');
  });

  it('restores the default text without a request and keeps the selected version', () => {
    const state = restoreDefault({ ...openPromptDialog(LIST), text: 'Changed.' });

    expect(state.text).toBe('Default text.');
    expect(state.selectedVersionId).toBe('12');
  });

  it('adds a saved version at the top and selects it', () => {
    const savedVersion = { id: 13, version_number: 3, text: 'New.', created_at_utc: '2026-01-04T03:04:05Z' };

    const state = addSavedVersion({ ...openPromptDialog(LIST), text: 'New.' }, savedVersion);

    expect(state.selectedVersionId).toBe('13');
    expect(state.versionItems[0]).toEqual({ value: '13', label: 'v3' });
    expect(state.text).toBe('New.');
  });

  it('refuses to save an empty text', () => {
    expect(describeSaveProblem({ ...openPromptDialog(LIST), text: '  ' })).toBe('Enter the prompt text.');
    expect(describeSaveProblem(openPromptDialog(LIST))).toBeNull();
  });
});

describe('the prompt version requests', () => {
  it('lists the prompt versions', async () => {
    const { fetchFunction, requests } = recordRequests(200, LIST);

    const result = await listPromptVersions(fetchFunction);

    expect(result).toEqual({ kind: 'ok', value: LIST });
    expect(requests).toEqual([{ url: '/api/assistant/prompt-versions', method: 'GET', body: null }]);
  });

  it('saves the text as a new version', async () => {
    const { fetchFunction, requests } = recordRequests(201, VERSION_2);

    const result = await savePromptVersion(fetchFunction, 'Answer in short sentences.');

    expect(result).toEqual({ kind: 'ok', value: VERSION_2 });
    expect(requests).toEqual([
      {
        url: '/api/assistant/prompt-versions',
        method: 'POST',
        body: JSON.stringify({ text: 'Answer in short sentences.' }),
      },
    ]);
  });

  it('returns the message of a refused save', async () => {
    const { fetchFunction } = recordRequests(422, { detail: [{ loc: ['body', 'text'], msg: 'Too short', type: 'x' }] });

    const result = await savePromptVersion(fetchFunction, 'x');

    expect(result).toEqual({ kind: 'failed', message: 'text: Too short' });
  });
});

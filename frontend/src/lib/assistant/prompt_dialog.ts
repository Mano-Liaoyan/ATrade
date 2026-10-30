// The logic of the "Prompt" dialog (docs/architecture/assistant.md 25.9.2) and the prompt version requests
// (backend/src/atrade/assistant/prompt_routes.py). A prompt version does not change after it is saved, so the dialog
// only reads versions and saves new ones. "Restore default" changes only the text area: it sends no request.
import type { components } from '#lib/api';
import { requestJson, type RequestResult } from '#lib/foundation/http_request';

export type PromptVersion = components['schemas']['PromptVersionResponse'];
export type PromptVersionList = components['schemas']['PromptVersionListResponse'];

const PROMPT_VERSIONS_PATH = '/api/assistant/prompt-versions';
const FAILED_ACTION = 'The prompt version request';

export interface PromptVersionItem {
  value: string;
  label: string;
}

export interface PromptDialogState {
  versions: PromptVersion[];
  versionItems: PromptVersionItem[];
  selectedVersionId: string;
  text: string;
  defaultText: string;
  fixedPart: string;
}

export function listPromptVersions(fetchFunction: typeof fetch): Promise<RequestResult<PromptVersionList>> {
  return requestJson<PromptVersionList>(fetchFunction, FAILED_ACTION, PROMPT_VERSIONS_PATH);
}

export function savePromptVersion(fetchFunction: typeof fetch, text: string): Promise<RequestResult<PromptVersion>> {
  return requestJson<PromptVersion>(fetchFunction, FAILED_ACTION, PROMPT_VERSIONS_PATH, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ text }),
  });
}

/** "Prompt v3" at the top of a conversation uses the same number. */
export function formatPromptVersionLabel(versionNumber: number): string {
  return `v${String(versionNumber)}`;
}

function toVersionItems(versions: PromptVersion[]): PromptVersionItem[] {
  return versions.map((version) => ({ value: String(version.id), label: formatPromptVersionLabel(version.version_number) }));
}

/** The list is the newest first. The dialog opens with the latest version, the one that new conversations use. */
export function openPromptDialog(list: PromptVersionList): PromptDialogState {
  const latest = list.prompt_versions[0];
  return {
    versions: list.prompt_versions,
    versionItems: toVersionItems(list.prompt_versions),
    selectedVersionId: latest === undefined ? '' : String(latest.id),
    text: latest?.text ?? list.default_text,
    defaultText: list.default_text,
    fixedPart: list.fixed_part,
  };
}

export function selectPromptVersion(state: PromptDialogState, versionId: string): PromptDialogState {
  const version = state.versions.find((candidate) => String(candidate.id) === versionId);
  if (version === undefined) {
    return state;
  }
  return { ...state, selectedVersionId: versionId, text: version.text };
}

export function restoreDefault(state: PromptDialogState): PromptDialogState {
  return { ...state, text: state.defaultText };
}

export function addSavedVersion(state: PromptDialogState, version: PromptVersion): PromptDialogState {
  const versions = [version, ...state.versions];
  return { ...state, versions, versionItems: toVersionItems(versions), selectedVersionId: String(version.id) };
}

/** Why the text cannot be saved, or null. */
export function describeSaveProblem(state: PromptDialogState): string | null {
  return state.text.trim() === '' ? 'Enter the prompt text.' : null;
}

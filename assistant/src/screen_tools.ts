// The screen tools of the AI assistant (docs/architecture/assistant.md 25.4.3, screen.md 24.8). Each tool calls one
// screen route of port 8001.
// - create_screen, update_screen, and run_screen give a 422 problem list {"problems": [{"location", "message"}]} to
//   the model. The model corrects the screen and tries again.
// - read_screen_result gives the summary and one page of rows, default the first 50. It leaves out the excluded
//   list: the summary has the count of each exclusion reason.
import { defineTool, type ToolDefinition } from '@earendil-works/pi-coding-agent';
import { Type } from 'typebox';
import { answerResult, isSuccess, textResult, type ToolResult } from './tool_results.ts';
import type { WebPortClient } from './web_port_client.ts';

export const SCREEN_RESULT_PAGE_SIZE = 50;
const Id = Type.Integer({ minimum: 1 });
// The screen check of port 8001 checks the definition and gives the location of each problem (screen.md 24.6).
const Definition = Type.Record(Type.String(), Type.Unknown(), {
  description: 'The screen definition of screen.md 24.4.1: start, filters, indicator_conditions, and order.',
});

interface ScreenResultBody {
  id: number;
  screen_id: number;
  market: string;
  summary: { row_count: number };
  definition: unknown;
  rows: unknown[];
}

/** The content of a screen result page for the model. `next_offset` is null on the last page. */
export function summarizeScreenResult(body: ScreenResultBody, offset: number): Record<string, unknown> {
  const end = offset + body.rows.length;
  return {
    id: body.id,
    screen_id: body.screen_id,
    market: body.market,
    summary: body.summary,
    definition: body.definition,
    offset,
    rows: body.rows,
    next_offset: end < body.summary.row_count ? end : null,
  };
}

async function readScreenResult(
  client: WebPortClient,
  screenResultId: number,
  offset: number,
  signal?: AbortSignal,
): Promise<ToolResult> {
  const query = `offset=${String(offset)}&limit=${String(SCREEN_RESULT_PAGE_SIZE)}`;
  const path = `/api/screen-results/${String(screenResultId)}?${query}`;
  const answer = await client.request('GET', path, undefined, signal);
  return isSuccess(answer) ? textResult(summarizeScreenResult(answer.body as ScreenResultBody, offset)) : answerResult(answer);
}

export function createScreenTools(client: WebPortClient): ToolDefinition[] {
  return [
    defineTool({
      name: 'list_screens',
      label: 'List screens',
      description: 'Lists the saved screens: ID, name, market, and kept.',
      parameters: Type.Object({}),
      execute: async (_id, _params, signal) => answerResult(await client.request('GET', '/api/screens', undefined, signal)),
    }),
    defineTool({
      name: 'read_screen',
      label: 'Read screen',
      description: 'Reads one screen: its definition and its last 10 screen results.',
      parameters: Type.Object({ screen_id: Id }),
      execute: async (_id, params, signal) =>
        answerResult(await client.request('GET', `/api/screens/${String(params.screen_id)}`, undefined, signal)),
    }),
    defineTool({
      name: 'create_screen',
      label: 'Create screen',
      description:
        'Saves a new screen. Port 8001 adds " (AI)" to the name. When the check fails, the result is the problem ' +
        'list {"problems": [{"location", "message"}]}. Correct the definition and try again.',
      parameters: Type.Object({
        name: Type.String({ minLength: 1 }),
        market: Type.Union([Type.Literal('US'), Type.Literal('HK')]),
        definition: Definition,
      }),
      execute: async (_id, params, signal) => {
        const body = { name: params.name, market: params.market, definition: params.definition };
        return answerResult(await client.request('POST', '/api/screens', body, signal));
      },
    }),
    defineTool({
      name: 'update_screen',
      label: 'Update screen',
      description:
        'Changes a screen that you made in this conversation and that the user has not kept. For each other screen, ' +
        'port 8001 answers 403: save a new screen with create_screen. A failed check gives the problem list.',
      parameters: Type.Object({ screen_id: Id, name: Type.String({ minLength: 1 }), definition: Definition }),
      execute: async (_id, params, signal) => {
        const body = { name: params.name, definition: params.definition };
        return answerResult(await client.request('PUT', `/api/screens/${String(params.screen_id)}`, body, signal));
      },
    }),
    defineTool({
      name: 'run_screen',
      label: 'Run screen',
      description:
        'Runs a saved screen and saves a screen result. The result is the summary and the first 50 rows. ' +
        'Read more rows with read_screen_result. A failed check gives the problem list.',
      parameters: Type.Object({ screen_id: Id }),
      execute: async (_id, params, signal) => {
        const answer = await client.request('POST', `/api/screens/${String(params.screen_id)}/runs`, undefined, signal);
        return isSuccess(answer) ? textResult(summarizeScreenResult(answer.body as ScreenResultBody, 0)) : answerResult(answer);
      },
    }),
    defineTool({
      name: 'read_screen_result',
      label: 'Read screen result',
      description:
        'Reads a screen result: the summary (row count, funnel counts, count of each exclusion reason, daily bars ' +
        'date) and 50 rows from `offset`. To read the next page, use `next_offset` as `offset`.',
      parameters: Type.Object({ screen_result_id: Id, offset: Type.Optional(Type.Integer({ minimum: 0 })) }),
      execute: (_id, params, signal) => readScreenResult(client, params.screen_result_id, params.offset ?? 0, signal),
    }),
  ];
}

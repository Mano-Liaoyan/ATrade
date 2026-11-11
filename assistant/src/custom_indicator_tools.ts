// The custom indicator tools of the AI assistant (docs/architecture/assistant.md 25.4.4, indicator.md 23.10.6). Each
// tool calls one route of port 8001. There is no delete tool. list_indicators (screen_tools.ts) shows the custom
// indicators in the catalog. The other tools show the kept state and the conversation.
// - check_custom_indicator saves nothing. create_custom_indicator and update_custom_indicator give the same 422 problem
//   list {"problems": [{"location", "message"}]} to the model.
import { defineTool, type ToolDefinition } from '@earendil-works/pi-coding-agent';
import { Type } from 'typebox';
import { answerResult } from './tool_results.ts';
import type { WebPortClient } from './web_port_client.ts';

const BASE_PATH = '/api/custom-indicators';
const Id = Type.Integer({ minimum: 1 });

// The only text of the expression syntax for the model. backend/tests/indicator/test_formula_syntax_text.py compares it
// with the parser. Change it together with atrade/indicator/formula_indicator.py and indicator.md 23.10.1.
const FORMULA_SYNTAX =
  'A formula expression is not Python code. It can have only these parts: ' +
  'numbers; the operators + - * / and **, with an exponent that is a number from -10 to 10; unary - and +; ' +
  'the bar fields open, high, low, close, volume; ' +
  'the rolling functions mean(x, n), max(x, n), min(x, n), sum(x, n), std(x, n) (n at least 2), lag(x, n), with an ' +
  'integer n from 1 to 1000; quantile(x, n, q) (the quantile q from 0 to 1 of the last n values, with linear ' +
  'interpolation) and median(x, n), which is quantile(x, n, 0.5); abs(x); log(x) (natural logarithm); ' +
  'and calls to built-in indicators with a catalog key as the function name: rsi(14), sma(period=50), ' +
  'macd(output="signal"). The arguments are numbers, in the catalog order or by name. A multi-line indicator needs ' +
  'output. Call list_indicators to get the keys and the parameter ranges. An expression cannot call a custom ' +
  'indicator, and it has no comparison, attribute, or list. ' +
  'Variables: a line `name = value` before the last line gives a name to a value, and the lines after it use the ' +
  'name. Use a new line or `;` between the lines. The last line is the value of the indicator. Use a variable for ' +
  'each part that the expression has more than 1 time: the part is then calculated 1 time and its windows count ' +
  '1 time. ' +
  'Parameters: the name of a parameter of the `parameters` list is a number in the expression. It can be a normal ' +
  'number, the n of a rolling function, the q of quantile, or an argument of a built-in indicator, but not an ' +
  'exponent. The range of the parameter must be in the range of that place, and an n must be an int parameter. ' +
  'Each name that is not a bar field, a variable, or a parameter is a problem, and so is a parameter or a variable ' +
  'that the expression does not use. ' +
  'Limits: 1000 characters, 20 levels, and 20000 bars read. Rolling windows have a calculation limit: the window ' +
  'bars x the bars read must be at most 10000000. The window bars are the sum of each n of a rolling function and ' +
  'lag, and the look-back of each built-in indicator, but 0 for an exponential average. So 11 windows of 1000 bars ' +
  'are refused. The check uses the maximum of each parameter. ' +
  'Examples: `close / sma(50) - 1`, `mean(high - low, 20) / close`, `(rsi(14) - lag(rsi(14), 5)) / 5`, ' +
  '`width = std(close, 20) / mean(close, 20); width / median(width, 60) - 1`.';

const Parameter = Type.Object({
  name: Type.String({
    minLength: 1,
    maxLength: 40,
    description: 'The name in the expression: a lower-case letter, then lower-case letters, digits, and _.',
  }),
  label: Type.String({ minLength: 1, maxLength: 60, description: 'The name that the UI shows.' }),
  value_type: Type.Union([Type.Literal('int'), Type.Literal('float')]),
  default: Type.Number(),
  minimum: Type.Number(),
  maximum: Type.Number(),
  description: Type.Optional(Type.String({ maxLength: 200 })),
});

const Fields = {
  name: Type.String({ minLength: 1, maxLength: 60, description: '1 to 60 characters, without parentheses. Unique.' }),
  expression: Type.String({ minLength: 1, maxLength: 1000, description: FORMULA_SYNTAX }),
  parameters: Type.Optional(
    Type.Array(Parameter, {
      maxItems: 10,
      description:
        'The numbers of the expression that the user can change, for example the days of a window. Each chart ' +
        'indicator, screen condition, and strategy sets its own values, so 1 custom indicator is sufficient for ' +
        'all values. Use a parameter and not a fixed number for each number that the user could want to change. ' +
        'An int parameter has integer default, minimum, and maximum.',
    }),
  ),
  chart_placement: Type.Union([Type.Literal('own'), Type.Literal('price')], {
    description: '"price" for a value on the price scale. "own" for each other value.',
  }),
  value_description: Type.String({
    minLength: 1,
    maxLength: 1000,
    description: 'The meaning, the range, and the unit of the value.',
  }),
};

export function createCustomIndicatorTools(client: WebPortClient): ToolDefinition[] {
  return [
    defineTool({
      name: 'list_custom_indicators',
      label: 'List custom indicators',
      description:
        'Lists the custom indicators: ID, catalog key, name, expression, parameters, chart_placement, ' +
        'value_description, kept, and assistant_conversation_id.',
      parameters: Type.Object({}),
      execute: async (_id, _params, signal) => answerResult(await client.request('GET', BASE_PATH, undefined, signal)),
    }),
    defineTool({
      name: 'read_custom_indicator',
      label: 'Read custom indicator',
      description: 'Reads one custom indicator.',
      parameters: Type.Object({ custom_indicator_id: Id }),
      execute: async (_id, params, signal) =>
        answerResult(await client.request('GET', `${BASE_PATH}/${String(params.custom_indicator_id)}`, undefined, signal)),
    }),
    defineTool({
      name: 'check_custom_indicator',
      label: 'Check custom indicator',
      description:
        'Checks a custom indicator and saves nothing. Call it before you save. The result is ' +
        '{"problems": [{"location", "message"}], "look_back_bars", "default_look_back_bars"}: the bars that a value ' +
        'needs when each parameter has its maximum, and when each parameter has its default. A message of the ' +
        'expression gives the column. ' +
        'Correct each problem and check again. Before update_custom_indicator, give custom_indicator_id, so the ' +
        'indicator does not conflict with its own name.',
      parameters: Type.Object({ ...Fields, custom_indicator_id: Type.Optional(Id) }),
      execute: async (_id, params, signal) => {
        const { custom_indicator_id: customIndicatorId, ...body } = params;
        const query = customIndicatorId === undefined ? '' : `?custom_indicator_id=${String(customIndicatorId)}`;
        return answerResult(await client.request('POST', `${BASE_PATH}/check${query}`, body, signal));
      },
    }),
    defineTool({
      name: 'create_custom_indicator',
      label: 'Create custom indicator',
      description:
        'Saves a new custom indicator. It records this conversation and is not kept. Tell the user to click Keep on ' +
        'the Settings page. A screen can use it at once: its reference needs the `formula` object that ' +
        'list_indicators gives, and `parameters` with the values, for example {"lookback_days": 20}. A parameter ' +
        'without a value has its default. Strategy code writes FormulaIndicator(<expression>), or ' +
        'FormulaIndicator(<expression>, parameters={"lookback_days": 20}) for an expression with parameters. A ' +
        'failed check gives the problem list. Correct the fields and try again.',
      parameters: Type.Object(Fields),
      execute: async (_id, params, signal) => answerResult(await client.request('POST', BASE_PATH, params, signal)),
    }),
    defineTool({
      name: 'update_custom_indicator',
      label: 'Update custom indicator',
      description:
        'Changes a custom indicator that you made in this conversation and that the user has not kept. For each ' +
        'other custom indicator, port 8001 answers 403: save a new one with create_custom_indicator. A failed check ' +
        'gives the problem list. A saved screen, strategy version, or backtest keeps its old expression and its ' +
        'old parameters. To use other parameter values, do not change the custom indicator: change `parameters` ' +
        'of the reference.',
      parameters: Type.Object({ ...Fields, custom_indicator_id: Id }),
      execute: async (_id, params, signal) => {
        const { custom_indicator_id: customIndicatorId, ...body } = params;
        return answerResult(await client.request('PUT', `${BASE_PATH}/${String(customIndicatorId)}`, body, signal));
      },
    }),
  ];
}

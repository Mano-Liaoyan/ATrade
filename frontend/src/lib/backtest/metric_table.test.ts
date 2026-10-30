// The rows of the Metrics table (docs/architecture/backtest.md section 10.9.6).
import { describe, expect, it } from 'vite-plus/test';
import { readMetricRows, type BacktestMetrics } from './index';

const METRICS: BacktestMetrics = {
  final_equity_usd: '112345.6',
  total_return_percent: '12.35',
  max_drawdown_percent: '7.5',
  trade_count: 4,
  cagr_percent: '8.1',
  annual_volatility_percent: '14.25',
  sharpe_ratio: '1.23',
  sortino_ratio: '-0.5',
  calmar_ratio: '1.08',
  profit_factor: '2.5',
  average_win_usd: '1234.5',
  average_win_percent: '2.1',
  average_loss_usd: '-321',
  exposure_percent: '45',
  turnover_per_year: '3.2',
  win_rate_percent: '66.67',
  missing_reasons: {},
};

describe('readMetricRows', () => {
  it('gives the metrics with their names and values in one order', () => {
    const rows = readMetricRows([METRICS]);

    expect(rows.map((row) => [row.name, row.values[0]?.text])).toEqual([
      ['CAGR', '+8.10 %'],
      ['Annual volatility', '14.25 %'],
      ['Sharpe ratio', '1.23'],
      ['Sortino ratio', '-0.50'],
      ['Calmar ratio', '1.08'],
      ['Profit factor', '2.50'],
      ['Win rate', '66.67 %'],
      ['Average win (USD)', '+1,234.50 (+2.10 %)'],
      ['Average loss (USD)', '-321.00'],
      ['Exposure', '45.00 %'],
      ['Turnover', '3.20× per year'],
    ]);
  });

  it('gives each metric a definition that names the risk-free rate', () => {
    const rows = readMetricRows([METRICS]);

    expect(rows.find((row) => row.name === 'Sharpe ratio')?.definition).toBe(
      'Mean of the daily returns / standard deviation of the daily returns × √252. Risk-free rate: 0',
    );
    for (const row of rows) {
      expect(row.definition).toMatch(/\. Risk-free rate: 0$/);
    }
  });

  it('gives a dash with the reason of the API for a null value', () => {
    const rows = readMetricRows([
      {
        ...METRICS,
        calmar_ratio: null,
        average_win_usd: null,
        average_win_percent: null,
        missing_reasons: { calmar_ratio: 'The max drawdown is 0', average_win_usd: 'No round trip with a profit' },
      },
    ]);

    expect(rows.find((row) => row.name === 'Calmar ratio')?.values).toEqual([
      { text: '–', reason: 'The max drawdown is 0' },
    ]);
    expect(rows.find((row) => row.name === 'Average win (USD)')?.values).toEqual([
      { text: '–', reason: 'No round trip with a profit' },
    ]);
  });

  it('gives one value for each set of metrics', () => {
    const rows = readMetricRows([METRICS, { ...METRICS, sharpe_ratio: '0.4' }]);

    expect(rows.find((row) => row.name === 'Sharpe ratio')?.values).toEqual([{ text: '1.23' }, { text: '0.40' }]);
  });
});

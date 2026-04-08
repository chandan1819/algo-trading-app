import React, { useState, useEffect, useCallback } from 'react';
import PnLCard from '../components/PnLCard';
import { runBacktest, getBacktestResults } from '../services/api';

const sampleResults = {
  metrics: {
    cagr: 24.5,
    sharpe_ratio: 1.85,
    max_drawdown: -12.3,
    win_rate: 62.5,
    profit_factor: 1.92,
    total_trades: 156,
    total_return: 48750.00,
  },
  equity_curve: [
    100000, 101200, 99800, 102500, 104100, 103200, 105800, 107400, 106100,
    108900, 111200, 109500, 112800, 115000, 113200, 116500, 118900, 120400,
    119000, 122500, 125800, 124100, 127500, 130200, 128400, 132000, 135500,
    133800, 137200, 140000, 138500, 142000, 145800, 143200, 147500, 148750,
  ],
};

const pastBacktests = [
  { id: 1, date: '2024-12-01', strategy: 'RSI + MACD', ticker: 'RELIANCE', cagr: 24.5, sharpe: 1.85, win_rate: 62.5 },
  { id: 2, date: '2024-11-28', strategy: 'MA Crossover', ticker: 'NIFTY', cagr: 18.2, sharpe: 1.42, win_rate: 55.8 },
  { id: 3, date: '2024-11-25', strategy: 'Bollinger Breakout', ticker: 'HDFCBANK', cagr: 31.7, sharpe: 2.10, win_rate: 58.3 },
  { id: 4, date: '2024-11-20', strategy: 'VWAP Intraday', ticker: 'INFY', cagr: 15.8, sharpe: 1.25, win_rate: 51.2 },
];

const EquityCurve = ({ data }) => {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  return (
    <div className="equity-curve" style={{ height: 180 }}>
      {data.map((val, i) => {
        const height = ((val - min) / range) * 160 + 20;
        const isGreen = i === 0 || val >= data[i - 1];
        return (
          <div
            key={i}
            className="equity-bar"
            style={{
              height: `${height}px`,
              backgroundColor: isGreen ? '#48bb78' : '#e94560',
              opacity: 0.8,
            }}
            title={`\u20B9${val.toLocaleString('en-IN')}`}
          />
        );
      })}
    </div>
  );
};

const BacktestPage = () => {
  const [form, setForm] = useState({
    strategy: 'rsi_macd',
    ticker: 'RELIANCE',
    start_date: '2024-01-01',
    end_date: '2024-12-01',
    initial_capital: 100000,
  });
  const [results, setResults] = useState(null);
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState(pastBacktests);
  const [error, setError] = useState('');

  const fetchHistory = useCallback(async () => {
    try {
      const res = await getBacktestResults();
      if (Array.isArray(res.data) && res.data.length > 0) {
        setHistory(res.data);
      }
    } catch {
      // Use sample
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError('');
  };

  const handleRun = async (e) => {
    e.preventDefault();
    setRunning(true);
    setError('');
    setResults(null);
    try {
      const payload = {
        ...form,
        initial_capital: parseFloat(form.initial_capital),
      };
      const res = await runBacktest(payload);
      setResults(res.data);
    } catch (err) {
      setError(err.message || 'Backtest failed');
      // Show sample results on error for demo
      setResults(sampleResults);
    } finally {
      setRunning(false);
    }
  };

  const metrics = results?.metrics || null;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Backtesting</h1>
        <p className="text-gray-500 text-sm">Test strategies on historical data</p>
      </div>

      {/* Config Form */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-4">Backtest Configuration</h3>
        <form onSubmit={handleRun}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Strategy</label>
              <select name="strategy" value={form.strategy} onChange={handleChange} className="input-field text-sm">
                <option value="ma_crossover">MA Crossover</option>
                <option value="rsi_macd">RSI + MACD</option>
                <option value="bollinger_breakout">Bollinger Breakout</option>
                <option value="vwap_intraday">VWAP Intraday</option>
                <option value="breakout">S/R Breakout</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Ticker</label>
              <input type="text" name="ticker" value={form.ticker} onChange={handleChange} className="input-field text-sm" required />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Start Date</label>
              <input type="date" name="start_date" value={form.start_date} onChange={handleChange} className="input-field text-sm" required />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">End Date</label>
              <input type="date" name="end_date" value={form.end_date} onChange={handleChange} className="input-field text-sm" required />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Capital</label>
              <input type="number" name="initial_capital" value={form.initial_capital} onChange={handleChange} className="input-field text-sm" min="10000" step="10000" required />
            </div>
          </div>

          <div className="flex items-center gap-4 mt-4">
            <button type="submit" disabled={running} className="btn-primary text-sm">
              {running ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full"></span>
                  Running Backtest...
                </span>
              ) : (
                'Run Backtest'
              )}
            </button>
            {error && <span className="text-red-400 text-sm">{error}</span>}
          </div>
        </form>
      </div>

      {/* Results */}
      {metrics && (
        <div className="space-y-4 animate-fade-in">
          <h3 className="text-sm font-semibold text-white">Results</h3>

          {/* Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <PnLCard title="CAGR" value={metrics.cagr} suffix="%" change={metrics.cagr} />
            <PnLCard title="Sharpe Ratio" value={metrics.sharpe_ratio} change={null} />
            <PnLCard title="Max Drawdown" value={metrics.max_drawdown} suffix="%" change={metrics.max_drawdown} />
            <PnLCard title="Win Rate" value={metrics.win_rate} suffix="%" change={metrics.win_rate > 50 ? 1 : -1} />
            <PnLCard title="Profit Factor" value={metrics.profit_factor} change={metrics.profit_factor > 1 ? 1 : -1} />
            <PnLCard title="Total Return" value={metrics.total_return} prefix={'\u20B9'} change={metrics.total_return > 0 ? 1 : -1} />
          </div>

          {/* Equity Curve */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">Equity Curve</h3>
              <span className="text-xs text-gray-500 mono">
                {results.equity_curve?.length || 0} data points
              </span>
            </div>
            <EquityCurve data={results.equity_curve || sampleResults.equity_curve} />
            <div className="flex justify-between text-xs text-gray-600 mt-2">
              <span>{form.start_date}</span>
              <span>{form.end_date}</span>
            </div>
          </div>
        </div>
      )}

      {/* Past Results */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-4">Past Backtest Results</h3>
        <div className="overflow-x-auto">
          <table className="trade-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Strategy</th>
                <th>Ticker</th>
                <th>CAGR</th>
                <th>Sharpe</th>
                <th>Win Rate</th>
              </tr>
            </thead>
            <tbody>
              {history.map((r) => (
                <tr key={r.id}>
                  <td className="mono text-gray-400">{r.date}</td>
                  <td className="text-gray-300">{r.strategy}</td>
                  <td className="mono text-white font-medium">{r.ticker}</td>
                  <td className={`mono ${r.cagr >= 0 ? 'text-green-400' : 'text-red-400'}`}>{r.cagr}%</td>
                  <td className="mono text-gray-300">{r.sharpe}</td>
                  <td className="mono text-gray-300">{r.win_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default BacktestPage;

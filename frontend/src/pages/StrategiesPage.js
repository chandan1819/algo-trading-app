import React, { useState, useEffect, useCallback } from 'react';
import { getStrategies, toggleStrategy, updateStrategyConfig, runStrategy } from '../services/api';

const defaultStrategies = [
  {
    name: 'ma_crossover',
    display_name: 'Moving Average Crossover',
    description: 'Generates signals when fast MA crosses slow MA',
    enabled: false,
    params: { fast_period: 9, slow_period: 21, ticker: 'NIFTY', interval: 'FIVE_MINUTE' },
  },
  {
    name: 'rsi_macd',
    display_name: 'RSI + MACD',
    description: 'Combines RSI oversold/overbought with MACD crossover confirmation',
    enabled: true,
    params: { rsi_period: 14, rsi_oversold: 30, rsi_overbought: 70, macd_fast: 12, macd_slow: 26, macd_signal: 9, ticker: 'RELIANCE', interval: 'FIFTEEN_MINUTE' },
  },
  {
    name: 'bollinger_breakout',
    display_name: 'Bollinger Bands Breakout',
    description: 'Trades breakouts above upper band or below lower band',
    enabled: false,
    params: { period: 20, std_dev: 2.0, ticker: 'HDFCBANK', interval: 'FIVE_MINUTE' },
  },
  {
    name: 'vwap_intraday',
    display_name: 'VWAP Intraday',
    description: 'Uses VWAP as dynamic support/resistance for intraday entries',
    enabled: false,
    params: { deviation_pct: 0.5, ticker: 'INFY', interval: 'FIVE_MINUTE' },
  },
  {
    name: 'breakout',
    display_name: 'Support/Resistance Breakout',
    description: 'Detects breakout from consolidation zones using pivot points',
    enabled: false,
    params: { lookback: 20, volume_multiplier: 1.5, ticker: 'TCS', interval: 'FIFTEEN_MINUTE' },
  },
];

const sampleSignals = [
  { time: '09:25:14', strategy: 'RSI + MACD', ticker: 'RELIANCE', signal: 'BUY', strength: 'Strong' },
  { time: '10:15:32', strategy: 'MA Crossover', ticker: 'NIFTY', signal: 'SELL', strength: 'Moderate' },
  { time: '11:42:08', strategy: 'Bollinger Breakout', ticker: 'HDFCBANK', signal: 'BUY', strength: 'Weak' },
  { time: '13:08:55', strategy: 'VWAP Intraday', ticker: 'INFY', signal: 'BUY', strength: 'Strong' },
];

const StrategyCard = ({ strategy, onToggle, onConfigSave, onRun }) => {
  const [expanded, setExpanded] = useState(false);
  const [params, setParams] = useState(strategy.params || {});
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  const handleParamChange = (key, value) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    await onConfigSave(strategy.name, params);
    setSaving(false);
  };

  const handleRun = async () => {
    setRunning(true);
    await onRun(strategy.name);
    setRunning(false);
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <h3 className="text-white font-semibold text-sm">{strategy.display_name}</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full ${strategy.enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-600/20 text-gray-500'}`}>
              {strategy.enabled ? 'Active' : 'Inactive'}
            </span>
          </div>
          <p className="text-gray-500 text-xs">{strategy.description}</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRun}
            disabled={running}
            className="btn-secondary text-xs"
          >
            {running ? 'Running...' : 'Run Now'}
          </button>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={strategy.enabled}
              onChange={() => onToggle(strategy.name)}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>

      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-gray-400 hover:text-highlight mt-3 transition-colors"
      >
        {expanded ? '\u25BC Hide Parameters' : '\u25B6 Show Parameters'}
      </button>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-darkAccent/30 animate-fade-in">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(params).map(([key, value]) => (
              <div key={key}>
                <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                  {key.replace(/_/g, ' ')}
                </label>
                <input
                  type={typeof value === 'number' ? 'number' : 'text'}
                  value={value}
                  onChange={(e) =>
                    handleParamChange(
                      key,
                      typeof value === 'number' ? parseFloat(e.target.value) || 0 : e.target.value
                    )
                  }
                  step={typeof value === 'number' && value < 1 ? '0.1' : '1'}
                  className="input-field text-xs"
                />
              </div>
            ))}
          </div>
          <div className="mt-4 flex justify-end">
            <button onClick={handleSave} disabled={saving} className="btn-primary text-xs">
              {saving ? 'Saving...' : 'Save Parameters'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const StrategiesPage = () => {
  const [strategies, setStrategies] = useState(defaultStrategies);
  const [signals] = useState(sampleSignals);

  const fetchStrategies = useCallback(async () => {
    try {
      const res = await getStrategies();
      if (Array.isArray(res.data) && res.data.length > 0) {
        setStrategies(res.data);
      }
    } catch {
      // Use defaults
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const handleToggle = async (name) => {
    try {
      await toggleStrategy(name);
      setStrategies((prev) =>
        prev.map((s) => (s.name === name ? { ...s, enabled: !s.enabled } : s))
      );
    } catch {
      // Optimistic toggle even on error for demo
      setStrategies((prev) =>
        prev.map((s) => (s.name === name ? { ...s, enabled: !s.enabled } : s))
      );
    }
  };

  const handleConfigSave = async (name, params) => {
    try {
      await updateStrategyConfig(name, params);
      setStrategies((prev) =>
        prev.map((s) => (s.name === name ? { ...s, params } : s))
      );
    } catch {
      // Still update locally
      setStrategies((prev) =>
        prev.map((s) => (s.name === name ? { ...s, params } : s))
      );
    }
  };

  const handleRun = async (name) => {
    try {
      await runStrategy({ strategy_name: name });
    } catch {
      // Ignore for demo
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Strategies</h1>
        <p className="text-gray-500 text-sm">Configure and manage trading strategies</p>
      </div>

      {/* Strategy Cards */}
      <div className="space-y-4">
        {strategies.map((strategy) => (
          <StrategyCard
            key={strategy.name}
            strategy={strategy}
            onToggle={handleToggle}
            onConfigSave={handleConfigSave}
            onRun={handleRun}
          />
        ))}
      </div>

      {/* Signal Log */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-4">Recent Signals</h3>
        <div className="overflow-x-auto">
          <table className="trade-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Strategy</th>
                <th>Ticker</th>
                <th>Signal</th>
                <th>Strength</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s, i) => (
                <tr key={i}>
                  <td className="mono text-gray-400">{s.time}</td>
                  <td className="text-gray-300">{s.strategy}</td>
                  <td className="mono text-white font-medium">{s.ticker}</td>
                  <td>
                    <span className={`font-semibold ${s.signal === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                      {s.signal}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        s.strength === 'Strong'
                          ? 'bg-green-500/20 text-green-400'
                          : s.strength === 'Moderate'
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}
                    >
                      {s.strength}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default StrategiesPage;

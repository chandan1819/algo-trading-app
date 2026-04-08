import React, { useState, useEffect, useCallback } from 'react';
import PnLCard from '../components/PnLCard';
import TradeTable from '../components/TradeTable';
import useWebSocket from '../hooks/useWebSocket';
import {
  getDashboardPnL,
  getDashboardStats,
  getTradeLog,
  getRiskStatus,
} from '../services/api';

// Sample candlestick data for the chart placeholder
const generateSampleCandles = () => {
  const candles = [];
  let price = 19500;
  for (let i = 0; i < 40; i++) {
    const open = price;
    const close = open + (Math.random() - 0.48) * 120;
    const high = Math.max(open, close) + Math.random() * 60;
    const low = Math.min(open, close) - Math.random() * 60;
    candles.push({ open, close, high, low });
    price = close;
  }
  return candles;
};

const CandlestickChart = ({ candles }) => {
  const allPrices = candles.flatMap((c) => [c.high, c.low]);
  const maxPrice = Math.max(...allPrices);
  const minPrice = Math.min(...allPrices);
  const range = maxPrice - minPrice || 1;
  const chartHeight = 200;

  const scale = (val) => ((val - minPrice) / range) * chartHeight;

  return (
    <div className="candle-chart" style={{ height: chartHeight }}>
      {candles.map((c, i) => {
        const isGreen = c.close >= c.open;
        const bodyTop = scale(Math.max(c.open, c.close));
        const bodyBottom = scale(Math.min(c.open, c.close));
        const bodyHeight = Math.max(bodyTop - bodyBottom, 2);
        const wickTop = scale(c.high);
        const wickBottom = scale(c.low);
        const upperWick = wickTop - bodyTop;
        const lowerWick = bodyBottom - wickBottom;

        return (
          <div
            key={i}
            className={`candle ${isGreen ? 'green' : 'red'}`}
            style={{ height: chartHeight }}
          >
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', height: '100%' }}>
              <div style={{ height: chartHeight - wickTop }} />
              <div className="candle-wick" style={{ height: upperWick }} />
              <div className="candle-body" style={{ height: bodyHeight }} />
              <div className="candle-wick" style={{ height: lowerWick }} />
              <div style={{ height: wickBottom }} />
            </div>
          </div>
        );
      })}
    </div>
  );
};

const RiskMeter = ({ label, value, max, unit = '%' }) => {
  const pct = Math.min((value / max) * 100, 100);
  const color =
    pct < 50 ? '#48bb78' : pct < 75 ? '#ecc94b' : '#e94560';

  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="mono" style={{ color }}>
          {value}{unit} / {max}{unit}
        </span>
      </div>
      <div className="risk-meter">
        <div
          className="risk-meter-fill"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
};

const tradeColumns = [
  { key: 'time', label: 'Time' },
  { key: 'ticker', label: 'Ticker' },
  {
    key: 'side',
    label: 'Side',
    render: (val) => (
      <span className={val === 'BUY' ? 'text-green-400 font-semibold' : 'text-red-400 font-semibold'}>
        {val}
      </span>
    ),
  },
  { key: 'qty', label: 'Qty', className: 'mono' },
  { key: 'price', label: 'Price', className: 'mono' },
  {
    key: 'pnl',
    label: 'PnL',
    className: 'mono',
    render: (val) => (
      <span className={val >= 0 ? 'text-green-400' : 'text-red-400'}>
        {val >= 0 ? '+' : ''}{val?.toFixed(2)}
      </span>
    ),
  },
];

const sampleTrades = [
  { id: 1, time: '09:20:15', ticker: 'NIFTY24DEC19500CE', side: 'BUY', qty: 50, price: 245.50, pnl: 1250.00 },
  { id: 2, time: '09:35:42', ticker: 'BANKNIFTY24DEC44000PE', side: 'SELL', qty: 25, price: 320.75, pnl: -450.00 },
  { id: 3, time: '10:15:08', ticker: 'RELIANCE', side: 'BUY', qty: 100, price: 2456.80, pnl: 3200.00 },
  { id: 4, time: '11:02:33', ticker: 'NIFTY24DEC19600PE', side: 'SELL', qty: 50, price: 180.25, pnl: 875.50 },
  { id: 5, time: '11:45:19', ticker: 'HDFCBANK', side: 'BUY', qty: 200, price: 1678.50, pnl: -280.00 },
  { id: 6, time: '13:10:55', ticker: 'BANKNIFTY24DEC44200CE', side: 'BUY', qty: 25, price: 275.30, pnl: 1560.00 },
];

const sampleTickers = [
  { symbol: 'NIFTY 50', ltp: 19567.85, change: 0.42 },
  { symbol: 'BANKNIFTY', ltp: 44123.40, change: -0.18 },
  { symbol: 'SENSEX', ltp: 65432.10, change: 0.35 },
  { symbol: 'RELIANCE', ltp: 2456.80, change: 1.22 },
  { symbol: 'HDFCBANK', ltp: 1678.50, change: -0.55 },
  { symbol: 'INFY', ltp: 1487.65, change: 0.78 },
];

const DashboardPage = () => {
  const [pnl, setPnl] = useState(null);
  const [stats, setStats] = useState(null);
  const [trades, setTrades] = useState(sampleTrades);
  const [risk, setRisk] = useState(null);
  const [tickers, setTickers] = useState(sampleTickers);
  const [candles] = useState(generateSampleCandles);
  const { lastMessage, isConnected } = useWebSocket();

  const fetchData = useCallback(async () => {
    try {
      const [pnlRes, statsRes, tradeRes, riskRes] = await Promise.allSettled([
        getDashboardPnL(),
        getDashboardStats(),
        getTradeLog(),
        getRiskStatus(),
      ]);
      if (pnlRes.status === 'fulfilled') setPnl(pnlRes.value.data);
      if (statsRes.status === 'fulfilled') setStats(statsRes.value.data);
      if (tradeRes.status === 'fulfilled' && Array.isArray(tradeRes.value.data)) {
        setTrades(tradeRes.value.data);
      }
      if (riskRes.status === 'fulfilled') setRisk(riskRes.value.data);
    } catch {
      // Use sample data on error
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Update tickers from WebSocket
  useEffect(() => {
    if (lastMessage?.type === 'ticker' && lastMessage.data) {
      setTickers((prev) =>
        prev.map((t) =>
          t.symbol === lastMessage.data.symbol
            ? { ...t, ltp: lastMessage.data.ltp, change: lastMessage.data.change }
            : t
        )
      );
    }
  }, [lastMessage]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-500 text-sm">Real-time trading overview</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className={`live-dot ${!isConnected ? 'opacity-30' : ''}`}></span>
          <span className={isConnected ? 'text-green-400' : 'text-gray-500'}>
            {isConnected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* PnL Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <PnLCard
          title="Today's PnL"
          value={pnl?.today ?? 12580.50}
          change={pnl?.todayPct ?? 2.34}
          prefix={'\u20B9'}
          subtitle="Realized + Unrealized"
        />
        <PnLCard
          title="Total Trades"
          value={stats?.totalTrades ?? 24}
          change={null}
          subtitle="Today's executed orders"
        />
        <PnLCard
          title="Win Rate"
          value={stats?.winRate ?? 68.5}
          change={stats?.winRateChange ?? 3.2}
          suffix="%"
          subtitle="Last 30 days"
        />
        <PnLCard
          title="Max Drawdown"
          value={stats?.maxDrawdown ?? -4250.00}
          change={stats?.drawdownPct ?? -1.85}
          prefix={'\u20B9'}
          subtitle="Intraday peak-to-trough"
        />
      </div>

      {/* Chart + Live Tickers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Candlestick Chart */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">NIFTY 50 - Intraday</h3>
            <span className="text-xs text-gray-500 mono">5min candles</span>
          </div>
          <CandlestickChart candles={candles} />
          <div className="flex justify-between text-xs text-gray-600 mt-2">
            <span>09:15</span>
            <span>11:00</span>
            <span>13:00</span>
            <span>15:00</span>
            <span>15:30</span>
          </div>
        </div>

        {/* Live Tickers */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">Live Prices</h3>
          <div className="space-y-3">
            {tickers.map((t) => (
              <div
                key={t.symbol}
                className="flex items-center justify-between py-2 border-b border-darkAccent/20 last:border-0"
              >
                <span className="text-sm text-gray-300 font-medium">{t.symbol}</span>
                <div className="text-right">
                  <div className="text-sm mono text-white">
                    {t.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <div className={`text-xs mono ${t.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {t.change >= 0 ? '+' : ''}{t.change.toFixed(2)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Trade Log + Risk Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Trade Log */}
        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-white mb-3">Recent Trades</h3>
          <TradeTable columns={tradeColumns} data={trades} pageSize={6} />
        </div>

        {/* Risk Status */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">Risk Status</h3>
          <RiskMeter
            label="Daily Loss Limit"
            value={risk?.dailyLossUsed ?? 35}
            max={100}
          />
          <RiskMeter
            label="Trade Count"
            value={risk?.tradeCount ?? 24}
            max={risk?.maxTrades ?? 50}
            unit=""
          />
          <RiskMeter
            label="Drawdown"
            value={risk?.drawdownPct ?? 1.85}
            max={risk?.maxDrawdownPct ?? 5}
          />

          <div className="mt-4 pt-4 border-t border-darkAccent/30">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-gray-400">Capital Deployed</span>
              <span className="mono text-white">{'\u20B9'}2,45,000</span>
            </div>
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-gray-400">Available Margin</span>
              <span className="mono text-green-400">{'\u20B9'}7,55,000</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Margin Utilization</span>
              <span className="mono text-yellow-400">24.5%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;

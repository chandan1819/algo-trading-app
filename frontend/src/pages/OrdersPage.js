import React, { useState, useEffect, useCallback } from 'react';
import TradeTable from '../components/TradeTable';
import { placeOrder, getOrderBook, getPositions, getHoldings } from '../services/api';

const sampleOrders = [
  { id: 'ORD001', time: '09:20:15', ticker: 'RELIANCE', side: 'BUY', type: 'LIMIT', qty: 100, price: 2456.80, status: 'EXECUTED' },
  { id: 'ORD002', time: '09:35:42', ticker: 'HDFCBANK', side: 'SELL', type: 'MARKET', qty: 200, price: 1678.50, status: 'EXECUTED' },
  { id: 'ORD003', time: '10:15:08', ticker: 'INFY', side: 'BUY', type: 'SL', qty: 150, price: 1487.65, status: 'PENDING' },
  { id: 'ORD004', time: '11:02:33', ticker: 'TCS', side: 'BUY', type: 'LIMIT', qty: 50, price: 3890.00, status: 'CANCELLED' },
];

const samplePositions = [
  { ticker: 'RELIANCE', side: 'BUY', qty: 100, avg_price: 2456.80, ltp: 2478.50, pnl: 2170.00, pnl_pct: 0.88 },
  { ticker: 'HDFCBANK', side: 'SELL', qty: 200, avg_price: 1678.50, ltp: 1665.20, pnl: 2660.00, pnl_pct: 0.79 },
  { ticker: 'INFY', side: 'BUY', qty: 150, avg_price: 1487.65, ltp: 1492.30, pnl: 697.50, pnl_pct: 0.31 },
];

const sampleHoldings = [
  { ticker: 'RELIANCE', qty: 50, avg_price: 2380.00, ltp: 2478.50, pnl: 4925.00, pnl_pct: 4.14 },
  { ticker: 'TCS', qty: 25, avg_price: 3750.00, ltp: 3890.00, pnl: 3500.00, pnl_pct: 3.73 },
  { ticker: 'WIPRO', qty: 200, avg_price: 410.00, ltp: 425.60, pnl: 3120.00, pnl_pct: 3.80 },
];

const orderColumns = [
  { key: 'time', label: 'Time' },
  { key: 'id', label: 'Order ID', className: 'mono' },
  { key: 'ticker', label: 'Ticker' },
  { key: 'side', label: 'Side', render: (val) => <span className={val === 'BUY' ? 'text-green-400 font-semibold' : 'text-red-400 font-semibold'}>{val}</span> },
  { key: 'type', label: 'Type' },
  { key: 'qty', label: 'Qty', className: 'mono' },
  { key: 'price', label: 'Price', className: 'mono', render: (val) => val?.toFixed(2) },
  { key: 'status', label: 'Status', render: (val) => {
    const color = val === 'EXECUTED' ? 'text-green-400' : val === 'PENDING' ? 'text-yellow-400' : 'text-red-400';
    return <span className={`${color} font-medium`}>{val}</span>;
  }},
];

const positionColumns = [
  { key: 'ticker', label: 'Ticker' },
  { key: 'side', label: 'Side', render: (val) => <span className={val === 'BUY' ? 'text-green-400' : 'text-red-400'}>{val}</span> },
  { key: 'qty', label: 'Qty', className: 'mono' },
  { key: 'avg_price', label: 'Avg Price', className: 'mono', render: (val) => val?.toFixed(2) },
  { key: 'ltp', label: 'LTP', className: 'mono', render: (val) => val?.toFixed(2) },
  { key: 'pnl', label: 'PnL', className: 'mono', render: (val) => <span className={val >= 0 ? 'text-green-400' : 'text-red-400'}>{val >= 0 ? '+' : ''}{val?.toFixed(2)}</span> },
  { key: 'pnl_pct', label: 'PnL %', className: 'mono', render: (val) => <span className={val >= 0 ? 'text-green-400' : 'text-red-400'}>{val >= 0 ? '+' : ''}{val?.toFixed(2)}%</span> },
];

const holdingColumns = [
  { key: 'ticker', label: 'Ticker' },
  { key: 'qty', label: 'Qty', className: 'mono' },
  { key: 'avg_price', label: 'Avg Price', className: 'mono', render: (val) => val?.toFixed(2) },
  { key: 'ltp', label: 'LTP', className: 'mono', render: (val) => val?.toFixed(2) },
  { key: 'pnl', label: 'PnL', className: 'mono', render: (val) => <span className={val >= 0 ? 'text-green-400' : 'text-red-400'}>{val >= 0 ? '+' : ''}{val?.toFixed(2)}</span> },
  { key: 'pnl_pct', label: 'PnL %', className: 'mono', render: (val) => <span className={val >= 0 ? 'text-green-400' : 'text-red-400'}>{val >= 0 ? '+' : ''}{val?.toFixed(2)}%</span> },
];

const OrdersPage = () => {
  const [activeTab, setActiveTab] = useState('orders');
  const [orders, setOrders] = useState(sampleOrders);
  const [positions, setPositions] = useState(samplePositions);
  const [holdings, setHoldings] = useState(sampleHoldings);
  const [submitting, setSubmitting] = useState(false);
  const [orderMsg, setOrderMsg] = useState(null);
  const [form, setForm] = useState({
    ticker: '',
    transaction_type: 'BUY',
    order_type: 'MARKET',
    quantity: '',
    price: '',
    stoploss: '',
  });

  const fetchData = useCallback(async () => {
    const [ordRes, posRes, holdRes] = await Promise.allSettled([
      getOrderBook(),
      getPositions(),
      getHoldings(),
    ]);
    if (ordRes.status === 'fulfilled' && Array.isArray(ordRes.value.data)) setOrders(ordRes.value.data);
    if (posRes.status === 'fulfilled' && Array.isArray(posRes.value.data)) setPositions(posRes.value.data);
    if (holdRes.status === 'fulfilled' && Array.isArray(holdRes.value.data)) setHoldings(holdRes.value.data);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setOrderMsg(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setOrderMsg(null);
    try {
      const payload = {
        ...form,
        quantity: parseInt(form.quantity, 10),
        price: form.price ? parseFloat(form.price) : 0,
        stoploss: form.stoploss ? parseFloat(form.stoploss) : 0,
      };
      await placeOrder(payload);
      setOrderMsg({ type: 'success', text: 'Order placed successfully!' });
      setForm({ ticker: '', transaction_type: 'BUY', order_type: 'MARKET', quantity: '', price: '', stoploss: '' });
      fetchData();
    } catch (err) {
      setOrderMsg({ type: 'error', text: err.message || 'Failed to place order' });
    } finally {
      setSubmitting(false);
    }
  };

  const tabs = [
    { key: 'orders', label: 'Order Book' },
    { key: 'positions', label: 'Positions' },
    { key: 'holdings', label: 'Holdings' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Orders</h1>
        <p className="text-gray-500 text-sm">Place and manage orders</p>
      </div>

      {/* Place Order Form */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-4">Place Order</h3>
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Ticker</label>
              <input
                type="text"
                name="ticker"
                value={form.ticker}
                onChange={handleChange}
                className="input-field text-sm"
                placeholder="e.g. RELIANCE"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Side</label>
              <select name="transaction_type" value={form.transaction_type} onChange={handleChange} className="input-field text-sm">
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Type</label>
              <select name="order_type" value={form.order_type} onChange={handleChange} className="input-field text-sm">
                <option value="MARKET">Market</option>
                <option value="LIMIT">Limit</option>
                <option value="SL">Stop-Loss</option>
                <option value="SL-M">SL-Market</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Quantity</label>
              <input type="number" name="quantity" value={form.quantity} onChange={handleChange} className="input-field text-sm" placeholder="Qty" min="1" required />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Price</label>
              <input type="number" name="price" value={form.price} onChange={handleChange} className="input-field text-sm" placeholder="0.00" step="0.05" disabled={form.order_type === 'MARKET'} />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Stop-Loss</label>
              <input type="number" name="stoploss" value={form.stoploss} onChange={handleChange} className="input-field text-sm" placeholder="0.00" step="0.05" />
            </div>
          </div>

          <div className="flex items-center gap-4 mt-4">
            <button type="submit" disabled={submitting} className={`btn-primary text-sm ${form.transaction_type === 'SELL' ? 'bg-gradient-to-r from-red-600 to-red-700' : ''}`}>
              {submitting ? 'Placing...' : `${form.transaction_type} ${form.ticker || 'Order'}`}
            </button>
            {orderMsg && (
              <span className={`text-sm ${orderMsg.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                {orderMsg.text}
              </span>
            )}
          </div>
        </form>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-darkAccent/30 pb-0">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === tab.key
                ? 'bg-darkCard text-highlight border border-darkAccent/30 border-b-transparent -mb-px'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'orders' && <TradeTable columns={orderColumns} data={orders} pageSize={10} />}
      {activeTab === 'positions' && <TradeTable columns={positionColumns} data={positions} pageSize={10} />}
      {activeTab === 'holdings' && <TradeTable columns={holdingColumns} data={holdings} pageSize={10} />}
    </div>
  );
};

export default OrdersPage;

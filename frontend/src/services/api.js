import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status } = error.response;
      if (status === 401) {
        // Clear auth state and redirect to login
        localStorage.removeItem('isAuthenticated');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
      const message =
        error.response.data?.message ||
        error.response.data?.detail ||
        `Request failed with status ${status}`;
      return Promise.reject(new Error(message));
    }
    if (error.request) {
      return Promise.reject(new Error('Network error - server unreachable'));
    }
    return Promise.reject(error);
  }
);

// Auth
export const authLogin = (credentials) =>
  api.post('/api/auth/login', credentials);

export const authLogout = () =>
  api.post('/api/auth/logout');

export const authStatus = () =>
  api.get('/api/auth/status');

// Market Data
export const getMarketLTP = (ticker) =>
  api.get(`/api/market/ltp/${ticker}`);

export const getMarketHistorical = (ticker, params) =>
  api.get(`/api/market/historical/${ticker}`, { params });

// Orders
export const placeOrder = (orderData) =>
  api.post('/api/orders/place', orderData);

export const getOrderBook = () =>
  api.get('/api/orders/book');

export const getPositions = () =>
  api.get('/api/orders/positions');

export const getHoldings = () =>
  api.get('/api/orders/holdings');

// Strategies
export const getStrategies = () =>
  api.get('/api/strategies');

export const toggleStrategy = (name) =>
  api.put(`/api/strategies/${name}/toggle`);

export const updateStrategyConfig = (name, config) =>
  api.put(`/api/strategies/${name}/config`, config);

export const runStrategy = (data) =>
  api.post('/api/strategies/run', data);

// Dashboard
export const getDashboardPnL = () =>
  api.get('/api/dashboard/pnl');

export const getDashboardStats = () =>
  api.get('/api/dashboard/stats');

export const getTradeLog = () =>
  api.get('/api/dashboard/trade-log');

export const getRiskStatus = () =>
  api.get('/api/dashboard/risk-status');

// Backtest
export const runBacktest = (params) =>
  api.post('/api/backtest/run', params);

export const getBacktestResults = () =>
  api.get('/api/backtest/results');

export default api;

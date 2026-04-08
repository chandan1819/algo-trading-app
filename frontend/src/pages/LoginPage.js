import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authLogin } from '../services/api';

const LoginPage = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    api_key: '',
    client_id: '',
    password: '',
    totp: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await authLogin(form);
      localStorage.setItem('isAuthenticated', 'true');
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-darkBg flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-highlight text-5xl mb-3">{'\u25C8'}</div>
          <h1 className="text-3xl font-bold text-white tracking-tight">AlgoTrader</h1>
          <p className="text-gray-500 text-sm mt-1">NSE Algorithmic Trading Platform</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="card space-y-5">
          <h2 className="text-lg font-semibold text-white mb-2">Broker Login</h2>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              API Key
            </label>
            <input
              type="text"
              name="api_key"
              value={form.api_key}
              onChange={handleChange}
              className="input-field"
              placeholder="Enter your broker API key"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              Client ID
            </label>
            <input
              type="text"
              name="client_id"
              value={form.client_id}
              onChange={handleChange}
              className="input-field"
              placeholder="Enter your client ID"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              Password
            </label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              className="input-field"
              placeholder="Enter your password"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              TOTP
            </label>
            <input
              type="text"
              name="totp"
              value={form.totp}
              onChange={handleChange}
              className="input-field mono"
              placeholder="Enter 6-digit TOTP"
              maxLength={6}
              pattern="[0-9]{6}"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="animate-spin inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full"></span>
                Connecting...
              </>
            ) : (
              'Login & Connect'
            )}
          </button>
        </form>

        <p className="text-center text-gray-600 text-xs mt-6">
          Secure connection to NSE via broker API
        </p>
      </div>
    </div>
  );
};

export default LoginPage;

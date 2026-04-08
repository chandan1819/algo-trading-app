import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { authLogout } from '../services/api';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '\u2302' },
  { path: '/strategies', label: 'Strategies', icon: '\u2699' },
  { path: '/orders', label: 'Orders', icon: '\u21C4' },
  { path: '/backtest', label: 'Backtest', icon: '\u23F1' },
];

const Navbar = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await authLogout();
    } catch {
      // Logout regardless
    }
    localStorage.removeItem('isAuthenticated');
    navigate('/login');
  };

  return (
    <nav
      className={`fixed top-0 left-0 h-full bg-darkCard border-r border-darkAccent/30 flex flex-col z-50 transition-all duration-300 ${
        collapsed ? 'w-[72px]' : 'w-[240px]'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-darkAccent/30">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <span className="text-highlight text-xl font-bold">\u25C8</span>
            <span className="text-white font-bold text-lg tracking-tight">
              AlgoTrader
            </span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-gray-400 hover:text-white p-1 rounded transition-colors"
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? '\u25B6' : '\u25C0'}
        </button>
      </div>

      {/* Nav Links */}
      <div className="flex-1 py-4">
        {navItems.map(({ path, label, icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 mx-2 rounded-lg transition-all duration-200 text-sm font-medium ${
                isActive
                  ? 'bg-highlight/20 text-highlight border-l-2 border-highlight'
                  : 'text-gray-400 hover:text-white hover:bg-darkAccent/30'
              }`
            }
          >
            <span className="text-lg w-6 text-center">{icon}</span>
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-darkAccent/30">
        <button
          onClick={handleLogout}
          className={`flex items-center gap-3 w-full px-3 py-2 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-400/10 transition-all duration-200 text-sm font-medium ${
            collapsed ? 'justify-center' : ''
          }`}
        >
          <span className="text-lg">{'\u23FB'}</span>
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </nav>
  );
};

export default Navbar;

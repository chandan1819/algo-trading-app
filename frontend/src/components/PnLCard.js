import React from 'react';

const PnLCard = ({ title, value, change, subtitle, prefix = '', suffix = '' }) => {
  const isPositive = typeof change === 'number' ? change >= 0 : null;
  const changeColor = isPositive === null ? 'text-gray-400' : isPositive ? 'text-green-400' : 'text-red-400';
  const changeIcon = isPositive === null ? '' : isPositive ? '\u25B2' : '\u25BC';

  return (
    <div className="card animate-fade-in">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          {title}
        </span>
        {typeof change === 'number' && (
          <span className={`text-xs font-medium ${changeColor}`}>
            {changeIcon} {Math.abs(change).toFixed(2)}%
          </span>
        )}
      </div>
      <div className={`text-2xl font-bold mono ${changeColor}`}>
        {prefix}{typeof value === 'number' ? value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : value}{suffix}
      </div>
      {subtitle && (
        <div className="text-xs text-gray-500 mt-1">{subtitle}</div>
      )}
    </div>
  );
};

export default PnLCard;

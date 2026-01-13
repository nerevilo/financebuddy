'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from 'recharts';

interface TrendDataPoint {
  day: number;
  date: string;
  daily: number;
  cumulative: number;
  budget_pace: number;
}

interface LastMonthDataPoint {
  day: number;
  cumulative: number;
}

interface SpendingTrendProps {
  trend: {
    this_month: TrendDataPoint[];
    last_month: LastMonthDataPoint[];
    budget: number;
    current_total: number;
    projected_total: number;
    days_elapsed: number;
    days_in_month: number;
    on_track: boolean;
    month_name: string;
    last_month_name: string;
  };
}

export function SpendingTrendChart({ trend }: SpendingTrendProps) {
  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);

  // Merge this month and last month data for the chart
  const chartData = trend.this_month.map((point) => {
    const lastMonthPoint = trend.last_month.find((lm) => lm.day === point.day);
    return {
      ...point,
      last_month: lastMonthPoint?.cumulative || null,
    };
  });

  // Calculate pace status
  const paceStatus = trend.on_track ? 'on-track' : 'over-budget';
  const paceDiff = trend.current_total - (trend.budget / trend.days_in_month * trend.days_elapsed);
  const pacePercent = trend.budget > 0
    ? ((trend.current_total / (trend.budget / trend.days_in_month * trend.days_elapsed)) - 1) * 100
    : 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Spending Trend</h3>
          <p className="text-sm text-gray-500">
            {trend.month_name} spending vs budget pace
          </p>
        </div>

        {/* Status Badge */}
        <div className={`px-3 py-1.5 rounded-full text-sm font-medium ${
          trend.on_track
            ? 'bg-green-100 text-green-700'
            : 'bg-red-100 text-red-700'
        }`}>
          {trend.on_track ? 'On Track' : 'Over Pace'}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Spent</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(trend.current_total)}
          </p>
          <p className="text-xs text-gray-500">
            Day {trend.days_elapsed} of {trend.days_in_month}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Budget</p>
          <p className="text-2xl font-bold text-gray-600">
            {formatCurrency(trend.budget)}
          </p>
          <p className="text-xs text-gray-500">
            Based on {trend.last_month_name}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Projected</p>
          <p className={`text-2xl font-bold ${
            trend.projected_total <= trend.budget ? 'text-green-600' : 'text-red-600'
          }`}>
            {formatCurrency(trend.projected_total)}
          </p>
          <p className="text-xs text-gray-500">
            {trend.projected_total <= trend.budget
              ? `${formatCurrency(trend.budget - trend.projected_total)} under`
              : `${formatCurrency(trend.projected_total - trend.budget)} over`}
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 12, fill: '#6b7280' }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
              tickFormatter={(day) => (day % 5 === 0 || day === 1 ? `${day}` : '')}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#6b7280' }}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
              tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
              width={50}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
              formatter={(value: number, name: string) => [
                formatCurrency(value),
                name === 'cumulative' ? 'Actual' : name === 'budget_pace' ? 'Budget Pace' : 'Last Month',
              ]}
              labelFormatter={(day) => `Day ${day}`}
            />
            <Legend
              verticalAlign="top"
              height={36}
              formatter={(value) => {
                const labels: Record<string, string> = {
                  cumulative: 'Actual Spending',
                  budget_pace: 'Budget Pace',
                  last_month: trend.last_month_name,
                };
                return <span className="text-sm text-gray-600">{labels[value] || value}</span>;
              }}
            />

            {/* Budget pace line (dashed) */}
            <Line
              type="monotone"
              dataKey="budget_pace"
              stroke="#9ca3af"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              activeDot={false}
            />

            {/* Last month comparison (light) */}
            {trend.last_month.length > 0 && (
              <Line
                type="monotone"
                dataKey="last_month"
                stroke="#ddd6fe"
                strokeWidth={2}
                dot={false}
                activeDot={false}
              />
            )}

            {/* This month actual (primary) */}
            <Line
              type="monotone"
              dataKey="cumulative"
              stroke={trend.on_track ? '#10b981' : '#ef4444'}
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 6, strokeWidth: 2 }}
            />

            {/* Budget reference line */}
            <ReferenceLine
              y={trend.budget}
              stroke="#6b7280"
              strokeDasharray="3 3"
              label={{
                value: 'Budget',
                position: 'right',
                fill: '#6b7280',
                fontSize: 12,
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Pace Indicator */}
      {Math.abs(pacePercent) > 5 && (
        <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
          trend.on_track ? 'bg-green-50' : 'bg-red-50'
        }`}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d={trend.on_track
                ? "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                : "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              }
            />
          </svg>
          <span className={`text-sm font-medium ${
            trend.on_track ? 'text-green-700' : 'text-red-700'
          }`}>
            {trend.on_track
              ? `${formatCurrency(Math.abs(paceDiff))} under budget pace`
              : `${formatCurrency(Math.abs(paceDiff))} over budget pace`
            }
          </span>
        </div>
      )}
    </div>
  );
}

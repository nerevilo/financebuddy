'use client';

import { formatCurrency } from '@/lib/utils';

interface Account {
  id: string;
  name: string;
  type: string;
  subtype: string;
  current_balance: number;
  institution_name: string;
}

interface BalanceSummary {
  total_balance: number;
  depository_balance: number;
  credit_balance: number;
  account_count: number;
}

interface AccountsSummaryProps {
  accounts: Account[];
  summary: BalanceSummary;
}

export function AccountsSummary({ accounts, summary }: AccountsSummaryProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Accounts</h3>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-green-50 rounded-lg p-4">
          <p className="text-sm text-green-600">Cash</p>
          <p className="text-xl font-bold text-green-700">
            {formatCurrency(summary.depository_balance)}
          </p>
        </div>
        <div className="bg-red-50 rounded-lg p-4">
          <p className="text-sm text-red-600">Credit Used</p>
          <p className="text-xl font-bold text-red-700">
            {formatCurrency(summary.credit_balance)}
          </p>
        </div>
      </div>

      <div className="border-t border-gray-100 pt-4 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-600">Net Worth</span>
          <span
            className={`text-xl font-bold ${
              summary.total_balance >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {formatCurrency(summary.total_balance)}
          </span>
        </div>
      </div>

      {/* Account List */}
      <div className="space-y-3">
        {accounts.map((account) => (
          <div
            key={account.id}
            className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0"
          >
            <div>
              <p className="text-sm font-medium text-gray-900">{account.name}</p>
              <p className="text-xs text-gray-500">
                {account.institution_name} · {account.subtype || account.type}
              </p>
            </div>
            <span
              className={`text-sm font-semibold ${
                account.type === 'credit' ? 'text-red-600' : 'text-gray-900'
              }`}
            >
              {account.type === 'credit' ? '-' : ''}
              {formatCurrency(Math.abs(account.current_balance))}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

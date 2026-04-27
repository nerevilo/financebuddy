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
    <div className="bg-white rounded-xl shadow-sm border border-neutral-200 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 mb-4">Accounts</h3>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-success-50 rounded-lg p-4">
          <p className="text-sm text-success-500">Cash</p>
          <p className="text-xl font-bold text-success-600">
            {formatCurrency(summary.depository_balance)}
          </p>
        </div>
        <div className="bg-danger-50 rounded-lg p-4">
          <p className="text-sm text-danger-500">Credit Used</p>
          <p className="text-xl font-bold text-danger-600">
            {formatCurrency(summary.credit_balance)}
          </p>
        </div>
      </div>

      <div className="border-t border-neutral-100 pt-4 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-neutral-600">Net Worth</span>
          <span
            className={`text-xl font-bold ${
              summary.total_balance >= 0 ? 'text-success-500' : 'text-danger-500'
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
            className="flex items-center justify-between py-2 border-b border-neutral-100 last:border-0"
          >
            <div>
              <p className="text-sm font-medium text-neutral-900">{account.name}</p>
              <p className="text-xs text-neutral-500">
                {account.institution_name} · {account.subtype || account.type}
              </p>
            </div>
            <span
              className={`text-sm font-semibold ${
                account.type === 'credit' ? 'text-danger-500' : 'text-neutral-900'
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

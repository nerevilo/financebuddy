'use client';

import { useState } from 'react';
import { useTransactionsList, useCategories } from '@/lib/hooks';
import { updateTransactionCategory, TransactionListParams, Transaction } from '@/lib/api';
import { mutate } from 'swr';

type SortField = 'date' | 'amount' | 'merchant' | 'category';
type SortOrder = 'asc' | 'desc';

export function TransactionsTable() {
  const [sortBy, setSortBy] = useState<SortField>('date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [page, setPage] = useState(0);
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingCategory, setEditingCategory] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);

  const limit = 50;

  const params: TransactionListParams = {
    sort_by: sortBy,
    sort_order: sortOrder,
    limit,
    offset: page * limit,
    ...(categoryFilter && { category: categoryFilter }),
  };

  const { data, isLoading, refresh } = useTransactionsList(params);
  const { categories } = useCategories();

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Math.abs(amount));

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setPage(0);
  };

  const handleEditCategory = (transaction: Transaction) => {
    setEditingId(transaction.id);
    setEditingCategory(transaction.category || '');
  };

  const handleSaveCategory = async (transactionId: string) => {
    if (!editingCategory) {
      setEditingId(null);
      return;
    }

    setIsSaving(true);
    try {
      await updateTransactionCategory(transactionId, editingCategory);
      await refresh();
      // Also refresh dashboard data
      await mutate('dashboard');
    } catch (err) {
      console.error('Failed to update category:', err);
    } finally {
      setIsSaving(false);
      setEditingId(null);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingCategory('');
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortBy !== field) {
      return (
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return sortOrder === 'asc' ? (
      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  const totalPages = Math.ceil(data.total / limit);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Filters */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-600">
              {data.total} transaction{data.total !== 1 ? 's' : ''}
            </div>

            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setPage(0);
              }}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat.name} value={cat.name}>
                  {cat.name}
                </option>
              ))}
            </select>

            {categoryFilter && (
              <button
                onClick={() => setCategoryFilter('')}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Clear filter
              </button>
            )}
          </div>

          <div className="text-sm text-gray-500">
            Click a category to edit it
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left">
                <button
                  onClick={() => handleSort('date')}
                  className="flex items-center gap-1 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                >
                  Date <SortIcon field="date" />
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left">
                <button
                  onClick={() => handleSort('merchant')}
                  className="flex items-center gap-1 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                >
                  Merchant <SortIcon field="merchant" />
                </button>
              </th>
              <th className="px-6 py-3 text-left">
                <button
                  onClick={() => handleSort('category')}
                  className="flex items-center gap-1 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                >
                  Category <SortIcon field="category" />
                </button>
              </th>
              <th className="px-6 py-3 text-right">
                <button
                  onClick={() => handleSort('amount')}
                  className="flex items-center gap-1 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 ml-auto"
                >
                  Amount <SortIcon field="amount" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {isLoading && data.transactions.length === 0 ? (
              // Loading skeleton
              [...Array(10)].map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-48"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-32"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-20 ml-auto"></div></td>
                </tr>
              ))
            ) : data.transactions.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                  No transactions found
                </td>
              </tr>
            ) : (
              data.transactions.map((txn) => (
                <tr key={txn.id} className="hover:bg-gray-50 transition">
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {formatDate(txn.date)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900 max-w-xs truncate" title={txn.description}>
                      {txn.description}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">
                      {txn.merchant_name || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {editingId === txn.id ? (
                      <div className="flex items-center gap-2">
                        <select
                          value={editingCategory}
                          onChange={(e) => setEditingCategory(e.target.value)}
                          className="px-2 py-1 text-sm border border-blue-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          autoFocus
                        >
                          <option value="">Select...</option>
                          {categories.map((cat) => (
                            <option key={cat.name} value={cat.name}>
                              {cat.name}
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={() => handleSaveCategory(txn.id)}
                          disabled={isSaving}
                          className="p-1 text-green-600 hover:text-green-800 disabled:opacity-50"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="p-1 text-gray-400 hover:text-gray-600"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleEditCategory(txn)}
                        className="inline-flex items-center gap-1 px-2 py-1 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200 transition capitalize"
                      >
                        {txn.category || 'uncategorized'}
                        <svg className="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                      </button>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className={`text-sm font-semibold ${txn.amount < 0 ? 'text-gray-900' : 'text-green-600'}`}>
                      {txn.amount < 0 ? '-' : '+'}{formatCurrency(txn.amount)}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data.total > limit && (
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Showing {page * limit + 1} - {Math.min((page + 1) * limit, data.total)} of {data.total}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-gray-600">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={!data.has_more}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

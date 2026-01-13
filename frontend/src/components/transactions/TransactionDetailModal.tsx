'use client';

import { useState, useEffect } from 'react';
import { useCategories } from '@/lib/hooks';
import { updateTransactionCategory, Transaction } from '@/lib/api';
import { mutate } from 'swr';

interface TransactionDetailModalProps {
  transaction: {
    id: string;
    merchant: string | null;
    category: string | null;
    amount: number;
    description: string;
    date?: string;
    time?: string;
    emoji?: string;
  } | null;
  isOpen: boolean;
  onClose: () => void;
  onCategoryUpdated?: () => void;
}

export function TransactionDetailModal({
  transaction,
  isOpen,
  onClose,
  onCategoryUpdated,
}: TransactionDetailModalProps) {
  const { categories, isLoading: categoriesLoading } = useCategories();
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset selected category when transaction changes
  useEffect(() => {
    if (transaction) {
      setSelectedCategory(transaction.category || '');
      setError(null);
    }
  }, [transaction]);

  if (!isOpen || !transaction) return null;

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Math.abs(amount));

  const handleSave = async () => {
    if (!selectedCategory || selectedCategory === transaction.category) {
      onClose();
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      await updateTransactionCategory(transaction.id, selectedCategory);

      // Invalidate all relevant caches
      await Promise.all([
        mutate('dashboard'),
        mutate((key) => Array.isArray(key) && key[0] === 'transactions-period', undefined, { revalidate: true }),
        mutate((key) => Array.isArray(key) && key[0] === 'transactions-list', undefined, { revalidate: true }),
      ]);

      onCategoryUpdated?.();
      onClose();
    } catch (err) {
      console.error('Failed to update category:', err);
      setError('Failed to update category. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = selectedCategory !== transaction.category;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-md w-full m-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{transaction.emoji || '📝'}</span>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Edit Transaction</h2>
              <p className="text-gray-500 text-sm">Update category</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Transaction Details */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-semibold text-gray-900 text-lg">
                  {transaction.merchant || 'Unknown Merchant'}
                </div>
                <div className="text-sm text-gray-500">{transaction.description}</div>
              </div>
              <div className="text-right">
                <div className="font-bold text-xl text-gray-900">
                  {formatCurrency(transaction.amount)}
                </div>
                {transaction.date && (
                  <div className="text-sm text-gray-500">
                    {transaction.date} {transaction.time && `at ${transaction.time}`}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Category Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category
            </label>
            {categoriesLoading ? (
              <div className="h-10 bg-gray-100 rounded-lg animate-pulse"></div>
            ) : (
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-900"
              >
                <option value="">Select a category</option>
                {categories.map((cat) => (
                  <option key={cat.name} value={cat.name}>
                    {cat.name} {cat.transaction_count && `(${cat.transaction_count})`}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:text-gray-900 font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className={`px-6 py-2 rounded-lg font-medium transition ${
              hasChanges && !isSaving
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {isSaving ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Saving...
              </span>
            ) : (
              'Save Changes'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

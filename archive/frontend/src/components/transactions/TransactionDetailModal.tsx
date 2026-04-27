'use client';

import { useState, useEffect } from 'react';
import useSWR from 'swr';
import { mutate } from 'swr';
import { X, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { useCategories } from '@/lib/hooks';
import {
  getTransactionDetail,
  updateTransaction,
  markTransactionOneTime,
  markTransactionNormal,
  TransactionDetail,
  checkMerchantRule,
  updateTransactionCategoryWithRule,
  MerchantCheckResponse,
} from '@/lib/api';
import { UnusualBadge } from './UnusualBadge';
import { TagSelector } from './TagSelector';
import { TagBadge } from '@/components/ui/TagBadge';

interface TransactionDetailModalProps {
  transactionId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdated?: () => void;
}

export function TransactionDetailModal({
  transactionId,
  isOpen,
  onClose,
  onUpdated,
}: TransactionDetailModalProps) {
  const { categories, isLoading: categoriesLoading } = useCategories();

  // Fetch transaction details
  const { data: transaction, isLoading, mutate: refreshTransaction } = useSWR(
    transactionId && isOpen ? ['transaction-detail', transactionId] : null,
    () => getTransactionDetail(transactionId!)
  );

  // Form state
  const [merchantName, setMerchantName] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isMarkingAnomaly, setIsMarkingAnomaly] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Bulk category rule state
  const [showRuleDialog, setShowRuleDialog] = useState(false);
  const [merchantCheckData, setMerchantCheckData] = useState<MerchantCheckResponse | null>(null);
  const [pendingCategory, setPendingCategory] = useState<string | null>(null);

  // Sync form state when transaction loads
  useEffect(() => {
    if (transaction) {
      setMerchantName(transaction.merchant_name || '');
      setSelectedCategory(transaction.category || '');
      setSelectedTagIds(transaction.tags.map((t) => t.id));
      setError(null);
    }
  }, [transaction]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setError(null);
      setShowRuleDialog(false);
      setMerchantCheckData(null);
      setPendingCategory(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Math.abs(amount));

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const hasChanges = transaction && (
    merchantName !== (transaction.merchant_name || '') ||
    selectedCategory !== (transaction.category || '') ||
    JSON.stringify(selectedTagIds.sort()) !== JSON.stringify(transaction.tags.map((t) => t.id).sort())
  );

  const handleSave = async () => {
    if (!transaction || !hasChanges) {
      onClose();
      return;
    }

    // If category changed and merchant exists, check for rule opportunity
    const categoryChanged = selectedCategory !== (transaction.category || '');
    if (categoryChanged && transaction.merchant_name) {
      setPendingCategory(selectedCategory);
      try {
        const checkResult = await checkMerchantRule(transaction.merchant_name);
        setMerchantCheckData(checkResult);

        // Only show dialog if there's more than 1 matching transaction
        if (checkResult.matching_transactions > 1) {
          setShowRuleDialog(true);
          return; // Wait for user decision
        }
      } catch (err) {
        console.error('Failed to check merchant rule:', err);
        // Continue with single update if check fails
      }
    }

    // Proceed with single transaction update (no rule)
    await saveTransaction(false);
  };

  const saveTransaction = async (applyToAll: boolean) => {
    if (!transaction) return;

    setIsSaving(true);
    setError(null);
    setShowRuleDialog(false);

    try {
      const categoryToSave = pendingCategory || selectedCategory;
      const categoryChanged = categoryToSave !== (transaction.category || '');
      const merchantChanged = merchantName !== (transaction.merchant_name || '');
      const tagsChanged = JSON.stringify(selectedTagIds.sort()) !== JSON.stringify(transaction.tags.map((t) => t.id).sort());

      // If category changed, use the rule-aware endpoint
      if (categoryChanged) {
        const result = await updateTransactionCategoryWithRule(
          transaction.id,
          categoryToSave,
          applyToAll
        );

        // Update other fields if needed
        if (merchantChanged || tagsChanged) {
          await updateTransaction(transaction.id, {
            merchant_name: merchantChanged ? merchantName : undefined,
            tag_ids: tagsChanged ? selectedTagIds : undefined,
          });
        }
      } else {
        // Only merchant/tags changed
        await updateTransaction(transaction.id, {
          merchant_name: merchantChanged ? merchantName : undefined,
          tag_ids: tagsChanged ? selectedTagIds : undefined,
        });
      }

      // Invalidate caches
      await Promise.all([
        mutate('dashboard'),
        mutate((key) => Array.isArray(key) && key[0] === 'transactions-list', undefined, { revalidate: true }),
        mutate((key) => Array.isArray(key) && key[0] === 'unusual-transactions', undefined, { revalidate: true }),
        refreshTransaction(),
      ]);

      onUpdated?.();
      onClose();
    } catch (err) {
      console.error('Failed to update transaction:', err);
      setError('Failed to save changes. Please try again.');
    } finally {
      setIsSaving(false);
      setPendingCategory(null);
    }
  };

  const handleMarkOneTime = async () => {
    if (!transaction) return;
    setIsMarkingAnomaly(true);
    try {
      await markTransactionOneTime(transaction.id);
      await Promise.all([
        refreshTransaction(),
        mutate((key) => Array.isArray(key) && key[0] === 'unusual-transactions', undefined, { revalidate: true }),
        mutate((key) => Array.isArray(key) && key[0] === 'transactions-list', undefined, { revalidate: true }),
      ]);
      onUpdated?.();
    } catch (err) {
      console.error('Failed to mark as one-time:', err);
    } finally {
      setIsMarkingAnomaly(false);
    }
  };

  const handleMarkNormal = async () => {
    if (!transaction) return;
    setIsMarkingAnomaly(true);
    try {
      await markTransactionNormal(transaction.id);
      await Promise.all([
        refreshTransaction(),
        mutate((key) => Array.isArray(key) && key[0] === 'unusual-transactions', undefined, { revalidate: true }),
        mutate((key) => Array.isArray(key) && key[0] === 'transactions-list', undefined, { revalidate: true }),
      ]);
      onUpdated?.();
    } catch (err) {
      console.error('Failed to mark as normal:', err);
    } finally {
      setIsMarkingAnomaly(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-lg w-full m-4 overflow-hidden max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-neutral-200">
          <div className="flex items-center gap-3">
            <span className="text-3xl">
              {transaction?.amount && transaction.amount < 0 ? '💸' : '💰'}
            </span>
            <div>
              <h2 className="text-xl font-bold text-neutral-900">Transaction Details</h2>
              <p className="text-neutral-500 text-sm">Edit details, category, and tags</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {isLoading ? (
            <div className="space-y-4">
              <div className="h-20 bg-neutral-100 rounded-xl animate-pulse"></div>
              <div className="h-12 bg-neutral-100 rounded-lg animate-pulse"></div>
              <div className="h-12 bg-neutral-100 rounded-lg animate-pulse"></div>
            </div>
          ) : transaction ? (
            <>
              {/* Transaction Summary */}
              <div className="bg-cream-50 rounded-xl p-4 space-y-2">
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-neutral-900 text-lg truncate">
                      {transaction.merchant_name || 'Unknown Merchant'}
                    </div>
                    <div className="text-sm text-neutral-500 truncate" title={transaction.description}>
                      {transaction.description}
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <div className={`font-bold text-xl ${transaction.amount < 0 ? 'text-neutral-900' : 'text-success-500'}`}>
                      {transaction.amount < 0 ? '-' : '+'}{formatCurrency(transaction.amount)}
                    </div>
                    <div className="text-sm text-neutral-500">
                      {formatDate(transaction.date)}
                    </div>
                  </div>
                </div>

                {/* Current tags display */}
                {transaction.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-2 border-t border-neutral-200 mt-2">
                    {transaction.tags.map((tag) => (
                      <TagBadge key={tag.id} tag={tag} size="sm" />
                    ))}
                  </div>
                )}
              </div>

              {/* Anomaly Alert */}
              {transaction.is_anomaly && !transaction.user_reviewed && (
                <div className="bg-warning-50 border border-warning-200 rounded-xl p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-warning-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="font-medium text-warning-700">
                        Flagged as Unusual
                      </div>
                      <div className="text-sm text-warning-700 mt-1">
                        <UnusualBadge anomalyReason={transaction.anomaly_reason} size="sm" />
                      </div>
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={handleMarkOneTime}
                          disabled={isMarkingAnomaly}
                          className="px-3 py-1.5 text-sm font-medium bg-warning-100 text-warning-700 rounded-lg hover:bg-warning-200 transition disabled:opacity-50"
                        >
                          <Clock className="w-4 h-4 inline mr-1" />
                          One-Time
                        </button>
                        <button
                          onClick={handleMarkNormal}
                          disabled={isMarkingAnomaly}
                          className="px-3 py-1.5 text-sm font-medium bg-success-100 text-success-700 rounded-lg hover:bg-success-200 transition disabled:opacity-50"
                        >
                          <CheckCircle className="w-4 h-4 inline mr-1" />
                          Normal
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Reviewed status */}
              {transaction.is_anomaly && transaction.user_reviewed && (
                <div className="bg-success-50 border border-success-200 rounded-xl p-3 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-success-500" />
                  <span className="text-sm text-success-700">
                    Reviewed - marked as {transaction.is_one_time ? 'one-time expense' : 'normal'}
                  </span>
                </div>
              )}

              {/* Merchant Name */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Merchant Name
                </label>
                <input
                  type="text"
                  value={merchantName}
                  onChange={(e) => setMerchantName(e.target.value)}
                  placeholder="Enter merchant name"
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-transparent"
                />
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Category
                </label>
                {categoriesLoading ? (
                  <div className="h-10 bg-neutral-100 rounded-lg animate-pulse"></div>
                ) : (
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-transparent bg-white"
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

              {/* Tags */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Tags
                </label>
                <TagSelector
                  selectedTagIds={selectedTagIds}
                  onChange={setSelectedTagIds}
                />
              </div>

              {/* Error Message */}
              {error && (
                <div className="bg-danger-50 text-danger-500 px-4 py-2 rounded-lg text-sm">
                  {error}
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-8 text-neutral-500">
              Transaction not found
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-200 bg-cream-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-neutral-700 hover:text-neutral-900 font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className={`px-6 py-2 rounded-lg font-medium transition shadow-button ${
              hasChanges && !isSaving
                ? 'bg-slate-900 text-white hover:bg-slate-800 hover:-translate-y-px'
                : 'bg-slate-200 text-slate-400 cursor-not-allowed'
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

      {/* Apply to All Confirmation Dialog */}
      {showRuleDialog && merchantCheckData && transaction && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full m-4 overflow-hidden">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-3xl">🏷️</span>
                <h3 className="text-lg font-bold text-neutral-900">
                  Apply to all {transaction.merchant_name} transactions?
                </h3>
              </div>

              <p className="text-neutral-600 mb-4">
                {merchantCheckData.has_existing_rule ? (
                  <>
                    You have an existing rule for this merchant (currently: <span className="font-medium">{merchantCheckData.existing_category}</span>).
                    This will update <span className="font-bold">{merchantCheckData.matching_transactions}</span> transactions to &quot;<span className="font-medium">{pendingCategory}</span>&quot;.
                  </>
                ) : (
                  <>
                    Create a rule to automatically categorize all <span className="font-bold">{merchantCheckData.matching_transactions}</span> transactions
                    from &quot;<span className="font-medium">{transaction.merchant_name}</span>&quot; as &quot;<span className="font-medium">{pendingCategory}</span>&quot;?
                    This will also apply to future transactions.
                  </>
                )}
              </p>

              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => saveTransaction(false)}
                  disabled={isSaving}
                  className="px-4 py-2 text-neutral-700 hover:text-neutral-900 font-medium transition"
                >
                  Just this one
                </button>
                <button
                  onClick={() => saveTransaction(true)}
                  disabled={isSaving}
                  className="px-4 py-2 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 transition disabled:opacity-50"
                >
                  {isSaving ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Applying...
                    </span>
                  ) : (
                    `Apply to all (${merchantCheckData.matching_transactions})`
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

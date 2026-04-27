'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTransactionsList, useCategories, useTags } from '@/lib/hooks';
import { updateTransactionCategoryWithRule, checkMerchantRule, TransactionListParams, TransactionDetail, MerchantCheckResponse } from '@/lib/api';
import { mutate } from 'swr';
import { AlertTriangle, Search, X } from 'lucide-react';
import { UnusualBadge } from './UnusualBadge';
import { TagBadge } from '@/components/ui/TagBadge';
import { TransactionDetailModal } from './TransactionDetailModal';

// Custom hook for debounced value
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

type SortField = 'date' | 'amount' | 'merchant' | 'category';
type SortOrder = 'asc' | 'desc';

interface TransactionsTableProps {
  initialShowUnusualOnly?: boolean;
  initialMonth?: number | null;
  initialYear?: number | null;
}

export function TransactionsTable({
  initialShowUnusualOnly = false,
  initialMonth = null,
  initialYear = null,
}: TransactionsTableProps) {
  const [sortBy, setSortBy] = useState<SortField>('date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [page, setPage] = useState(0);
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [showUnusualOnly, setShowUnusualOnly] = useState(initialShowUnusualOnly);
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [filterMonth, setFilterMonth] = useState<number | null>(initialMonth);
  const [filterYear, setFilterYear] = useState<number | null>(initialYear);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingCategory, setEditingCategory] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null);

  // Inline rule prompt state
  const [showInlineRulePrompt, setShowInlineRulePrompt] = useState(false);
  const [inlineRuleData, setInlineRuleData] = useState<{
    transactionId: string;
    merchantName: string;
    category: string;
    checkResult: MerchantCheckResponse;
  } | null>(null);

  // Debounce search query to avoid excessive API calls
  const debouncedSearch = useDebounce(searchQuery, 300);

  const limit = 50;

  // Helper to get month name
  const getMonthName = (month: number) => {
    const date = new Date(2000, month - 1, 1);
    return date.toLocaleString('default', { month: 'long' });
  };

  // Calculate start_date and end_date from month/year filter
  const getDateRange = () => {
    if (filterMonth && filterYear) {
      const startDate = new Date(filterYear, filterMonth - 1, 1);
      const endDate = new Date(filterYear, filterMonth, 0); // Last day of the month
      return {
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
      };
    }
    return {};
  };

  const dateRange = getDateRange();
  const params: TransactionListParams = {
    sort_by: sortBy,
    sort_order: sortOrder,
    limit,
    offset: page * limit,
    ...(categoryFilter && { category: categoryFilter }),
    ...(showUnusualOnly && { show_unusual_only: true }),
    ...(selectedTagIds.length > 0 && { tag_ids: selectedTagIds }),
    ...(debouncedSearch.length >= 2 && { q: debouncedSearch }),
    ...dateRange,
  };

  // Reset to page 0 when search changes
  useEffect(() => {
    setPage(0);
  }, [debouncedSearch]);

  const { data, isLoading, refresh } = useTransactionsList(params);
  const { categories } = useCategories();
  const { allTags } = useTags();

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

  const handleEditCategory = (transaction: TransactionDetail) => {
    setEditingId(transaction.id);
    setEditingCategory(transaction.category || '');
  };

  const handleSaveCategory = async (transactionId: string, merchantName: string | null) => {
    if (!editingCategory) {
      setEditingId(null);
      return;
    }

    // Check for rule opportunity if merchant exists
    if (merchantName) {
      try {
        const checkResult = await checkMerchantRule(merchantName);
        if (checkResult.matching_transactions > 1) {
          // Show inline prompt
          setInlineRuleData({
            transactionId,
            merchantName,
            category: editingCategory,
            checkResult,
          });
          setShowInlineRulePrompt(true);
          return;
        }
      } catch (err) {
        console.error('Failed to check merchant rule:', err);
      }
    }

    // No prompt needed, save directly
    await saveCategory(transactionId, editingCategory, false);
  };

  const saveCategory = async (transactionId: string, category: string, applyToAll: boolean) => {
    setIsSaving(true);
    setShowInlineRulePrompt(false);
    try {
      await updateTransactionCategoryWithRule(transactionId, category, applyToAll);
      await refresh();
      await mutate('dashboard');
    } catch (err) {
      console.error('Failed to update category:', err);
    } finally {
      setIsSaving(false);
      setEditingId(null);
      setInlineRuleData(null);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingCategory('');
  };

  const handleRowClick = (transaction: TransactionDetail) => {
    setSelectedTransactionId(transaction.id);
  };

  const handleModalClose = () => {
    setSelectedTransactionId(null);
  };

  const handleModalUpdate = () => {
    refresh();
    mutate('dashboard');
  };

  const clearAllFilters = () => {
    setCategoryFilter('');
    setShowUnusualOnly(false);
    setSelectedTagIds([]);
    setFilterMonth(null);
    setFilterYear(null);
    setSearchQuery('');
    setPage(0);
  };

  const clearMonthFilter = () => {
    setFilterMonth(null);
    setFilterYear(null);
    setPage(0);
  };

  const hasActiveFilters = categoryFilter || showUnusualOnly || selectedTagIds.length > 0 || (filterMonth && filterYear) || searchQuery;

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortBy !== field) {
      return (
        <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return sortOrder === 'asc' ? (
      <svg className="w-4 h-4 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  const totalPages = Math.ceil(data.total / limit);

  return (
    <>
      <div className="bg-white rounded-xl shadow border border-slate-200 overflow-hidden">
        {/* Filters */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex flex-wrap items-center gap-4">
            {/* Search input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search transactions..."
                className="w-64 pl-9 pr-8 py-1.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-transparent bg-white text-slate-700 placeholder:text-slate-400"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-slate-400 hover:text-slate-600 rounded"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Transaction count */}
            <div className="text-sm text-slate-600">
              {data.total} transaction{data.total !== 1 ? 's' : ''}
              {debouncedSearch && ` matching "${debouncedSearch}"`}
            </div>

            {/* Unusual filter toggle - Soft Wash Style */}
            <button
              onClick={() => {
                setShowUnusualOnly(!showUnusualOnly);
                setPage(0);
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg transition ${
                showUnusualOnly
                  ? 'bg-amber-500/10 border-amber-300 text-amber-700'
                  : 'border-slate-300 text-slate-600 hover:bg-slate-50'
              }`}
            >
              <AlertTriangle className="w-4 h-4" />
              Unusual
              {data.anomaly_count > 0 && !showUnusualOnly && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-amber-500 text-white rounded-full">
                  {data.anomaly_count}
                </span>
              )}
            </button>

            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setPage(0);
              }}
              className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-transparent bg-white text-slate-700"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat.name} value={cat.name}>
                  {cat.name}
                </option>
              ))}
            </select>

            {/* Tag Filter */}
            <div className="relative">
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value && !selectedTagIds.includes(e.target.value)) {
                    setSelectedTagIds([...selectedTagIds, e.target.value]);
                    setPage(0);
                  }
                }}
                className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-400 focus:border-transparent bg-white text-slate-700"
              >
                <option value="">Filter by tag...</option>
                {allTags
                  .filter((tag) => !selectedTagIds.includes(tag.id))
                  .map((tag) => (
                    <option key={tag.id} value={tag.id}>
                      {tag.name}
                    </option>
                  ))}
              </select>
            </div>

            {/* Selected tag filters */}
            {selectedTagIds.map((tagId) => {
              const tag = allTags.find((t) => t.id === tagId);
              if (!tag) return null;
              return (
                <TagBadge
                  key={tagId}
                  tag={tag}
                  size="sm"
                  onRemove={() => {
                    setSelectedTagIds(selectedTagIds.filter((id) => id !== tagId));
                    setPage(0);
                  }}
                />
              );
            })}

            {/* Month filter badge */}
            {filterMonth && filterYear && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-sky-500/10 border border-sky-300 text-sky-700 rounded-lg">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {getMonthName(filterMonth)} {filterYear}
                <button
                  onClick={clearMonthFilter}
                  className="ml-1 hover:bg-sky-200 rounded p-0.5"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </span>
            )}

            {/* Clear all filters */}
            {hasActiveFilters && (
              <button
                onClick={clearAllFilters}
                className="text-sm text-slate-600 hover:text-slate-800"
              >
                Clear all filters
              </button>
            )}

            <div className="flex-1" />

            <div className="text-sm text-slate-500">Click row to edit details</div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-6 py-3 text-left">
                  <button
                    onClick={() => handleSort('date')}
                    className="flex items-center gap-1 text-xs font-semibold text-slate-500 uppercase tracking-wide hover:text-slate-900"
                  >
                    Date <SortIcon field="date" />
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Description
                </th>
                <th className="px-6 py-3 text-left">
                  <button
                    onClick={() => handleSort('merchant')}
                    className="flex items-center gap-1 text-xs font-semibold text-slate-500 uppercase tracking-wide hover:text-slate-900"
                  >
                    Merchant <SortIcon field="merchant" />
                  </button>
                </th>
                <th className="px-6 py-3 text-left">
                  <button
                    onClick={() => handleSort('category')}
                    className="flex items-center gap-1 text-xs font-semibold text-slate-500 uppercase tracking-wide hover:text-slate-900"
                  >
                    Category <SortIcon field="category" />
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Tags
                </th>
                <th className="px-6 py-3 text-right">
                  <button
                    onClick={() => handleSort('amount')}
                    className="flex items-center gap-1 text-xs font-semibold text-slate-500 uppercase tracking-wide hover:text-slate-900 ml-auto"
                  >
                    Amount <SortIcon field="amount" />
                  </button>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {isLoading && data.transactions.length === 0 ? (
                [...Array(10)].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-24"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-48"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-32"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-24"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-16"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-20 ml-auto"></div></td>
                  </tr>
                ))
              ) : data.transactions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    No transactions found
                  </td>
                </tr>
              ) : (
                data.transactions.map((txn) => (
                  <tr
                    key={txn.id}
                    onClick={() => handleRowClick(txn)}
                    className="hover:bg-slate-50 transition cursor-pointer"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {txn.is_anomaly && !txn.user_reviewed && (
                          <UnusualBadge anomalyReason={txn.anomaly_reason} size="sm" showLabel={false} />
                        )}
                        <span className="text-sm text-slate-600">{formatDate(txn.date)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-slate-900 max-w-xs truncate" title={txn.description}>
                        {txn.description}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-slate-900">
                        {txn.merchant_name || '-'}
                      </div>
                    </td>
                    <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                      {editingId === txn.id ? (
                        <div className="flex items-center gap-2">
                          <select
                            value={editingCategory}
                            onChange={(e) => setEditingCategory(e.target.value)}
                            className="px-2 py-1 text-sm border border-slate-300 rounded focus:ring-2 focus:ring-slate-400 focus:border-transparent"
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
                            onClick={() => handleSaveCategory(txn.id, txn.merchant_name)}
                            disabled={isSaving}
                            className="p-1 text-emerald-600 hover:text-emerald-700 disabled:opacity-50"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="p-1 text-slate-400 hover:text-slate-600"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleEditCategory(txn);
                          }}
                          className="inline-flex items-center gap-1 px-2 py-1 text-sm text-slate-700 bg-slate-100 rounded hover:bg-slate-200 transition capitalize"
                        >
                          {txn.category || 'uncategorized'}
                          <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {txn.tags.slice(0, 3).map((tag) => (
                          <TagBadge key={tag.id} tag={tag} size="sm" />
                        ))}
                        {txn.tags.length > 3 && (
                          <span className="text-xs text-slate-500">+{txn.tags.length - 3}</span>
                        )}
                        {txn.tags.length === 0 && (
                          <span className="text-xs text-slate-400">-</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className={`text-sm font-semibold ${txn.amount < 0 ? 'text-slate-900' : 'text-emerald-600'}`}>
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
          <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
            <div className="text-sm text-slate-600">
              Showing {page * limit + 1} - {Math.min((page + 1) * limit, data.total)} of {data.total}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-slate-600">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={!data.has_more}
                className="px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Transaction Detail Modal */}
      <TransactionDetailModal
        transactionId={selectedTransactionId}
        isOpen={!!selectedTransactionId}
        onClose={handleModalClose}
        onUpdated={handleModalUpdate}
      />

      {/* Inline Rule Prompt Dialog */}
      {showInlineRulePrompt && inlineRuleData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full m-4 overflow-hidden">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-3xl">🏷️</span>
                <h3 className="text-lg font-bold text-neutral-900">
                  Apply to all {inlineRuleData.merchantName} transactions?
                </h3>
              </div>

              <p className="text-neutral-600 mb-4">
                {inlineRuleData.checkResult.has_existing_rule ? (
                  <>
                    You have an existing rule for this merchant (currently: <span className="font-medium">{inlineRuleData.checkResult.existing_category}</span>).
                    This will update <span className="font-bold">{inlineRuleData.checkResult.matching_transactions}</span> transactions to &quot;<span className="font-medium">{inlineRuleData.category}</span>&quot;.
                  </>
                ) : (
                  <>
                    Create a rule to automatically categorize all <span className="font-bold">{inlineRuleData.checkResult.matching_transactions}</span> transactions
                    from &quot;<span className="font-medium">{inlineRuleData.merchantName}</span>&quot; as &quot;<span className="font-medium">{inlineRuleData.category}</span>&quot;?
                    This will also apply to future transactions.
                  </>
                )}
              </p>

              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => saveCategory(inlineRuleData.transactionId, inlineRuleData.category, false)}
                  disabled={isSaving}
                  className="px-4 py-2 text-neutral-700 hover:text-neutral-900 font-medium transition"
                >
                  Just this one
                </button>
                <button
                  onClick={() => saveCategory(inlineRuleData.transactionId, inlineRuleData.category, true)}
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
                    `Apply to all (${inlineRuleData.checkResult.matching_transactions})`
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

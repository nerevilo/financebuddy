'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  syncInstitution,
  disconnectInstitution,
  saveTellerConnection,
} from '@/lib/api';
import { useInstitutions, refreshAllData } from '@/lib/hooks';
import { formatCurrency } from '@/lib/utils';

declare global {
  interface Window {
    TellerConnect: {
      setup: (config: any) => { open: () => void };
    };
  }
}

interface InstitutionSidebarProps {
  onDataChange?: () => void;
}

export function InstitutionSidebar({ onDataChange }: InstitutionSidebarProps) {
  const { institutions, isLoading: loading, refresh: refreshInstitutions } = useInstitutions();
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [syncingIds, setSyncingIds] = useState<Set<string>>(new Set());
  const [tellerReady, setTellerReady] = useState(false);
  const [addingBank, setAddingBank] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const pathname = usePathname();

  // Expand all institutions by default when loaded
  useEffect(() => {
    if (institutions.length > 0 && expandedIds.size === 0) {
      setExpandedIds(new Set(institutions.map(i => i.id)));
    }
  }, [institutions, expandedIds.size]);

  useEffect(() => {
    loadTellerScript();
  }, []);

  // Close menu when clicking outside
  useEffect(() => {
    if (!menuOpenId) return;
    const handleClick = () => setMenuOpenId(null);
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [menuOpenId]);

  const loadTellerScript = () => {
    if (document.querySelector('script[src*="teller.io"]')) {
      setTellerReady(true);
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://cdn.teller.io/connect/connect.js';
    script.async = true;
    script.onload = () => setTellerReady(true);
    document.body.appendChild(script);
  };

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSync = async (institutionId: string) => {
    setSyncingIds(prev => new Set(prev).add(institutionId));
    try {
      await syncInstitution(institutionId);
      await refreshAllData();
      onDataChange?.();
    } catch (error) {
      console.error('Sync failed:', error);
    } finally {
      setSyncingIds(prev => {
        const next = new Set(prev);
        next.delete(institutionId);
        return next;
      });
    }
  };

  const handleDisconnect = async (institutionId: string) => {
    if (!confirm('Disconnect this bank? Historical data will be preserved.')) return;
    try {
      await disconnectInstitution(institutionId);
      await refreshAllData();
      onDataChange?.();
    } catch (error) {
      console.error('Disconnect failed:', error);
    }
    setMenuOpenId(null);
  };

  const openTellerConnect = () => {
    if (!window.TellerConnect) return;

    setAddingBank(true);
    const tellerConnect = window.TellerConnect.setup({
      applicationId: process.env.NEXT_PUBLIC_TELLER_APP_ID || 'app_pn55bmnf8k4papve7o000',
      environment: process.env.NEXT_PUBLIC_TELLER_ENV || 'sandbox',
      products: ['balance', 'transactions', 'identity'],
      onSuccess: async (enrollment: any) => {
        try {
          await saveTellerConnection({
            accessToken: enrollment.accessToken,
            enrollment: enrollment.enrollment,
            user: enrollment.user || {},
          });
          // Refresh all cached data after connecting
          await refreshAllData();
          onDataChange?.();
        } catch (error) {
          console.error('Error saving connection:', error);
        } finally {
          setAddingBank(false);
        }
      },
      onExit: () => setAddingBank(false),
      onFailure: () => setAddingBank(false),
    });
    tellerConnect.open();
  };

  const formatTimeAgo = (dateString: string | null) => {
    if (!dateString) return 'Never synced';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const getAccountIcon = (type: string, subtype: string | null) => {
    const baseClass = "w-4 h-4";
    if (type === 'credit') {
      return (
        <svg className={baseClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
      );
    }
    if (subtype === 'savings') {
      return (
        <svg className={baseClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    }
    return (
      <svg className={baseClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    );
  };

  if (loading) {
    return (
      <aside className="w-72 bg-surface-sidebar flex flex-col fixed left-0 top-0 h-screen">
        <div className="p-4 border-b border-slate-700">
          <h2 className="font-semibold text-white">Connected Accounts</h2>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin h-6 w-6 border-2 border-slate-400 border-t-transparent rounded-full" />
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-72 bg-surface-sidebar flex flex-col fixed left-0 top-0 h-screen">
      <div className="p-4 border-b border-slate-700">
        <h2 className="font-semibold text-white tracking-tight">Finance Buddy</h2>
      </div>

      {/* Navigation */}
      <nav className="p-2 border-b border-slate-700">
        <Link
          href="/"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
            pathname === '/'
              ? 'bg-slate-700 text-white'
              : 'text-slate-300 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Dashboard
        </Link>
        <Link
          href="/transactions"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
            pathname === '/transactions'
              ? 'bg-slate-700 text-white'
              : 'text-slate-300 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
          </svg>
          All Transactions
        </Link>
        <Link
          href="/chat"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
            pathname === '/chat'
              ? 'bg-slate-700 text-white'
              : 'text-slate-300 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          Finance Buddy
        </Link>
        <Link
          href="/settings"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
            pathname === '/settings'
              ? 'bg-slate-700 text-white'
              : 'text-slate-300 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Settings
        </Link>
      </nav>

      {/* Accounts Header */}
      <div className="px-4 py-3">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Connected Accounts</h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {institutions.length === 0 ? (
          <div className="p-4 text-center text-slate-400">
            <p className="text-sm">No accounts connected</p>
            <p className="text-xs mt-1 text-slate-500">Add a bank to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700/50">
            {institutions.map(institution => (
              <div key={institution.id} className="py-2">
                {/* Institution Header */}
                <div className="px-4 py-2 flex items-center justify-between group">
                  <button
                    onClick={() => toggleExpand(institution.id)}
                    className="flex items-center gap-2 flex-1 text-left"
                  >
                    <svg
                      className={`w-4 h-4 text-slate-500 transition-transform ${
                        expandedIds.has(institution.id) ? 'rotate-90' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    <span className="font-medium text-white text-sm">{institution.name}</span>
                  </button>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {/* Sync Button */}
                    <button
                      onClick={() => handleSync(institution.id)}
                      disabled={syncingIds.has(institution.id)}
                      className="p-1 text-slate-400 hover:text-white rounded"
                      title="Sync"
                    >
                      <svg
                        className={`w-4 h-4 ${syncingIds.has(institution.id) ? 'animate-spin' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                    </button>

                    {/* Menu Button */}
                    <div className="relative">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setMenuOpenId(menuOpenId === institution.id ? null : institution.id);
                        }}
                        className="p-1 text-slate-400 hover:text-white rounded"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                          <circle cx="12" cy="6" r="2" />
                          <circle cx="12" cy="12" r="2" />
                          <circle cx="12" cy="18" r="2" />
                        </svg>
                      </button>

                      {menuOpenId === institution.id && (
                        <div
                          className="absolute right-0 mt-1 w-36 bg-slate-800 border border-slate-600 rounded-lg shadow-lg z-10"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={() => handleDisconnect(institution.id)}
                            className="w-full px-3 py-2 text-left text-sm text-rose-400 hover:bg-slate-700 rounded-lg"
                          >
                            Disconnect
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Accounts List */}
                {expandedIds.has(institution.id) && (
                  <div className="px-4 pb-2">
                    {institution.accounts.map(account => (
                      <div
                        key={account.id}
                        className="flex items-center justify-between py-2 pl-6"
                      >
                        <div className="flex items-center gap-2">
                          <div className="text-slate-400">{getAccountIcon(account.type, account.subtype)}</div>
                          <div>
                            <p className="text-sm text-slate-200">{account.name}</p>
                            {account.last_four && (
                              <p className="text-xs text-slate-500">••{account.last_four}</p>
                            )}
                          </div>
                        </div>
                        <span className={`text-sm font-medium ${
                          account.current_balance < 0 ? 'text-rose-400' : 'text-white'
                        }`}>
                          {formatCurrency(account.current_balance)}
                        </span>
                      </div>
                    ))}

                    {/* Sync Status */}
                    <div className="pl-6 pt-1">
                      <span className="text-xs text-slate-500">
                        Synced {formatTimeAgo(institution.last_synced_at)}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Bank Button */}
      <div className="p-4 border-t border-slate-700">
        <button
          onClick={openTellerConnect}
          disabled={!tellerReady || addingBank}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-slate-700 rounded-lg hover:bg-slate-600 disabled:opacity-50 transition-colors"
        >
          {addingBank ? (
            <>
              <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
              Connecting...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Add Bank
            </>
          )}
        </button>
      </div>
    </aside>
  );
}

'use client';

import { useState } from 'react';
import {
  Key,
  Plus,
  Copy,
  Check,
  Trash2,
  ChevronLeft,
  AlertTriangle,
  Clock,
  Shield,
  ExternalLink,
  Eye,
  EyeOff
} from 'lucide-react';
import { useApiKeys } from '@/lib/hooks';
import { APIKey, APIKeyCreated } from '@/lib/api';
import { InstitutionSidebar } from '@/components/dashboard/InstitutionSidebar';
import { refreshAllData } from '@/lib/hooks';
import { ProtectedRoute } from '@/lib/auth';
import Link from 'next/link';

// Format relative time
function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Never';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

// API Key Card Component
function APIKeyCard({
  apiKey,
  onRevoke
}: {
  apiKey: APIKey;
  onRevoke: (id: string) => void;
}) {
  const [isRevoking, setIsRevoking] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleRevoke = async () => {
    setIsRevoking(true);
    try {
      await onRevoke(apiKey.id);
    } finally {
      setIsRevoking(false);
      setShowConfirm(false);
    }
  };

  return (
    <div className={`bg-white rounded-xl border ${apiKey.is_active ? 'border-slate-200' : 'border-slate-200 opacity-60'} p-5`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${apiKey.is_active ? 'bg-slate-100' : 'bg-slate-50'}`}>
            <Key className="w-5 h-5 text-slate-600" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800">{apiKey.name}</h3>
            <p className="text-sm text-slate-500 font-mono">{apiKey.key_prefix}...</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!apiKey.is_active && (
            <span className="px-2 py-1 text-xs font-medium bg-red-50 text-red-600 rounded">
              Revoked
            </span>
          )}
          <span className={`px-2 py-1 text-xs font-medium rounded ${
            apiKey.tier === 'beta'
              ? 'bg-purple-50 text-purple-600'
              : apiKey.tier === 'pro'
              ? 'bg-amber-50 text-amber-600'
              : 'bg-slate-50 text-slate-600'
          }`}>
            {apiKey.tier}
          </span>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-6 text-sm text-slate-500">
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4" />
          <span>Last used: {formatRelativeTime(apiKey.last_used_at)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Shield className="w-4 h-4" />
          <span>{apiKey.scopes.includes('*') ? 'Full access' : apiKey.scopes.join(', ')}</span>
        </div>
      </div>

      {apiKey.expires_at && (
        <div className="mt-2 text-sm text-amber-600 flex items-center gap-1.5">
          <AlertTriangle className="w-4 h-4" />
          <span>Expires: {new Date(apiKey.expires_at).toLocaleDateString()}</span>
        </div>
      )}

      {apiKey.is_active && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          {showConfirm ? (
            <div className="flex items-center justify-between">
              <span className="text-sm text-red-600">Revoke this key? This cannot be undone.</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowConfirm(false)}
                  className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRevoke}
                  disabled={isRevoking}
                  className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                >
                  {isRevoking ? 'Revoking...' : 'Yes, Revoke'}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowConfirm(true)}
              className="flex items-center gap-1.5 text-sm text-red-600 hover:text-red-700"
            >
              <Trash2 className="w-4 h-4" />
              Revoke Key
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// Create API Key Modal
function CreateAPIKeyModal({
  isOpen,
  onClose,
  onCreate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string) => Promise<APIKeyCreated>;
}) {
  const [name, setName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createdKey, setCreatedKey] = useState<APIKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!name.trim()) return;

    setIsCreating(true);
    setError(null);

    try {
      const key = await onCreate(name);
      setCreatedKey(key);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create API key');
    } finally {
      setIsCreating(false);
    }
  };

  const handleCopy = async () => {
    if (!createdKey) return;

    await navigator.clipboard.writeText(createdKey.key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setName('');
    setCreatedKey(null);
    setCopied(false);
    setShowKey(false);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-lg w-full m-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-xl font-semibold text-slate-800">
            {createdKey ? 'API Key Created' : 'Create API Key'}
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            {createdKey
              ? 'Copy your key now. It will not be shown again.'
              : 'Create a new API key for programmatic access to your data.'
            }
          </p>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              {error}
            </div>
          )}

          {createdKey ? (
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium">Save this key now!</p>
                    <p className="mt-1">This is the only time you will see the full API key. Store it securely.</p>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Your API Key</label>
                <div className="relative">
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={createdKey.key}
                    readOnly
                    className="w-full px-4 py-3 pr-24 bg-slate-50 border border-slate-200 rounded-lg font-mono text-sm"
                  />
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                    <button
                      onClick={() => setShowKey(!showKey)}
                      className="p-2 text-slate-400 hover:text-slate-600"
                    >
                      {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={handleCopy}
                      className="p-2 text-slate-400 hover:text-slate-600"
                    >
                      {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Name</span>
                  <span className="text-slate-700 font-medium">{createdKey.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Tier</span>
                  <span className="text-slate-700 font-medium capitalize">{createdKey.tier}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Scopes</span>
                  <span className="text-slate-700 font-medium">
                    {createdKey.scopes.includes('*') ? 'Full access' : createdKey.scopes.join(', ')}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Key Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Claude Code, My Script"
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent"
                />
                <p className="mt-2 text-sm text-slate-500">
                  Give your key a descriptive name to identify where it&apos;s used.
                </p>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg">
                <h4 className="text-sm font-medium text-slate-700 mb-2">What you can do with API keys:</h4>
                <ul className="text-sm text-slate-600 space-y-1">
                  <li>• Query your transactions and spending data</li>
                  <li>• Get account balances and analytics</li>
                  <li>• Update transaction categories and tags</li>
                  <li>• Access AI-generated insights</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
          {createdKey ? (
            <button
              onClick={handleClose}
              className="px-6 py-2.5 bg-slate-800 text-white rounded-lg hover:bg-slate-700 font-medium"
            >
              Done
            </button>
          ) : (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2.5 text-slate-600 hover:text-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!name.trim() || isCreating}
                className="px-6 py-2.5 bg-slate-800 text-white rounded-lg hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isCreating ? 'Creating...' : 'Create Key'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Main Settings Page Content
function SettingsPageContent() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { keys, isLoading, createKey, revokeKey } = useApiKeys();

  const activeKeys = keys.filter(k => k.is_active);
  const revokedKeys = keys.filter(k => !k.is_active);

  const handleCreateKey = async (name: string) => {
    return await createKey({ name });
  };

  return (
    <div className="min-h-screen bg-surface-base">
      {/* Left Sidebar */}
      <InstitutionSidebar onDataChange={refreshAllData} />

      {/* Main Content */}
      <div className="ml-72 p-8">
        {/* Back Link */}
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-700 mb-6"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Settings</h1>
          <p className="text-slate-500 mt-1">Manage your API keys and account settings</p>
        </div>

        {/* API Keys Section */}
        <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="p-6 border-b border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
                  <Key className="w-5 h-5" />
                  API Keys
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  Create API keys to access your financial data programmatically
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 text-white rounded-lg hover:bg-slate-700 font-medium"
              >
                <Plus className="w-4 h-4" />
                Create Key
              </button>
            </div>
          </div>

          <div className="p-6">
            {/* Info Box */}
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-3">
                <ExternalLink className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-blue-800">Use API keys with LLMs like Claude Code</p>
                  <p className="text-blue-700 mt-1">
                    Your API key gives access to endpoints at <code className="px-1.5 py-0.5 bg-blue-100 rounded">/api/v1/*</code>.
                    Use it with the <code className="px-1.5 py-0.5 bg-blue-100 rounded">X-API-Key</code> header or as a Bearer token.
                  </p>
                </div>
              </div>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin w-8 h-8 border-2 border-slate-200 border-t-slate-600 rounded-full" />
              </div>
            ) : activeKeys.length === 0 && revokedKeys.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Key className="w-8 h-8 text-slate-400" />
                </div>
                <h3 className="text-lg font-medium text-slate-700">No API keys yet</h3>
                <p className="text-slate-500 mt-1 mb-4">Create your first API key to get started</p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700"
                >
                  <Plus className="w-4 h-4" />
                  Create API Key
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Active Keys */}
                {activeKeys.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider">
                      Active Keys ({activeKeys.length})
                    </h3>
                    {activeKeys.map(key => (
                      <APIKeyCard
                        key={key.id}
                        apiKey={key}
                        onRevoke={revokeKey}
                      />
                    ))}
                  </div>
                )}

                {/* Revoked Keys */}
                {revokedKeys.length > 0 && (
                  <div className="space-y-3 mt-8">
                    <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                      Revoked Keys ({revokedKeys.length})
                    </h3>
                    {revokedKeys.map(key => (
                      <APIKeyCard
                        key={key.id}
                        apiKey={key}
                        onRevoke={revokeKey}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Example Usage Section */}
        <section className="mt-8 bg-white rounded-2xl border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Example Usage</h2>

          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Using curl</h4>
              <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-sm overflow-x-auto">
{`curl https://your-api.com/api/v1/summary \\
  -H "X-API-Key: fb_sk_your_key_here"`}
              </pre>
            </div>

            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Using JavaScript</h4>
              <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-sm overflow-x-auto">
{`const response = await fetch('https://your-api.com/api/v1/transactions', {
  headers: {
    'X-API-Key': 'fb_sk_your_key_here'
  }
});
const data = await response.json();`}
              </pre>
            </div>

            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Available Endpoints</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <code className="p-2 bg-slate-100 rounded">GET /api/v1/summary</code>
                <code className="p-2 bg-slate-100 rounded">GET /api/v1/transactions</code>
                <code className="p-2 bg-slate-100 rounded">GET /api/v1/accounts</code>
                <code className="p-2 bg-slate-100 rounded">GET /api/v1/spending/by-category</code>
                <code className="p-2 bg-slate-100 rounded">GET /api/v1/spending/trends</code>
                <code className="p-2 bg-slate-100 rounded">GET /api/v1/anomalies</code>
                <code className="p-2 bg-slate-100 rounded">GET /api/v1/insights</code>
                <code className="p-2 bg-slate-100 rounded">GET /api/v1/goals</code>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Create API Key Modal */}
      <CreateAPIKeyModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateKey}
      />
    </div>
  );
}

// Export with ProtectedRoute wrapper
export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <SettingsPageContent />
    </ProtectedRoute>
  );
}

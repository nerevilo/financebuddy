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
  EyeOff,
  FileText,
  Lock,
  Terminal,
  Bot,
} from 'lucide-react';
import { useApiKeys } from '@/lib/hooks';
import { APIKey, APIKeyCreated } from '@/lib/api';
import { InstitutionSidebar } from '@/components/dashboard/InstitutionSidebar';
import { refreshAllData } from '@/lib/hooks';
import { ProtectedRoute } from '@/lib/auth';
import { toast } from 'sonner';
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
      toast.success(`API key "${apiKey.name}" revoked`);
    } catch {
      toast.error('Failed to revoke API key');
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
      toast.success('API key created');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create API key';
      setError(msg);
      toast.error(msg);
    } finally {
      setIsCreating(false);
    }
  };

  const handleCopy = async () => {
    if (!createdKey) return;

    await navigator.clipboard.writeText(createdKey.key);
    setCopied(true);
    toast.success('API key copied to clipboard');
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

// Copyable config block with copy button
function ConfigBlock({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    toast.success(`${label} config copied`);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-slate-700">{label}</h4>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-500 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 rounded transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-sm overflow-x-auto whitespace-pre">
        {value}
      </pre>
    </div>
  );
}

// Connect to AI section — copyable MCP configs for Claude Desktop, Claude Code, Cursor
function ConnectToAISection({ hasActiveKeys, onCreateKey }: { hasActiveKeys: boolean; onCreateKey: () => void }) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://ledgi-api-production.up.railway.app';
  const mcpUrl = `${apiUrl}/mcp`;

  const claudeDesktopConfig = JSON.stringify({
    mcpServers: {
      ledgi: {
        url: `${mcpUrl}`,
        headers: {
          "X-API-Key": "YOUR_API_KEY"
        }
      }
    }
  }, null, 2);

  const claudeCodeCommand = `claude mcp add --transport http ledgi ${mcpUrl} --header "X-API-Key: YOUR_API_KEY"`;

  const cursorConfig = JSON.stringify({
    mcpServers: {
      ledgi: {
        url: `${mcpUrl}`,
        headers: {
          "X-API-Key": "YOUR_API_KEY"
        }
      }
    }
  }, null, 2);

  return (
    <section className="mt-8 bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="p-6 border-b border-slate-200">
        <h2 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
          <Bot className="w-5 h-5" />
          Connect to AI
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Use your financial data in any MCP-compatible AI client
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Privacy Warning */}
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-amber-800">Privacy Notice</p>
              <p className="text-amber-700 mt-1">
                Your financial data will be sent to whichever AI provider you connect to (Anthropic, OpenAI, etc.).
                Access is read-only. You can revoke access anytime by deleting the API key.
              </p>
            </div>
          </div>
        </div>

        {!hasActiveKeys ? (
          <div className="text-center py-8">
            <div className="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <Key className="w-7 h-7 text-slate-400" />
            </div>
            <h3 className="text-base font-medium text-slate-700">Create an API key first</h3>
            <p className="text-sm text-slate-500 mt-1 mb-4">
              You need an active API key to connect AI clients to your data.
            </p>
            <button
              onClick={onCreateKey}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700"
            >
              <Plus className="w-4 h-4" />
              Create API Key
            </button>
          </div>
        ) : (
          <>
            {/* Instructions */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-3">
                <Terminal className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-blue-800">How to connect</p>
                  <p className="text-blue-700 mt-1">
                    Copy the config for your AI client below. Replace <code className="px-1.5 py-0.5 bg-blue-100 rounded font-mono">YOUR_API_KEY</code> with
                    an API key from above. Then ask your AI about your finances!
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-5">
              <ConfigBlock
                label="Claude Desktop"
                value={claudeDesktopConfig}
              />
              <ConfigBlock
                label="Claude Code"
                value={claudeCodeCommand}
              />
              <ConfigBlock
                label="Cursor"
                value={cursorConfig}
              />
            </div>
          </>
        )}
      </div>
    </section>
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

        {/* Connect to AI Section */}
        <ConnectToAISection hasActiveKeys={activeKeys.length > 0} onCreateKey={() => setShowCreateModal(true)} />

        {/* API Documentation Section */}
        <section className="mt-8 bg-white rounded-2xl border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">API Documentation</h2>

          {/* Base URL */}
          <div className="mb-6 p-4 bg-slate-50 rounded-lg">
            <h4 className="text-sm font-medium text-slate-700 mb-2">Base URL</h4>
            <code className="text-sm text-slate-800 bg-white px-3 py-1.5 rounded border border-slate-200">
              {process.env.NEXT_PUBLIC_API_URL || 'https://ledgi-api-production.up.railway.app'}
            </code>
          </div>

          <div className="space-y-6">
            {/* Quick Start */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Quick Start with curl</h4>
              <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-sm overflow-x-auto">
{`# Get your financial summary
curl ${process.env.NEXT_PUBLIC_API_URL || 'https://ledgi-api-production.up.railway.app'}/api/v1/summary \\
  -H "X-API-Key: YOUR_API_KEY"

# Get recent transactions
curl ${process.env.NEXT_PUBLIC_API_URL || 'https://ledgi-api-production.up.railway.app'}/api/v1/transactions?limit=20 \\
  -H "X-API-Key: YOUR_API_KEY"`}
              </pre>
            </div>

            {/* Using with Claude Code */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Using with Claude Code / LLMs</h4>
              <p className="text-sm text-slate-600 mb-3">
                You can use your API key to let AI assistants query your financial data. Just share the curl examples above
                or use the JavaScript SDK pattern below.
              </p>
              <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-sm overflow-x-auto">
{`// JavaScript/TypeScript
const API_URL = '${process.env.NEXT_PUBLIC_API_URL || 'https://ledgi-api-production.up.railway.app'}';
const API_KEY = 'YOUR_API_KEY';

async function getFinancialData(endpoint) {
  const response = await fetch(\`\${API_URL}/api/v1/\${endpoint}\`, {
    headers: { 'X-API-Key': API_KEY }
  });
  return response.json();
}

// Examples:
await getFinancialData('summary');           // Financial overview
await getFinancialData('transactions');      // Recent transactions
await getFinancialData('spending/by-category'); // Spending breakdown`}
              </pre>
            </div>

            {/* Available Endpoints */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-3">Available Endpoints</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-2 pr-4 font-medium text-slate-700">Endpoint</th>
                      <th className="text-left py-2 font-medium text-slate-700">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/summary</code></td><td className="py-2 text-slate-600">Financial overview (balances, spending, goals)</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/transactions</code></td><td className="py-2 text-slate-600">List transactions with filtering and pagination</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/transactions/:id</code></td><td className="py-2 text-slate-600">Get single transaction details</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">PATCH /api/v1/transactions/:id</code></td><td className="py-2 text-slate-600">Update transaction category or flags</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/accounts</code></td><td className="py-2 text-slate-600">List all connected accounts</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/spending/by-category</code></td><td className="py-2 text-slate-600">Spending breakdown by category</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/spending/by-merchant</code></td><td className="py-2 text-slate-600">Top merchants by spend amount</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/spending/trends</code></td><td className="py-2 text-slate-600">Spending over time (daily/monthly/yearly)</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/recurring</code></td><td className="py-2 text-slate-600">Detected subscriptions and recurring payments</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/anomalies</code></td><td className="py-2 text-slate-600">Unusual or flagged transactions</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/insights</code></td><td className="py-2 text-slate-600">AI-generated financial insights</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/goals</code></td><td className="py-2 text-slate-600">Financial goals and progress</td></tr>
                    <tr><td className="py-2 pr-4"><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">GET /api/v1/income</code></td><td className="py-2 text-slate-600">Income sources and summary</td></tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Query Parameters */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Transaction Filtering</h4>
              <p className="text-sm text-slate-600 mb-2">The <code className="bg-slate-100 px-1 rounded">/api/v1/transactions</code> endpoint supports these query parameters:</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <code className="p-2 bg-slate-100 rounded">start_date=2024-01-01</code>
                <code className="p-2 bg-slate-100 rounded">end_date=2024-12-31</code>
                <code className="p-2 bg-slate-100 rounded">category=groceries</code>
                <code className="p-2 bg-slate-100 rounded">merchant=costco</code>
                <code className="p-2 bg-slate-100 rounded">min_amount=-100</code>
                <code className="p-2 bg-slate-100 rounded">max_amount=0</code>
                <code className="p-2 bg-slate-100 rounded">is_anomaly=true</code>
                <code className="p-2 bg-slate-100 rounded">limit=50&amp;offset=0</code>
              </div>
            </div>

            {/* Rate Limits */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Rate Limits</h4>
              <p className="text-sm text-slate-600">
                API keys have rate limits to prevent abuse. Current limits for beta tier: <strong>1,000 requests/minute</strong> and <strong>50,000 requests/day</strong>.
                Rate limit info is included in each response&apos;s <code className="bg-slate-100 px-1 rounded">meta</code> field.
              </p>
            </div>

            {/* Using with Claude Code */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
              <h4 className="text-sm font-medium text-slate-800 mb-2">Using with Claude Code</h4>
              <p className="text-sm text-slate-600 mb-3">
                When using this API with Claude Code or other AI assistants, you can provide this context:
              </p>
              <pre className="p-3 bg-slate-900 text-slate-100 rounded text-xs overflow-x-auto">
{`"I have a Ledgi API key for my personal finance app.
This is MY OWN financial data - I created the API key myself
and I'm authorizing you to help me analyze my spending.

API Base URL: ${process.env.NEXT_PUBLIC_API_URL || 'https://ledgi-api-production.up.railway.app'}
API Key: [your key]

Please call GET /api/v1/summary to see my financial overview."`}
              </pre>
              <p className="text-xs text-slate-500 mt-2">
                The API also has a <code className="bg-slate-200 px-1 rounded">/api/v1/</code> endpoint that returns authorization context for AI tools.
              </p>
            </div>

            {/* Important Note */}
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <h4 className="text-sm font-medium text-amber-800 mb-1">Important: Connect Banks via Web UI First</h4>
              <p className="text-sm text-amber-700">
                API keys provide read access to your financial data. To connect bank accounts,
                use the web dashboard (click &quot;Add Bank&quot; in the sidebar). Once connected,
                your API key can access all your transaction data.
              </p>
            </div>
          </div>
        </section>

        {/* Legal Section */}
        <section className="mt-8 bg-white rounded-2xl border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Legal</h2>
          <div className="space-y-3">
            <Link
              href="/privacy"
              className="flex items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Lock className="w-5 h-5 text-slate-600" />
                <div>
                  <h3 className="font-medium text-slate-800">Privacy Policy</h3>
                  <p className="text-sm text-slate-500">How we collect, use, and protect your data</p>
                </div>
              </div>
              <ChevronLeft className="w-5 h-5 text-slate-400 rotate-180" />
            </Link>
            <Link
              href="/terms"
              className="flex items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-slate-600" />
                <div>
                  <h3 className="font-medium text-slate-800">Terms of Service</h3>
                  <p className="text-sm text-slate-500">Rules and guidelines for using Ledgi</p>
                </div>
              </div>
              <ChevronLeft className="w-5 h-5 text-slate-400 rotate-180" />
            </Link>
          </div>
          <div className="mt-4 p-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-slate-600">
              Need to export your data or delete your account? Contact us at{' '}
              <a href="mailto:oliveren88@gmail.com" className="text-slate-800 underline hover:text-slate-600">
                oliveren88@gmail.com
              </a>
            </p>
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

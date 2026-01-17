'use client';

import { MessageSquare, Loader2 } from 'lucide-react';
import type { ConversationSummary } from '@/lib/api';

interface ConversationListProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  isLoading?: boolean;
}

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  isLoading,
}: ConversationListProps) {
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <Loader2 className="w-6 h-6 text-slate-400 animate-spin" />
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mb-3">
          <MessageSquare className="w-6 h-6 text-slate-400" />
        </div>
        <p className="text-sm text-slate-500">No conversations yet</p>
        <p className="text-xs text-slate-400 mt-1">
          Start a new chat to begin
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-2 space-y-1">
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            onClick={() => onSelect(conversation.id)}
            className={`
              w-full text-left px-3 py-2.5 rounded-lg
              transition-colors
              ${activeId === conversation.id
                ? 'bg-slate-100'
                : 'hover:bg-slate-50'
              }
            `}
          >
            <div className="flex items-start gap-2">
              <MessageSquare className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="font-medium text-sm text-slate-800 truncate">
                  {conversation.title || 'New conversation'}
                </div>
                {conversation.last_message_preview && (
                  <div className="text-xs text-slate-500 truncate mt-0.5">
                    {conversation.last_message_preview}
                  </div>
                )}
                <div className="text-[10px] text-slate-400 mt-1">
                  {formatRelativeTime(conversation.updated_at)}
                  {conversation.message_count > 0 && (
                    <span> &middot; {conversation.message_count} messages</span>
                  )}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

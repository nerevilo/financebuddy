'use client';

import { X, MessageSquarePlus, History, ChevronLeft } from 'lucide-react';

interface ChatHeaderProps {
  onClose: () => void;
  onNewChat: () => void;
  onToggleHistory: () => void;
  showingHistory: boolean;
  conversationTitle?: string | null;
}

export function ChatHeader({
  onClose,
  onNewChat,
  onToggleHistory,
  showingHistory,
  conversationTitle,
}: ChatHeaderProps) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
      <div className="flex items-center gap-2">
        {showingHistory ? (
          <button
            onClick={onToggleHistory}
            className="p-1.5 hover:bg-slate-200 rounded-lg transition-colors"
            aria-label="Back to chat"
          >
            <ChevronLeft className="w-5 h-5 text-slate-600" />
          </button>
        ) : null}
        <div>
          <h2 className="font-semibold text-slate-900">
            {showingHistory ? 'Chat History' : 'Ledgi'}
          </h2>
          {!showingHistory && conversationTitle && (
            <p className="text-xs text-slate-500 truncate max-w-[180px]">
              {conversationTitle}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1">
        {!showingHistory && (
          <>
            <button
              onClick={onToggleHistory}
              className="p-2 hover:bg-slate-200 rounded-lg transition-colors"
              aria-label="View chat history"
              title="Chat history"
            >
              <History className="w-5 h-5 text-slate-600" />
            </button>
            <button
              onClick={onNewChat}
              className="p-2 hover:bg-slate-200 rounded-lg transition-colors"
              aria-label="New chat"
              title="New chat"
            >
              <MessageSquarePlus className="w-5 h-5 text-slate-600" />
            </button>
          </>
        )}
        <button
          onClick={onClose}
          className="p-2 hover:bg-slate-200 rounded-lg transition-colors"
          aria-label="Close chat"
        >
          <X className="w-5 h-5 text-slate-600" />
        </button>
      </div>
    </div>
  );
}

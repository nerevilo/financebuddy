'use client';

import { MessageCircle } from 'lucide-react';

interface ChatButtonProps {
  onClick: () => void;
  hasUnread?: boolean;
}

export function ChatButton({ onClick, hasUnread }: ChatButtonProps) {
  return (
    <button
      onClick={onClick}
      className="
        fixed bottom-6 right-6 z-30
        w-14 h-14 rounded-full
        bg-slate-900 text-white shadow-lg
        flex items-center justify-center
        hover:bg-slate-800 hover:scale-105
        active:scale-95
        transition-all duration-200
        lg:hidden
      "
      aria-label="Open chat assistant"
    >
      <MessageCircle className="w-6 h-6" />

      {/* Unread indicator */}
      {hasUnread && (
        <span className="absolute top-0 right-0 w-3 h-3 bg-rose-500 rounded-full border-2 border-white" />
      )}
    </button>
  );
}

'use client';

import { MessageBubble } from './MessageBubble';
import { Loader2, Sparkles } from 'lucide-react';
import type { ChatMessage } from '@/lib/api';

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
          <Sparkles className="w-8 h-8 text-slate-400" />
        </div>
        <h3 className="font-semibold text-slate-800 mb-2">
          Hi! I&apos;m Ledgi
        </h3>
        <p className="text-sm text-slate-500 max-w-xs">
          Ask me about your spending, search transactions, check your budget pace, or manage your financial goals.
        </p>
        <div className="mt-6 space-y-2 w-full max-w-xs">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
            Try asking
          </p>
          <div className="space-y-2">
            {[
              "How much did I spend on dining this month?",
              "Am I on track with my budget?",
              "Show me my recent Amazon purchases",
            ].map((suggestion, idx) => (
              <div
                key={idx}
                className="text-sm text-slate-600 bg-slate-50 rounded-lg px-3 py-2 border border-slate-100"
              >
                {suggestion}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-1">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex items-center gap-2 px-4 py-3">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-sm text-slate-500">Thinking...</span>
        </div>
      )}
    </div>
  );
}

'use client';

import { ToolResultCard } from './ToolResultCard';
import type { ChatMessage } from '@/lib/api';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`
          max-w-[85%] rounded-2xl px-4 py-3
          ${isUser
            ? 'bg-slate-900 text-white rounded-br-md'
            : 'bg-slate-100 text-slate-800 rounded-bl-md'
          }
        `}
      >
        {/* Message content */}
        <div className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </div>

        {/* Tool results (for assistant messages) */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.tool_calls.map((tool) => (
              <ToolResultCard key={tool.id} toolCall={tool} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div
          className={`
            text-[10px] mt-2 opacity-70
            ${isUser ? 'text-slate-300' : 'text-slate-400'}
          `}
        >
          {new Date(message.created_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  );
}

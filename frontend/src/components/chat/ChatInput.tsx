'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void | Promise<void>;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [message]);

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    const trimmed = message.trim();
    if (trimmed && !disabled && !isSubmitting) {
      setIsSubmitting(true);
      setMessage('');
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
      try {
        await onSend(trimmed);
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-slate-200 bg-white p-3">
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your spending..."
            disabled={disabled}
            rows={1}
            className="
              w-full resize-none rounded-xl border border-slate-200
              bg-slate-50 px-4 py-2.5 text-sm
              placeholder:text-slate-400
              focus:outline-none focus:ring-2 focus:ring-slate-300 focus:border-transparent
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-all
            "
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={disabled || isSubmitting || !message.trim()}
          className="
            p-2.5 rounded-xl
            bg-slate-900 text-white
            hover:bg-slate-800
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors
            flex-shrink-0
          "
          aria-label="Send message"
        >
          {disabled || isSubmitting ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>
      <p className="text-[10px] text-slate-400 mt-2 text-center">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}

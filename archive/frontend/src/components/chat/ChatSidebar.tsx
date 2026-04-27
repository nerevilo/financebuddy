'use client';

import { useState, useRef, useEffect } from 'react';
import { X, MessageSquarePlus, History, ChevronLeft, AlertCircle } from 'lucide-react';
import { useChat, useConversations } from '@/lib/hooks';
import { ChatHeader } from './ChatHeader';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { ConversationList } from './ConversationList';

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatSidebar({ isOpen, onClose }: ChatSidebarProps) {
  const [showHistory, setShowHistory] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const {
    conversations,
    activeConversationId,
    setActiveConversation,
    createConversation,
    isLoading: conversationsLoading,
  } = useConversations();

  const {
    messages,
    isLoading: chatLoading,
    isSending,
    error: chatError,
    sendMessage,
  } = useChat(activeConversationId);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Clear error when conversation changes
  useEffect(() => {
    setSendError(null);
  }, [activeConversationId]);

  const handleSendMessage = async (text: string) => {
    setSendError(null);
    try {
      if (!activeConversationId) {
        // Create new conversation first
        const newConv = await createConversation();
        if (newConv) {
          const result = await sendMessage(newConv.id, text);
          if (!result) {
            setSendError('Failed to send message. Please try again.');
          }
        } else {
          setSendError('Failed to create conversation. Please try again.');
        }
      } else {
        const result = await sendMessage(activeConversationId, text);
        if (!result) {
          setSendError('Failed to send message. Please try again.');
        }
      }
    } catch (err) {
      console.error('Chat error:', err);
      setSendError('An unexpected error occurred. Please try again.');
    }
  };

  const handleNewChat = async () => {
    const newConv = await createConversation();
    if (newConv) {
      setActiveConversation(newConv.id);
    }
    setShowHistory(false);
  };

  const handleSelectConversation = (id: string) => {
    setActiveConversation(id);
    setShowHistory(false);
  };

  // Find active conversation title
  const activeConversation = conversations.find(c => c.id === activeConversationId);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop overlay for mobile */}
      <div
        className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
        onClick={onClose}
      />

      {/* Sidebar */}
      <aside
        className={`
          fixed right-0 top-0 h-screen z-50
          w-full max-w-md lg:w-96
          bg-white border-l border-slate-200 shadow-2xl
          flex flex-col
          transform transition-transform duration-300 ease-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {/* Header */}
        <ChatHeader
          onClose={onClose}
          onNewChat={handleNewChat}
          onToggleHistory={() => setShowHistory(!showHistory)}
          showingHistory={showHistory}
          conversationTitle={activeConversation?.title}
        />

        {/* Content */}
        {showHistory ? (
          <ConversationList
            conversations={conversations}
            activeId={activeConversationId}
            onSelect={handleSelectConversation}
            isLoading={conversationsLoading}
          />
        ) : (
          <>
            {/* Messages */}
            <MessageList
              messages={messages}
              isLoading={isSending}
            />
            <div ref={messagesEndRef} />

            {/* Error display */}
            {(sendError || chatError) && (
              <div className="px-3 py-2 bg-rose-50 border-t border-rose-200">
                <div className="flex items-center gap-2 text-sm text-rose-600">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{sendError || 'Failed to load chat. Please try again.'}</span>
                </div>
              </div>
            )}

            {/* Input */}
            <ChatInput
              onSend={handleSendMessage}
              disabled={isSending}
            />
          </>
        )}
      </aside>
    </>
  );
}

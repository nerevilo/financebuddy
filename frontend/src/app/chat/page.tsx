'use client';

import { useState, useRef, useEffect } from 'react';
import { MessageSquarePlus, ChevronLeft, History } from 'lucide-react';
import { useChat, useConversations } from '@/lib/hooks';
import { MessageList } from '@/components/chat/MessageList';
import { MessageBubble } from '@/components/chat/MessageBubble';
import { ChatInput } from '@/components/chat/ChatInput';
import { ConversationList } from '@/components/chat/ConversationList';
import { InstitutionSidebar } from '@/components/dashboard/InstitutionSidebar';
import { refreshAllData } from '@/lib/hooks';
import { ProtectedRoute } from '@/lib/auth';
import Link from 'next/link';

function ChatPageContent() {
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

  const activeConversation = conversations.find(c => c.id === activeConversationId);

  return (
    <div className="min-h-screen bg-surface-base">
      {/* Left Sidebar */}
      <InstitutionSidebar onDataChange={refreshAllData} />

      {/* Main Content */}
      <div className="ml-72 flex min-h-screen">
        {/* Conversation History Panel */}
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
          {/* History Header */}
          <div className="p-4 border-b border-slate-200">
            <button
              onClick={handleNewChat}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors"
            >
              <MessageSquarePlus className="w-4 h-4" />
              <span className="font-medium">New Chat</span>
            </button>
          </div>

          {/* Conversation List */}
          <div className="flex-1 overflow-hidden">
            <div className="p-3 border-b border-slate-100">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Recent Conversations
              </h3>
            </div>
            <ConversationList
              conversations={conversations}
              activeId={activeConversationId}
              onSelect={handleSelectConversation}
              isLoading={conversationsLoading}
            />
          </div>
        </aside>

        {/* Chat Area */}
        <main className="flex-1 flex flex-col bg-slate-50">
          {/* Chat Header */}
          <header className="bg-white border-b border-slate-200 px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-500 mb-1">
                  <Link href="/" className="hover:text-slate-700">Dashboard</Link>
                  <span>/</span>
                  <span className="text-slate-900">Finance Buddy Chat</span>
                </div>
                <h1 className="text-xl font-bold tracking-tight text-slate-900">
                  {activeConversation?.title || 'New Conversation'}
                </h1>
              </div>
              <Link
                href="/"
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition"
              >
                <ChevronLeft className="w-4 h-4" />
                Back to Dashboard
              </Link>
            </div>
          </header>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto py-6">
              {messages.length === 0 && !isSending ? (
                <WelcomeScreen />
              ) : (
                <div className="space-y-1 px-4">
                  {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                  ))}
                  {isSending && (
                    <div className="flex items-center gap-2 px-4 py-3">
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                      <span className="text-sm text-slate-500">Thinking...</span>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </div>

          {/* Error Display */}
          {(sendError || chatError) && (
            <div className="px-6 py-3 bg-rose-50 border-t border-rose-200">
              <div className="max-w-3xl mx-auto text-sm text-rose-600">
                {sendError || 'Failed to load chat. Please try again.'}
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="border-t border-slate-200 bg-white p-4">
            <div className="max-w-3xl mx-auto">
              <ChatInput
                onSend={handleSendMessage}
                disabled={isSending}
              />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function WelcomeScreen() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-6">
        <svg className="w-10 h-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      </div>
      <h2 className="text-2xl font-bold text-slate-900 mb-3">
        Hi! I'm Finance Buddy
      </h2>
      <p className="text-slate-600 max-w-md mb-8">
        Your AI-powered financial assistant. I can help you understand your spending,
        track transactions, check your budget, and manage your financial goals.
      </p>

      <div className="grid gap-3 w-full max-w-md">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
          Try asking me
        </p>
        {[
          "How much did I spend on dining this month?",
          "What are my top spending categories?",
          "Am I on track with my budget?",
          "Show me unusual transactions",
        ].map((suggestion, idx) => (
          <div
            key={idx}
            className="text-left text-sm text-slate-700 bg-white rounded-xl px-4 py-3 border border-slate-200 hover:border-slate-300 hover:shadow-sm transition cursor-default"
          >
            {suggestion}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatPageContent />
    </ProtectedRoute>
  );
}

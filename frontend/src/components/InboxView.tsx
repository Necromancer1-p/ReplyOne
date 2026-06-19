import React, { useState, useEffect, useRef } from 'react';
import { api } from '../utils/api';
import { 
  MessageSquare, Bot, AlertCircle, CheckCircle, 
  Send, Sparkles, RefreshCw, Smartphone, Globe, Instagram, Loader2
} from 'lucide-react';

interface Customer {
  id: number;
  display_name: string;
  avatar_url?: string;
  phone?: string;
  external_user_id: string;
}

interface Conversation {
  id: number;
  customer_id: number;
  channel_id: number;
  channel: string;
  status: string;
  assigned_agent_id?: number;
  ai_active: boolean;
  last_message_at: string;
  customer: Customer;
  last_message?: string;
}

interface Message {
  id: number;
  conversation_id: number;
  direction: string;
  sender_type: string;
  sender_user_id?: number;
  content: string;
  attachment_url?: string;
  external_message_id?: string;
  delivery_status?: string;
  created_at: string;
}

export const InboxView: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('open');
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Poll conversations & active messages
  const fetchConversations = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await api.get<Conversation[]>(`/dashboard/conversations?status_filter=${statusFilter}`);
      setConversations(data);
      // Sync active conversation
      if (activeConv) {
        const updated = data.find(c => c.id === activeConv.id);
        if (updated) setActiveConv(updated);
      }
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const fetchMessages = async (convId: number, silent = false) => {
    if (!silent) setMessagesLoading(true);
    try {
      const data = await api.get<Message[]>(`/dashboard/conversations/${convId}/messages`);
      setMessages(data);
    } catch (err) {
      console.error('Failed to fetch messages:', err);
    } finally {
      if (!silent) setMessagesLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [statusFilter]);

  // Periodic polling for real-time inbox feel
  useEffect(() => {
    const interval = setInterval(() => {
      fetchConversations(true);
      if (activeConv) {
        fetchMessages(activeConv.id, true);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [activeConv, statusFilter]);

  useEffect(() => {
    if (activeConv) {
      fetchMessages(activeConv.id);
    }
  }, [activeConv?.id]);

  useEffect(() => {
    // Scroll to bottom on new messages
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeConv || sending) return;

    setSending(true);
    const text = newMessage;
    setNewMessage('');

    try {
      await api.post(`/dashboard/conversations/${activeConv.id}/messages`, {
        content: text
      });
      // Instant reload
      await fetchMessages(activeConv.id, true);
      await fetchConversations(true);
    } catch (err) {
      console.error('Failed to send message:', err);
      setNewMessage(text); // Restore text on failure
    } finally {
      setSending(false);
    }
  };

  const handleToggleAutopilot = async (active: boolean) => {
    if (!activeConv) return;
    try {
      const updated = await api.put<Conversation>(`/dashboard/conversations/${activeConv.id}`, {
        ai_active: active
      });
      setActiveConv(updated);
      fetchConversations(true);
    } catch (err) {
      console.error('Failed to toggle autopilot:', err);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!activeConv) return;
    try {
      await api.put(`/dashboard/conversations/${activeConv.id}`, {
        status: newStatus
      });
      setActiveConv(null);
      setMessages([]);
      fetchConversations();
    } catch (err) {
      console.error('Failed to change status:', err);
    }
  };

  const selectQuickReply = (text: string) => {
    setNewMessage(text);
  };

  const getChannelIcon = (type: string) => {
    switch (type) {
      case 'whatsapp':
        return <Smartphone size={14} className="text-successGreen" />;
      case 'instagram':
        return <Instagram size={14} className="text-rose-400" />;
      default:
        return <Globe size={14} className="text-electricBlue" />;
    }
  };

  return (
    <div className="flex h-[calc(100vh-64px)] border-t border-darkBorder overflow-hidden bg-deepNavy">
      {/* 1. Conversations Column */}
      <div className="w-1/3 md:w-80 border-r border-darkBorder flex flex-col bg-darkSidebarBg">
        {/* Header/Filters */}
        <div className="p-md border-b border-darkBorder space-y-md">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-md text-cloudWhite flex items-center gap-xs">
              <MessageSquare size={18} className="text-electricBlue" />
              Inbox
            </h3>
            <button 
              onClick={() => fetchConversations()}
              className="p-xs text-darkSecondaryText hover:text-cloudWhite bg-darkBorder/40 rounded-default cursor-pointer border-none"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
          {/* Status Segment */}
          <div className="flex bg-deepNavy/80 p-[2px] rounded-large text-xs font-semibold">
            {['open', 'pending', 'escalated', 'resolved'].map((st) => (
              <button
                key={st}
                onClick={() => {
                  setStatusFilter(st);
                  setActiveConv(null);
                  setMessages([]);
                }}
                className={`flex-1 py-xs rounded-default capitalize transition-all cursor-pointer ${
                  statusFilter === st 
                    ? 'bg-darkCardBg text-cloudWhite border border-darkBorder' 
                    : 'text-darkSecondaryText hover:text-cloudWhite border border-transparent'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto">
          {loading && conversations.length === 0 ? (
            <div className="p-lg text-center space-y-xs">
              <Loader2 className="animate-spin mx-auto text-indigoBrand" size={24} />
              <p className="text-xs text-darkSecondaryText">Loading chats...</p>
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-lg text-center text-darkSecondaryText space-y-xs">
              <MessageSquare size={28} className="mx-auto text-softSlate" />
              <p className="text-xs">No {statusFilter} chats found.</p>
            </div>
          ) : (
            conversations.map((conv) => {
              const active = activeConv?.id === conv.id;
              return (
                <button
                  key={conv.id}
                  onClick={() => setActiveConv(conv)}
                  className={`w-full text-left p-md border-b border-darkBorder/40 flex items-start gap-md transition-all hover:bg-darkCardBg/35 ${
                    active ? 'bg-darkCardBg/80 border-l-4 border-l-electricBlue border-b-darkBorder' : 'bg-transparent'
                  }`}
                >
                  <div className="w-10 h-10 rounded-full bg-darkBorder/60 text-electricBlue font-bold flex items-center justify-center text-sm relative shrink-0">
                    {conv.customer.display_name.charAt(0).toUpperCase()}
                    <div className="absolute -bottom-1 -right-1 bg-darkSidebarBg p-[2px] rounded-full border border-darkBorder">
                      {getChannelIcon(conv.channel)}
                    </div>
                  </div>
                  <div className="flex-1 min-w-0 space-y-xs">
                    <div className="flex justify-between items-baseline">
                      <h4 className="font-semibold text-sm truncate text-cloudWhite">{conv.customer.display_name}</h4>
                      <span className="text-[10px] text-darkSecondaryText font-mono">
                        {new Date(conv.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-xs text-darkSecondaryText truncate">{conv.last_message || '[No message history]'}</p>
                    <div className="flex items-center justify-between mt-xs">
                      {conv.ai_active && (
                        <span className="bg-cyberTeal/15 text-cyberTeal text-[9px] px-sm py-[1px] rounded-pill border border-cyberTeal/20 flex items-center gap-[2px]">
                          <Bot size={10} /> Autopilot
                        </span>
                      )}
                      {conv.status === 'escalated' && (
                        <span className="bg-alertRed/15 text-alertRed text-[9px] px-sm py-[1px] rounded-pill border border-alertRed/20 flex items-center gap-[2px]">
                          <AlertCircle size={10} /> Escalated
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* 2. Messages Column */}
      <div className="flex-1 flex flex-col bg-deepNavy">
        {activeConv ? (
          <>
            {/* Active Header */}
            <div className="h-16 px-lg border-b border-darkBorder flex justify-between items-center bg-darkSidebarBg">
              <div className="flex items-center gap-md">
                <div className="w-9 h-9 rounded-full bg-indigoBrand/20 text-indigoBrand font-bold flex items-center justify-center text-sm">
                  {activeConv.customer.display_name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h4 className="font-bold text-sm text-cloudWhite">{activeConv.customer.display_name}</h4>
                  <p className="text-[10px] text-darkSecondaryText flex items-center gap-xs">
                    {getChannelIcon(activeConv.channel)}
                    <span className="capitalize">{activeConv.channel} channel</span>
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-sm">
                <button
                  onClick={() => handleStatusChange(activeConv.status === 'resolved' ? 'open' : 'resolved')}
                  className={`px-md py-xs rounded-default text-xs font-semibold flex items-center gap-xs cursor-pointer border ${
                    activeConv.status === 'resolved'
                      ? 'bg-transparent border-darkBorder text-darkSecondaryText hover:text-cloudWhite'
                      : 'bg-successGreen/20 border-successGreen/30 text-successGreen hover:bg-successGreen/30'
                  }`}
                >
                  <CheckCircle size={14} />
                  {activeConv.status === 'resolved' ? 'Reopen Chat' : 'Resolve Ticket'}
                </button>
              </div>
            </div>

            {/* Message Area */}
            <div className="flex-1 p-lg overflow-y-auto space-y-md">
              {messagesLoading && messages.length === 0 ? (
                <div className="text-center py-lg">
                  <Loader2 className="animate-spin mx-auto text-indigoBrand" size={24} />
                </div>
              ) : (
                messages.map((msg) => {
                  const isInbound = msg.direction === 'inbound';
                  return (
                    <div
                      key={msg.id}
                      className={`flex ${isInbound ? 'justify-start' : 'justify-end'}`}
                    >
                      <div className={`max-w-[70%] space-y-[2px]`}>
                        <div className={`px-md py-md-sm rounded-large text-sm leading-relaxed ${
                          isInbound
                            ? 'bg-darkCardBg text-cloudWhite rounded-tl-sharp border border-darkBorder'
                            : msg.sender_type === 'ai'
                              ? 'bg-cyberTeal/15 text-cloudWhite border border-cyberTeal/30 rounded-tr-sharp'
                              : 'bg-indigoBrand text-white rounded-tr-sharp'
                        }`}>
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-darkSecondaryText font-mono px-xs">
                          <span>
                            {msg.sender_type === 'ai' ? '🤖 AI Autopilot' : msg.sender_type === 'agent' ? '👤 Agent' : 'Customer'}
                          </span>
                          <span>
                            {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Composer / Quick Replies */}
            <div className="p-md bg-darkSidebarBg border-t border-darkBorder space-y-md">
              {/* Quick Reply Badges */}
              <div className="flex gap-sm overflow-x-auto pb-xs scrollbar-thin">
                <span className="text-[10px] uppercase font-mono text-darkSecondaryText shrink-0 flex items-center">Quick Reply:</span>
                {[
                  'Hello! How can I help you today?',
                  'Sure, shipping takes 3-5 business days.',
                  'We accept major credit cards and UPI transactions.',
                  'Can you please provide your Order ID?'
                ].map((rep, idx) => (
                  <button
                    key={idx}
                    onClick={() => selectQuickReply(rep)}
                    className="shrink-0 bg-darkCardBg hover:bg-darkBorder/40 border border-darkBorder px-sm py-xs rounded-pill text-[11px] text-darkSecondaryText hover:text-cloudWhite transition-all cursor-pointer"
                  >
                    {rep}
                  </button>
                ))}
              </div>

              {/* Chat Composer */}
              <form onSubmit={handleSendMessage} className="flex gap-md">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder={activeConv.ai_active ? "Type message... (Sending turns off AI Autopilot)" : "Type response to customer..."}
                  className="flex-1 px-md py-md-sm bg-deepNavy border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue text-sm"
                />
                <button
                  type="submit"
                  disabled={!newMessage.trim() || sending}
                  className="px-md bg-gradient-to-r from-electricBlue to-indigoBrand text-white rounded-default font-semibold shadow hover:from-electricBlue/95 hover:to-indigoBrand/95 active:scale-[0.98] transition-all flex items-center justify-center gap-xs disabled:opacity-30 disabled:pointer-events-none cursor-pointer border-none"
                >
                  {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-darkSecondaryText space-y-sm">
            <MessageSquare size={48} className="text-softSlate" />
            <div className="text-center">
              <h3 className="font-bold text-cloudWhite">No Conversation Selected</h3>
              <p className="text-xs">Pick a chat from the left side to review message logs and respond.</p>
            </div>
          </div>
        )}
      </div>

      {/* 3. Details Column */}
      {activeConv && (
        <div className="w-60 border-l border-darkBorder bg-darkSidebarBg p-md flex flex-col justify-between overflow-y-auto">
          <div className="space-y-lg">
            {/* Profile Summary */}
            <div className="text-center space-y-sm">
              <div className="w-16 h-16 rounded-full bg-indigoBrand/10 text-indigoBrand text-2xl font-bold flex items-center justify-center mx-auto border border-indigoBrand/20">
                {activeConv.customer.display_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <h4 className="font-bold text-sm text-cloudWhite">{activeConv.customer.display_name}</h4>
                <span className="text-xs text-darkSecondaryText font-mono">ID: {activeConv.customer.external_user_id}</span>
              </div>
            </div>

            <hr className="border-darkBorder" />

            {/* Customer metadata */}
            <div className="space-y-md">
              <h5 className="text-[10px] font-bold text-darkSecondaryText uppercase tracking-wider">Customer Details</h5>
              <div className="space-y-sm text-xs">
                {activeConv.customer.phone && (
                  <div className="flex justify-between">
                    <span className="text-darkSecondaryText">Phone:</span>
                    <span className="text-cloudWhite font-mono">{activeConv.customer.phone}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-darkSecondaryText">Channel:</span>
                  <span className="text-cloudWhite capitalize">{activeConv.channel}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-darkSecondaryText">Last Activity:</span>
                  <span className="text-cloudWhite">
                    {new Date(activeConv.last_message_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <hr className="border-darkBorder" />

            {/* AI Control Center */}
            <div className="space-y-md p-md bg-darkCardBg/50 border border-darkBorder rounded-large">
              <h5 className="text-[10px] font-bold text-cyberTeal uppercase tracking-wider flex items-center gap-xs">
                <Sparkles size={12} />
                AI Control Center
              </h5>
              
              <div className="space-y-sm">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-darkSecondaryText">Autopilot Mode:</span>
                  <span className={`font-semibold ${activeConv.ai_active ? 'text-cyberTeal' : 'text-signalAmber'}`}>
                    {activeConv.ai_active ? 'ON' : 'OFF'}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() => handleToggleAutopilot(!activeConv.ai_active)}
                  className={`w-full py-xs px-sm rounded-default text-xs font-semibold flex items-center justify-center gap-xs cursor-pointer border ${
                    activeConv.ai_active
                      ? 'bg-transparent border-signalAmber/30 text-signalAmber hover:bg-signalAmber/10'
                      : 'bg-cyberTeal/15 border-cyberTeal/30 text-cyberTeal hover:bg-cyberTeal/20'
                  }`}
                >
                  <Bot size={14} />
                  {activeConv.ai_active ? 'Disable Autopilot' : 'Enable Autopilot'}
                </button>
              </div>
            </div>
          </div>

          <div className="pt-md">
            <button
              onClick={() => handleStatusChange('resolved')}
              className="w-full py-md-sm bg-successGreen hover:bg-successGreen/95 text-white text-xs font-bold rounded-default flex items-center justify-center gap-xs shadow cursor-pointer border-none"
            >
              <CheckCircle size={14} />
              Resolve Ticket
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

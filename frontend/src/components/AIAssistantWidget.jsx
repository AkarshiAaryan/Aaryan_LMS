import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import {
  Bot,
  X,
  Send,
  Plus,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Sparkles,
  ChevronDown,
  Info,
  ArrowRight,
  MessageSquare,
  HelpCircle,
} from 'lucide-react';

export default function AIAssistantWidget() {
  const { user } = useAuth();
  const location = useLocation();
  const params = useParams();

  const [isOpen, setIsOpen] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const messagesEndRef = useRef(null);

  // Auto-detect page context based on URL and DOM
  const detectPageContext = () => {
    const path = location.pathname;
    const ctx = {
      page_type: 'general',
      course_id: null,
      resource_type: null,
      resource_id: null,
      assessment_status: 'none',
    };

    const courseMatch = path.match(/\/courses\/(\d+)/);
    if (courseMatch) {
      ctx.course_id = parseInt(courseMatch[1], 10);
      ctx.page_type = 'course';
    }

    const assignMatch = path.match(/\/assignments\/(\d+)/);
    if (assignMatch) {
      ctx.resource_type = 'assignment';
      ctx.resource_id = parseInt(assignMatch[1], 10);
      ctx.page_type = 'assignment_detail';
      ctx.assessment_status = 'active';
    }

    const quizMatch = path.match(/\/quizzes\/(\d+)/);
    if (quizMatch) {
      ctx.resource_type = 'quiz';
      ctx.resource_id = parseInt(quizMatch[1], 10);
      ctx.page_type = 'quiz_detail';
      ctx.assessment_status = 'active';
    }

    if (path.includes('/attempts/')) {
      ctx.resource_type = 'quiz';
      ctx.page_type = 'quiz_attempt';
      ctx.assessment_status = 'active';
    }

    if (path.includes('/grades')) {
      ctx.page_type = 'gradebook';
    }

    return ctx;
  };

  const currentContext = detectPageContext();

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  // Load conversations on mount
  useEffect(() => {
    if (user && isOpen) {
      loadConversations();
    }
  }, [user, isOpen]);

  const loadConversations = async () => {
    try {
      const res = await api.get('/api/ai/conversations');
      setConversations(res.data);
      if (res.data.length > 0 && !activeConvId) {
        selectConversation(res.data[0].conversation_id);
      }
    } catch (err) {
      console.error('Failed to load conversations', err);
    }
  };

  const selectConversation = async (convId) => {
    setActiveConvId(convId);
    setLoading(true);
    try {
      const res = await api.get(`/api/ai/conversations/${convId}`);
      const interactionHistory = [];
      if (res.data.interactions) {
        res.data.interactions.forEach((it) => {
          interactionHistory.push({
            role: 'user',
            text: it.user_request,
            id: `u-${it.id}`,
          });
          interactionHistory.push({
            role: 'assistant',
            text: it.agent_response,
            decision: it.guard_decision,
            violations: JSON.parse(it.violation_categories_json || '[]'),
            alternative: it.alternative_assistance,
            explanation: it.guard_explanation,
            id: `a-${it.id}`,
          });
        });
      }
      setMessages(interactionHistory);
    } catch (err) {
      setError('Failed to load conversation history');
    } finally {
      setLoading(false);
    }
  };

  const handleStartNewChat = async () => {
    try {
      setLoading(true);
      const res = await api.post('/api/ai/conversations', {
        title: currentContext.course_id ? `Course #${currentContext.course_id} Study` : 'Academic Study Session',
        course_id: currentContext.course_id,
      });
      setConversations([res.data, ...conversations]);
      setActiveConvId(res.data.conversation_id);
      setMessages([]);
    } catch (err) {
      setError('Could not start new chat session');
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const prompt = inputPrompt.trim();
    if (!prompt || loading) return;

    setInputPrompt('');
    setError(null);

    let convId = activeConvId;
    if (!convId) {
      try {
        const newConv = await api.post('/api/ai/conversations', {
          title: prompt.slice(0, 30),
          course_id: currentContext.course_id,
        });
        convId = newConv.data.conversation_id;
        setActiveConvId(convId);
        setConversations([newConv.data, ...conversations]);
      } catch (err) {
        setError('Failed to initialize session');
        return;
      }
    }

    const optimisticUserMsg = {
      role: 'user',
      text: prompt,
      id: `tmp-${Date.now()}`,
    };
    setMessages((prev) => [...prev, optimisticUserMsg]);
    setLoading(true);

    try {
      const res = await api.post(`/api/ai/conversations/${convId}/messages`, {
        user_request: prompt,
        page_context: currentContext,
      });

      const assistantMsg = {
        role: 'assistant',
        text: res.data.agent_response,
        decision: res.data.guard_decision,
        violations: res.data.violation_categories,
        alternative: res.data.alternative_assistance,
        explanation: res.data.guard_explanation,
        id: res.data.interaction_id,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Policy Guard communication failure');
    } finally {
      setLoading(false);
    }
  };

  const getDecisionBadge = (decision) => {
    switch (decision) {
      case 'ALLOW':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <ShieldCheck size={12} />
            ALLOW
          </span>
        );
      case 'LIMIT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle size={12} />
            LIMIT
          </span>
        );
      case 'BLOCK':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            <ShieldAlert size={12} />
            BLOCK
          </span>
        );
      case 'ESCALATE':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
            <ShieldAlert size={12} />
            ESCALATE
          </span>
        );
      default:
        return null;
    }
  };

  const renderSimpleMarkdown = (text) => {
    if (!text) return '';
    return text.split('\n\n').map((paragraph, idx) => {
      if (paragraph.startsWith('### ')) {
        return (
          <h4 key={idx} className="font-bold text-slate-900 mt-2 mb-1 text-sm">
            {paragraph.replace('### ', '')}
          </h4>
        );
      }
      if (paragraph.startsWith('> [!NOTE]') || paragraph.startsWith('> [!WARNING]')) {
        return (
          <div key={idx} className="p-2.5 bg-blue-50 border-l-4 border-blue-500 rounded text-xs text-blue-900 my-2">
            {paragraph.replace(/> \[[!A-Z]+\]\s*/g, '')}
          </div>
        );
      }
      if (paragraph.startsWith('- ') || paragraph.startsWith('* ')) {
        const items = paragraph.split('\n');
        return (
          <ul key={idx} className="list-disc pl-4 space-y-1 text-xs text-slate-700 my-1">
            {items.map((it, i) => (
              <li key={i}>{it.replace(/^[-*]\s*/, '')}</li>
            ))}
          </ul>
        );
      }
      return (
        <p key={idx} className="text-xs text-slate-800 leading-relaxed my-1">
          {paragraph}
        </p>
      );
    });
  };

  if (!user) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Floating Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2.5 bg-navy-800 hover:bg-navy-900 text-white px-4 py-3 rounded-full shadow-xl transition-all duration-200 hover:scale-105 border border-navy-700"
          aria-label="Open AI Assistant"
          data-testid="ai-assistant-toggle"
        >
          <div className="relative">
            <Bot size={20} className="text-amber-400" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 border-2 border-navy-800 rounded-full animate-pulse" />
          </div>
          <span className="text-sm font-semibold tracking-wide">AI Assistant</span>
          <span className="text-[10px] uppercase font-bold bg-navy-950 px-2 py-0.5 rounded text-amber-300">
            {user.role}
          </span>
        </button>
      )}

      {/* Expanded Assistant Drawer */}
      {isOpen && (
        <div
          className="w-[420px] h-[640px] max-h-[88vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-200"
          data-testid="ai-assistant-drawer"
        >
          {/* Header */}
          <div className="bg-navy-900 text-white p-3.5 flex items-center justify-between border-b border-navy-800">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 bg-navy-800 rounded-lg text-amber-400">
                <Bot size={18} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold tracking-tight">GuardSLM Assistant</h3>
                  <span className="text-[10px] font-semibold uppercase bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/30">
                    Policy Active
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-slate-300">
                  <span>Persona: <strong className="text-white">{user.username}</strong></span>
                  <span>•</span>
                  <span className="capitalize">{user.role} Authority</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleStartNewChat}
                title="New Chat Session"
                className="p-1.5 text-slate-300 hover:text-white hover:bg-navy-800 rounded-lg transition"
              >
                <Plus size={16} />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-slate-300 hover:text-white hover:bg-navy-800 rounded-lg transition"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Context Banner */}
          <div className="bg-slate-100 px-3.5 py-1.5 border-b border-slate-200 flex items-center justify-between text-[11px] text-slate-600">
            <div className="flex items-center gap-1.5 truncate">
              <Sparkles size={12} className="text-navy-700 shrink-0" />
              <span className="truncate">
                Detected: <strong className="text-slate-900">{currentContext.page_type}</strong>
                {currentContext.course_id && ` (Course #${currentContext.course_id})`}
                {currentContext.assessment_status === 'active' && ' • Assessment Active'}
              </span>
            </div>
            {conversations.length > 1 && (
              <select
                value={activeConvId || ''}
                onChange={(e) => selectConversation(e.target.value)}
                className="text-[11px] bg-white border border-slate-300 rounded px-1.5 py-0.5 text-slate-700 focus:outline-none"
              >
                {conversations.map((c) => (
                  <option key={c.conversation_id} value={c.conversation_id}>
                    {c.title.slice(0, 20)}...
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-slate-50/50">
            {messages.length === 0 && (
              <div className="p-4 bg-white rounded-xl border border-slate-200 text-center space-y-2 mt-4 shadow-sm">
                <div className="w-10 h-10 bg-navy-50 text-navy-800 rounded-full flex items-center justify-center mx-auto">
                  <Sparkles size={20} />
                </div>
                <h4 className="text-xs font-bold text-slate-900">Simulated Academic Assistant</h4>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Ask conceptual questions, request progressive hints, or diagnose code errors.
                  Requests are verified by institutional policy guards before response generation.
                </p>
                <div className="pt-2 flex flex-wrap gap-1.5 justify-center">
                  <button
                    onClick={() => setInputPrompt('Explain the concept of recursion.')}
                    className="text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-1 rounded-full transition"
                  >
                    Explain Recursion
                  </button>
                  <button
                    onClick={() => setInputPrompt('How does binary search work?')}
                    className="text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-1 rounded-full transition"
                  >
                    Binary Search
                  </button>
                  <button
                    onClick={() => setInputPrompt('Can you give me a hint on this assignment?')}
                    className="text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-1 rounded-full transition"
                  >
                    Assignment Hint
                  </button>
                </div>
              </div>
            )}

            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                {m.role === 'user' ? (
                  <div className="max-w-[85%] bg-navy-800 text-white rounded-2xl rounded-tr-sm px-3.5 py-2 text-xs shadow-sm">
                    {m.text}
                  </div>
                ) : (
                  <div className="max-w-[95%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-3.5 text-xs shadow-sm space-y-2">
                    {/* Guard Outcome Header */}
                    <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 gap-2">
                      <div className="flex items-center gap-1.5">
                        {getDecisionBadge(m.decision)}
                        {m.violations && m.violations.length > 0 && (
                          <span className="text-[10px] font-semibold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded">
                            {m.violations[0].replace(/_/g, ' ')}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400">Deterministic Engine</span>
                    </div>

                    {/* Agent Response Content */}
                    <div className="prose-xs text-slate-800">
                      {renderSimpleMarkdown(m.text)}
                    </div>

                    {/* Permitted Alternative Suggestion Box */}
                    {m.alternative && (m.decision === 'BLOCK' || m.decision === 'LIMIT') && (
                      <div className="mt-2.5 p-2 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-900 space-y-1">
                        <div className="flex items-center gap-1 font-semibold text-amber-800">
                          <Info size={12} />
                          <span>Permitted Educational Alternative:</span>
                        </div>
                        <p className="text-[11px] leading-relaxed text-slate-700">{m.alternative}</p>
                        <button
                          onClick={() => setInputPrompt('Can you provide a conceptual hint and pseudocode approach instead?')}
                          className="mt-1 flex items-center gap-1 text-[10px] font-bold text-navy-800 hover:text-navy-950 underline"
                        >
                          <span>Ask for conceptual approach</span>
                          <ArrowRight size={10} />
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 p-3 bg-white rounded-xl border border-slate-200 w-fit text-xs text-slate-500 shadow-sm animate-pulse">
                <Bot size={14} className="text-navy-800 animate-spin" />
                <span>Evaluating policy guard & generating guidance...</span>
              </div>
            )}

            {error && (
              <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center gap-2">
                <AlertTriangle size={14} className="shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Footer Input */}
          <form
            onSubmit={handleSendMessage}
            className="p-3 bg-white border-t border-slate-200 flex items-center gap-2"
          >
            <input
              type="text"
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              placeholder="Ask an academic question..."
              className="flex-1 bg-slate-100 hover:bg-slate-100/80 focus:bg-white text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 focus:border-navy-800 focus:outline-none transition"
              disabled={loading}
              data-testid="ai-assistant-input"
            />
            <button
              type="submit"
              disabled={loading || !inputPrompt.trim()}
              className="p-2.5 bg-navy-800 hover:bg-navy-900 disabled:bg-slate-300 text-white rounded-xl transition shadow-sm"
              data-testid="ai-assistant-send"
            >
              <Send size={14} />
            </button>
          </form>

          {/* Guard SLM Testbed Notice */}
          <div className="bg-slate-50 px-3 py-1 border-t border-slate-200 text-[10px] text-slate-400 text-center flex items-center justify-center gap-2">
            <span>Deterministic Policy Testbed</span>
            <span>•</span>
            <span>No External LLM APIs</span>
          </div>
        </div>
      )}
    </div>
  );
}

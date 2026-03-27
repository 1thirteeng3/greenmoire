import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  CognitiveSessionState,
  Message,
  PlanFrame,
  PlanStep,
  ResponseFrame,
  TraceFrame,
  UseCognitiveStreamReturn,
  WsConnectionStatus,
  WsFrame,
} from '../types';

// Config – can be overridden via env vars in Vite
const WS_URL = (import.meta.env.VITE_WS_URL as string) || 'ws://localhost:8000/ws/cognitive-stream';
const API_TOKEN = (import.meta.env.VITE_API_TOKEN as string) || 'grimoire_super_secret_token_2026';
const RECONNECT_DELAY_MS = 3000;
const MAX_TRACE_LINES = 200;

const INITIAL_SESSION: CognitiveSessionState = {
  status: 'idle',
  traces: [],
  planSteps: [],
};

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useCognitiveStream(): UseCognitiveStreamReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingPromptRef = useRef<string | null>(null);
  const connectRef = useRef<() => void>(() => {});

  const [connectionStatus, setConnectionStatus] = useState<WsConnectionStatus>('disconnected');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [session, setSession] = useState<CognitiveSessionState>(INITIAL_SESSION);


  // ==========================================
  // Frame dispatcher
  // ==========================================

  const _doSend = useCallback((prompt: string) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;

    const userMsg: Message = {
      id: generateId(),
      role: 'user',
      content: prompt,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setSession({
      status: 'classifying',
      traces: [],
      planSteps: [],
    });

    wsRef.current.send(JSON.stringify({ prompt, context_hints: [] }));
  }, []);

  const handleFrame = useCallback((frame: WsFrame) => {
    switch (frame.type) {
      case 'connected': {
        setSessionId(frame.session_id);
        // If there was a pending prompt (sent before connected), send it now
        if (pendingPromptRef.current) {
          _doSend(pendingPromptRef.current);
          pendingPromptRef.current = null;
        }
        break;
      }

      case 'trace': {
        const tf = frame as TraceFrame;
        setSession(prev => ({
          ...prev,
          status: _inferStatus(tf.agent),
          traces: [
            ...prev.traces.slice(-(MAX_TRACE_LINES - 1)),
            tf,
          ],
        }));
        break;
      }

      case 'plan': {
        const pf = frame as PlanFrame;
        setSession(prev => ({
          ...prev,
          plan: pf,
          planSteps: pf.steps,
          status: 'executing',
        }));
        break;
      }

      case 'plan_step_update': {
        const { step_id, status } = frame as { step_id: number; status: PlanStep['status']; type: string; trace_id: string };
        setSession(prev => ({
          ...prev,
          planSteps: prev.planSteps.map(s =>
            s.id === step_id ? { ...s, status } : s
          ),
        }));
        break;
      }

      case 'response': {
        const rf = frame as ResponseFrame;
        const grimMsg: Message = {
          id: generateId(),
          role: 'grimoire',
          content: rf.content,
          timestamp: new Date(),
          trace_id: rf.trace_id,
          metadata: {
            tier: rf.tier_used,
            primary_intent: rf.primary_intent,
            audit_approved: rf.audit_approved,
            audit_critique: rf.audit_critique,
            tokens_used: rf.metadata.tokens_used,
            elapsed_ms: rf.metadata.elapsed_ms,
          },
        };
        setMessages(prev => [...prev, grimMsg]);
        setSession(prev => ({
          ...prev,
          status: 'completed',
          traceId: rf.trace_id,
        }));
        break;
      }

      case 'error': {
        const ef = frame as { type: 'error'; trace_id: string; code: string; message: string };
        const errMsg: Message = {
          id: generateId(),
          role: 'system',
          content: `**Erro do Sistema [${ef.code}]:** ${ef.message}`,
          timestamp: new Date(),
          trace_id: ef.trace_id,
        };
        setMessages(prev => [...prev, errMsg]);
        setSession(prev => ({ ...prev, status: 'error' }));
        break;
      }

      default:
        break;
    }
  }, [_doSend]);

  // ==========================================
  // WebSocket lifecycle
  // ==========================================

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    setConnectionStatus('connecting');
    const url = `${WS_URL}?token=${encodeURIComponent(API_TOKEN)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const frame = JSON.parse(event.data) as WsFrame;
        handleFrame(frame);
      } catch (err) {
        console.error('[Grimoire WS] Failed to parse frame:', err);
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      wsRef.current = null;
      // Auto-reconnect
      reconnectTimerRef.current = setTimeout(() => connectRef.current(), RECONNECT_DELAY_MS);
    };

    ws.onerror = () => {
      setConnectionStatus('error');
      ws.close();
    };
  }, [handleFrame]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connectRef.current();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, []);


  const sendPrompt = useCallback((prompt: string) => {
    const trimmed = prompt.trim();
    if (!trimmed) return;

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      _doSend(trimmed);
    } else {
      // Queue and connect
      pendingPromptRef.current = trimmed;
      connect();
    }
  }, [connect, _doSend]);

  const clearHistory = useCallback(() => {
    setMessages([]);
    setSession(INITIAL_SESSION);
  }, []);

  return {
    connectionStatus,
    sessionId,
    messages,
    session,
    sendPrompt,
    clearHistory,
  };
}

// ==========================================
// Helper: infer cognitive status from agent name
// ==========================================

function _inferStatus(agent: string): CognitiveSessionState['status'] {
  const lower = agent.toLowerCase();
  if (lower.includes('classifier')) return 'classifying';
  if (lower.includes('planner')) return 'planning';
  if (lower.includes('executor')) return 'executing';
  if (lower.includes('auditor')) return 'auditing';
  return 'executing';
}

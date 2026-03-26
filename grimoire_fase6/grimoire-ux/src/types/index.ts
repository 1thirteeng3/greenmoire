// ==========================================
// GRIMOIRE UX — Type Contracts
// Mirrors the backend Pydantic schemas (core/api/schemas.py)
// ==========================================

export type UiMode = 'standard' | 'advanced';

// --- WebSocket Frame Types ---

export type WsFrameType =
  | 'trace'
  | 'plan'
  | 'plan_step_update'
  | 'response'
  | 'error'
  | 'heartbeat'
  | 'connected';

export interface ConnectedFrame {
  type: 'connected';
  session_id: string;
  message: string;
}

export interface TraceFrame {
  type: 'trace';
  trace_id: string;
  agent: string;
  action: string;
  tier?: 'T1' | 'T2' | 'T3';
  timestamp_ms: number;
}

export interface PlanStep {
  id: number;
  description: string;
  tools: string[];
  status: 'pending' | 'active' | 'completed' | 'failed';
}

export interface PlanFrame {
  type: 'plan';
  trace_id: string;
  plan_rationale: string;
  steps: PlanStep[];
}

export interface PlanStepUpdateFrame {
  type: 'plan_step_update';
  trace_id: string;
  step_id: number;
  status: PlanStep['status'];
}

export interface ResponseFrame {
  type: 'response';
  trace_id: string;
  content: string;
  tier_used: string;
  primary_intent: string;
  audit_approved: boolean;
  audit_critique?: string;
  metadata: {
    tokens_used?: number;
    elapsed_ms?: number;
  };
}

export interface ErrorFrame {
  type: 'error';
  trace_id: string;
  code: string;
  message: string;
}

export type WsFrame =
  | ConnectedFrame
  | TraceFrame
  | PlanFrame
  | PlanStepUpdateFrame
  | ResponseFrame
  | ErrorFrame
  | { type: 'heartbeat'; ts: number };

// --- Message Model (for IterationHistory) ---

export type MessageRole = 'user' | 'grimoire' | 'system';

export interface MessageMetadata {
  tier: string;
  primary_intent: string;
  audit_approved: boolean;
  audit_critique?: string;
  tokens_used?: number;
  elapsed_ms?: number;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  trace_id?: string;
  metadata?: MessageMetadata;
  isStreaming?: boolean;
}

// --- Cognitive Stream State ---

export type CognitiveCycleStatus =
  | 'idle'
  | 'classifying'
  | 'planning'
  | 'executing'
  | 'auditing'
  | 'completed'
  | 'error';

export interface CognitiveSessionState {
  status: CognitiveCycleStatus;
  traceId?: string;
  traces: TraceFrame[];
  plan?: PlanFrame;
  planSteps: PlanStep[];
}

// --- WebSocket Hook State ---

export type WsConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UseCognitiveStreamReturn {
  connectionStatus: WsConnectionStatus;
  sessionId: string | null;
  messages: Message[];
  session: CognitiveSessionState;
  sendPrompt: (prompt: string) => void;
  clearHistory: () => void;
}

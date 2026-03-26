import React from 'react';
import { useUi } from './contexts/UiContext';
import { useCognitiveStream } from './hooks/useCognitiveStream';

// Layout
import { Header } from './components/layout/Header';

// Transparency (Advanced mode)
import { LiveTracePanel } from './components/transparency/LiveTracePanel';
import { ExecutionPlanVisualizer } from './components/transparency/ExecutionPlan';
import { IterationHistory } from './components/transparency/IterationHistory';

// Shared
import { CognitiveCycleIndicator } from './components/shared/CognitiveCycleIndicator';
import { ChatInput } from './components/chat/ChatInput';

const TRACE_PANEL_WIDTH = 300;

const App: React.FC = () => {
  const { isAdvanced } = useUi();
  const {
    connectionStatus,
    sessionId,
    messages,
    session,
    sendPrompt,
    clearHistory,
  } = useCognitiveStream();

  const isProcessing =
    session.status !== 'idle' &&
    session.status !== 'completed' &&
    session.status !== 'error';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100dvh',
        overflow: 'hidden',
        background: 'var(--color-vault-900)',
      }}
    >
      {/* ── Top Navigation ── */}
      <Header
        connectionStatus={connectionStatus}
        sessionId={sessionId}
        onClearHistory={clearHistory}
      />

      {/* ── Main workspace ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── Center: Chat + Plan ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {/* Cognitive cycle breadcrumb */}
          <CognitiveCycleIndicator session={session} />

          {/* Execution plan (T3 only, visible in both modes when active) */}
          {session.planSteps.length > 0 && (
            <div style={{ overflowY: 'auto', maxHeight: '280px', flexShrink: 0 }}>
              <ExecutionPlanVisualizer session={session} />
            </div>
          )}

          {/* ── Message history ── */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <IterationHistory messages={messages} isProcessing={isProcessing} />
          </div>

          {/* ── Input bar ── */}
          <ChatInput
            onSend={sendPrompt}
            status={session.status}
            disabled={connectionStatus !== 'connected'}
          />
        </div>

        {/* ── Right: Live Trace Panel (Advanced mode only) ── */}
        {isAdvanced && (
          <div
            className="animate-fade-in-up"
            style={{
              width: `${TRACE_PANEL_WIDTH}px`,
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <LiveTracePanel session={session} />
          </div>
        )}
      </div>
    </div>
  );
};

export default App;

import React, { useEffect, useRef } from 'react';
import type { CognitiveSessionState, TraceFrame } from '../../types';

interface LiveTracePanelProps {
  session: CognitiveSessionState;
}

// ==========================================
// AGENT COLOR MAP
// ==========================================

const AGENT_COLORS: Record<string, string> = {
  IntentClassifier:    'var(--color-tele-t1)',
  ContextBuilder:      'var(--color-tele-t2)',
  ConflictResolver:    'var(--color-tele-warn)',
  AgentSelector:       'var(--color-tele-t2)',
  PlannerAgent:        'var(--color-tele-t3)',
  ExecutorAgent:       'var(--color-tele-t3)',
  AuditorAgent:        'var(--color-tele-audit)',
  ModelRouter:         'var(--color-tele-t1)',
  OrchestratorWorker:  'var(--color-vault-400)',
  System:              'var(--color-vault-500)',
};

const TIER_COLORS: Record<string, string> = {
  T1: 'var(--color-tele-t1)',
  T2: 'var(--color-tele-t2)',
  T3: 'var(--color-tele-t3)',
};

function getAgentColor(agent: string): string {
  return AGENT_COLORS[agent] ?? 'var(--color-vault-400)';
}

// ==========================================
// STATUS CYCLE INDICATOR
// ==========================================

const STATUS_LABELS: Record<CognitiveSessionState['status'], { label: string; color: string }> = {
  idle:        { label: 'IDLE',        color: 'var(--color-vault-500)' },
  classifying: { label: 'CLASSIFYING', color: 'var(--color-tele-t1)'   },
  planning:    { label: 'PLANNING',    color: 'var(--color-tele-t2)'   },
  executing:   { label: 'EXECUTING',   color: 'var(--color-tele-t3)'   },
  auditing:    { label: 'AUDITING',    color: 'var(--color-tele-audit)' },
  completed:   { label: 'COMPLETED',   color: 'var(--color-tele-audit)' },
  error:       { label: 'ERROR',       color: 'var(--color-tele-alert)' },
};

// ==========================================
// SINGLE LOG LINE
// ==========================================

const TraceLine: React.FC<{ frame: TraceFrame; index: number }> = ({ frame, index }) => {
  const agentColor = getAgentColor(frame.agent);
  const tierColor  = frame.tier ? TIER_COLORS[frame.tier] : undefined;

  const time = new Date(frame.timestamp_ms).toLocaleTimeString('pt-BR', {
    hour:   '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <div
      className="animate-fade-in-up"
      style={{
        display: 'flex',
        gap: '8px',
        alignItems: 'flex-start',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        lineHeight: 1.5,
        padding: '1px 0',
        animationDelay: `${Math.min(index * 20, 100)}ms`,
      }}
    >
      {/* Timestamp */}
      <span style={{ color: 'var(--color-vault-600)', flexShrink: 0, userSelect: 'none' }}>
        {time}
      </span>

      {/* Tier badge */}
      {frame.tier && (
        <span
          style={{
            color: tierColor,
            flexShrink: 0,
            fontSize: '9px',
            fontWeight: 700,
            padding: '1px 4px',
            background: `${tierColor}18`,
            border: `1px solid ${tierColor}30`,
            borderRadius: '3px',
            marginTop: '1px',
          }}
        >
          {frame.tier}
        </span>
      )}

      {/* Agent name */}
      <span
        style={{
          color: agentColor,
          flexShrink: 0,
          fontWeight: 600,
          minWidth: '140px',
        }}
      >
        {frame.agent}
      </span>

      {/* Action message */}
      <span style={{ color: 'var(--color-vault-300)', wordBreak: 'break-word' }}>
        {frame.action}
      </span>
    </div>
  );
};

// ==========================================
// MAIN COMPONENT
// ==========================================

export const LiveTracePanel: React.FC<LiveTracePanelProps> = ({ session }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { status, traces } = session;
  const statusCfg = STATUS_LABELS[status];
  const isActive = status !== 'idle' && status !== 'completed' && status !== 'error';

  // Auto-scroll to bottom on new trace
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [traces]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#080c12',
        borderLeft: '1px solid var(--color-vault-700)',
      }}
    >
      {/* ── Header ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          borderBottom: '1px solid var(--color-vault-700)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: 'var(--color-vault-400)',
            }}
          >
            COGNITIVE_TRACE_LOG
          </span>
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-vault-600)',
            }}
          >
            [{traces.length}]
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* Live pulse */}
          {isActive && (
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: statusCfg.color,
                boxShadow: `0 0 6px ${statusCfg.color}`,
                animation: 'pulse-dot 1s ease-in-out infinite',
                display: 'block',
              }}
            />
          )}
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              fontWeight: 700,
              letterSpacing: '0.1em',
              color: statusCfg.color,
            }}
          >
            {statusCfg.label}
          </span>
        </div>
      </div>

      {/* ── Agent Legend ── */}
      <div
        style={{
          padding: '6px 14px',
          borderBottom: '1px solid var(--color-vault-800)',
          flexShrink: 0,
          display: 'flex',
          gap: '10px',
          flexWrap: 'wrap',
          overflowX: 'auto',
        }}
      >
        {Object.entries(AGENT_COLORS).slice(0, 6).map(([agent, color]) => (
          <span
            key={agent}
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              color,
              opacity: 0.7,
              whiteSpace: 'nowrap',
            }}
          >
            ● {agent}
          </span>
        ))}
      </div>

      {/* ── Log body ── */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '10px 14px',
          position: 'relative',
        }}
      >
        {/* Scanline effect (subtle) */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            pointerEvents: 'none',
            background:
              'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)',
          }}
        />

        {traces.length === 0 ? (
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              color: 'var(--color-vault-700)',
              textAlign: 'center',
              marginTop: '32px',
            }}
          >
            {status === 'idle'
              ? '// Aguardando ciclo cognitivo...'
              : '// Inicializando rastreamento...'}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {traces.map((frame, i) => (
              <TraceLine key={`${frame.timestamp_ms}-${i}`} frame={frame} index={i} />
            ))}

            {/* Blinking cursor when active */}
            {isActive && (
              <span
                style={{
                  display: 'inline-block',
                  width: '7px',
                  height: '13px',
                  background: 'var(--color-vault-500)',
                  marginTop: '4px',
                  animation: 'blink 1s step-end infinite',
                }}
              />
            )}
          </div>
        )}
      </div>

      {/* ── Footer stats ── */}
      <div
        style={{
          padding: '6px 14px',
          borderTop: '1px solid var(--color-vault-800)',
          flexShrink: 0,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            color: 'var(--color-vault-600)',
          }}
        >
          {session.traceId
            ? `trace: ${session.traceId}`
            : '// no active trace'}
        </span>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            color: 'var(--color-vault-700)',
          }}
        >
          grimoire-ux v6.0
        </span>
      </div>
    </div>
  );
};

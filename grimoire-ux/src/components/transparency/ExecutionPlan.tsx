import React from 'react';
import type { CognitiveSessionState, PlanStep } from '../../types';

interface ExecutionPlanProps {
  session: CognitiveSessionState;
}

// ==========================================
// STEP STATUS CONFIG
// ==========================================

const STATUS_CONFIG: Record<PlanStep['status'], {
  color: string;
  bgColor: string;
  icon: string;
  label: string;
  glow?: string;
}> = {
  pending: {
    color: 'var(--color-vault-500)',
    bgColor: 'var(--color-vault-700)',
    icon: '○',
    label: 'Aguardando',
  },
  active: {
    color: 'var(--color-tele-t3)',
    bgColor: 'rgba(227,179,65,0.12)',
    icon: '◉',
    label: 'Executando',
    glow: '0 0 8px rgba(227,179,65,0.35)',
  },
  completed: {
    color: 'var(--color-tele-audit)',
    bgColor: 'rgba(63,185,80,0.1)',
    icon: '●',
    label: 'Concluído',
  },
  failed: {
    color: 'var(--color-tele-alert)',
    bgColor: 'rgba(248,81,73,0.1)',
    icon: '✗',
    label: 'Falhou',
  },
};

// ==========================================
// TOOL CHIP
// ==========================================

const ToolChip: React.FC<{ tool: string }> = ({ tool }) => (
  <span
    style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '10px',
      padding: '1px 6px',
      background: 'rgba(88,166,255,0.08)',
      border: '1px solid rgba(88,166,255,0.18)',
      borderRadius: '4px',
      color: 'var(--color-tele-t1)',
    }}
  >
    {tool}
  </span>
);

// ==========================================
// STEP ROW
// ==========================================

const StepRow: React.FC<{ step: PlanStep; isLast: boolean }> = ({ step, isLast }) => {
  const cfg = STATUS_CONFIG[step.status];
  const isActive = step.status === 'active';

  return (
    <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
      {/* Connector line + status dot */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
        <div
          style={{
            width: '22px',
            height: '22px',
            borderRadius: '50%',
            background: cfg.bgColor,
            border: `1px solid ${cfg.color}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '10px',
            color: cfg.color,
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            boxShadow: isActive ? cfg.glow : undefined,
            transition: 'all 0.3s ease',
          }}
        >
          {isActive ? (
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: cfg.color,
                animation: 'pulse-dot 1s ease-in-out infinite',
              }}
            />
          ) : (
            step.id
          )}
        </div>

        {!isLast && (
          <div
            style={{
              width: '1px',
              flex: 1,
              minHeight: '16px',
              marginTop: '3px',
              background: step.status === 'completed'
                ? 'var(--color-tele-audit)'
                : 'var(--color-vault-700)',
              opacity: 0.5,
            }}
          />
        )}
      </div>

      {/* Step content */}
      <div
        style={{
          flex: 1,
          paddingBottom: isLast ? 0 : '14px',
          paddingTop: '2px',
          transition: 'opacity 0.2s',
          opacity: step.status === 'pending' ? 0.55 : 1,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexWrap: 'wrap',
            marginBottom: '4px',
          }}
        >
          <span
            style={{
              fontSize: '12px',
              color: step.status === 'active' || step.status === 'completed'
                ? 'var(--color-vault-100)'
                : 'var(--color-vault-300)',
              fontWeight: step.status === 'active' ? 600 : 400,
              lineHeight: 1.4,
            }}
          >
            {step.description}
          </span>
        </div>

        {/* Tool chips */}
        {step.tools.length > 0 && (
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {step.tools.map(t => (
              <ToolChip key={t} tool={t} />
            ))}
          </div>
        )}

        {/* Status label */}
        <div
          style={{
            marginTop: '4px',
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
            color: cfg.color,
            opacity: 0.8,
          }}
        >
          {cfg.label}
        </div>
      </div>
    </div>
  );
};

// ==========================================
// PROGRESS BAR
// ==========================================

const PlanProgress: React.FC<{ steps: PlanStep[] }> = ({ steps }) => {
  if (steps.length === 0) return null;
  const completed = steps.filter(s => s.status === 'completed').length;
  const pct = Math.round((completed / steps.length) * 100);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
      <div
        style={{
          flex: 1,
          height: '3px',
          background: 'var(--color-vault-700)',
          borderRadius: '99px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: pct === 100
              ? 'var(--color-tele-audit)'
              : 'linear-gradient(90deg, var(--color-tele-t1), var(--color-tele-t3))',
            borderRadius: '99px',
            transition: 'width 0.4s ease',
          }}
        />
      </div>
      <span
        style={{
          fontSize: '10px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--color-vault-500)',
          minWidth: '32px',
        }}
      >
        {pct}%
      </span>
    </div>
  );
};

// ==========================================
// MAIN COMPONENT
// ==========================================

export const ExecutionPlanVisualizer: React.FC<ExecutionPlanProps> = ({ session }) => {
  const { plan, planSteps } = session;

  if (!plan || planSteps.length === 0) return null;

  return (
    <div
      className="animate-fade-in-up vault-surface"
      style={{ padding: '14px 16px', margin: '0 24px 12px' }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '12px',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: 'var(--color-tele-t3)',
          }}
        >
          GRAFO DE EXECUÇÃO
        </span>
        <span className="tier-badge tier-t3">T3</span>
        <span
          style={{
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--color-vault-500)',
          }}
        >
          {planSteps.length} etapa{planSteps.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Rationale */}
      {plan.plan_rationale && (
        <div
          style={{
            marginBottom: '12px',
            padding: '8px 10px',
            background: 'var(--color-vault-750)',
            borderRadius: '4px',
            borderLeft: '2px solid var(--color-tele-t2)',
            fontSize: '11px',
            color: 'var(--color-vault-400)',
            fontStyle: 'italic',
            lineHeight: 1.5,
          }}
        >
          {plan.plan_rationale}
        </div>
      )}

      {/* Progress */}
      <PlanProgress steps={planSteps} />

      {/* Steps */}
      <div>
        {planSteps.map((step, i) => (
          <StepRow key={step.id} step={step} isLast={i === planSteps.length - 1} />
        ))}
      </div>
    </div>
  );
};

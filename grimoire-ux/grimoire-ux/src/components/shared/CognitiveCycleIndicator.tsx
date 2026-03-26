import React from 'react';
import type { CognitiveSessionState } from '../../types';

interface CognitiveCycleIndicatorProps {
  session: CognitiveSessionState;
}

const STEPS = [
  { key: 'classifying', label: 'Classificar',  icon: '⧩' },
  { key: 'planning',    label: 'Planear',       icon: '◫' },
  { key: 'executing',   label: 'Executar',      icon: '⚙' },
  { key: 'auditing',    label: 'Auditar',       icon: '⬡' },
  { key: 'completed',   label: 'Concluído',     icon: '✓' },
] as const;

type StepKey = typeof STEPS[number]['key'];

const ORDER: StepKey[] = ['classifying', 'planning', 'executing', 'auditing', 'completed'];

function getStepState(stepKey: StepKey, currentStatus: CognitiveSessionState['status']): 'done' | 'active' | 'pending' {
  if (currentStatus === 'idle' || currentStatus === 'error') return 'pending';
  const currentIdx = ORDER.indexOf(currentStatus as StepKey);
  const stepIdx    = ORDER.indexOf(stepKey);
  if (stepIdx < currentIdx) return 'done';
  if (stepIdx === currentIdx) return 'active';
  return 'pending';
}

export const CognitiveCycleIndicator: React.FC<CognitiveCycleIndicatorProps> = ({ session }) => {
  const { status } = session;
  const isActive = status !== 'idle';

  if (!isActive) return null;

  return (
    <div
      className="animate-fade-in-up"
      style={{
        padding: '8px 24px',
        borderBottom: '1px solid var(--color-vault-800)',
        background: 'var(--color-vault-850)',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: '0',
        overflowX: 'auto',
      }}
    >
      {STEPS.map((step, i) => {
        const state = getStepState(step.key, status);
        const isLast = i === STEPS.length - 1;

        return (
          <React.Fragment key={step.key}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '3px 8px',
                borderRadius: '5px',
                background:
                  state === 'active'
                    ? 'rgba(88,166,255,0.06)'
                    : 'transparent',
                border:
                  state === 'active'
                    ? '1px solid rgba(88,166,255,0.15)'
                    : '1px solid transparent',
                transition: 'all 0.3s',
              }}
            >
              <span
                style={{
                  fontSize: '12px',
                  color:
                    state === 'done'   ? 'var(--color-tele-audit)' :
                    state === 'active' ? 'var(--color-tele-t1)'    :
                                         'var(--color-vault-700)',
                  transition: 'color 0.3s',
                }}
              >
                {state === 'done' ? '✓' : step.icon}
              </span>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '10px',
                  fontWeight: state === 'active' ? 600 : 400,
                  color:
                    state === 'done'   ? 'var(--color-tele-audit)' :
                    state === 'active' ? 'var(--color-tele-t1)'    :
                                         'var(--color-vault-600)',
                  transition: 'color 0.3s',
                  whiteSpace: 'nowrap',
                }}
              >
                {step.label}
              </span>
            </div>

            {!isLast && (
              <div
                style={{
                  width: '20px',
                  height: '1px',
                  background:
                    getStepState(STEPS[i + 1].key, status) !== 'pending'
                      ? 'var(--color-vault-600)'
                      : 'var(--color-vault-800)',
                  flexShrink: 0,
                  transition: 'background 0.3s',
                }}
              />
            )}
          </React.Fragment>
        );
      })}

      {/* Error state */}
      {status === 'error' && (
        <div
          style={{
            marginLeft: 'auto',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--color-tele-alert)',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
          }}
        >
          <span>✗</span>
          <span>Erro no ciclo cognitivo</span>
        </div>
      )}
    </div>
  );
};

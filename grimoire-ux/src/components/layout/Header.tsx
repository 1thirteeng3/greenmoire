import React from 'react';
import { useUi } from '../../contexts/UiContext';
import type { WsConnectionStatus } from '../../types';

interface HeaderProps {
  connectionStatus: WsConnectionStatus;
  sessionId: string | null;
  onClearHistory: () => void;
}

const CONNECTION_CONFIG: Record<WsConnectionStatus, { label: string; color: string; pulse: boolean }> = {
  connected:    { label: 'Conectado',    color: 'var(--color-tele-audit)', pulse: false },
  connecting:   { label: 'Conectando',   color: 'var(--color-tele-warn)',  pulse: true  },
  disconnected: { label: 'Desconectado', color: 'var(--color-vault-500)',  pulse: false },
  error:        { label: 'Erro WS',      color: 'var(--color-tele-alert)', pulse: false },
};

export const Header: React.FC<HeaderProps> = ({ connectionStatus, sessionId, onClearHistory }) => {
  const { mode, toggleMode, isAdvanced } = useUi();
  const connCfg = CONNECTION_CONFIG[connectionStatus];

  return (
    <header
      style={{
        height: '48px',
        background: 'var(--color-vault-900)',
        borderBottom: '1px solid var(--color-vault-700)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        flexShrink: 0,
        gap: '12px',
      }}
    >
      {/* ── Brand ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{ fontSize: '18px', lineHeight: 1 }}>🔮</span>
        <span
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '1rem',
            fontWeight: 700,
            color: 'var(--color-vault-100)',
            letterSpacing: '-0.01em',
          }}
        >
          Grimoire
        </span>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--color-vault-600)',
            paddingLeft: '4px',
            borderLeft: '1px solid var(--color-vault-700)',
          }}
        >
          Cognitive OS
        </span>
      </div>

      {/* ── Controls ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Session ID (advanced only) */}
        {isAdvanced && sessionId && (
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: 'var(--color-vault-600)',
              display: 'none',   // visible via CSS .advanced-mode
            }}
            className="advanced-only"
          >
            {sessionId}
          </span>
        )}

        {/* Connection status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: connCfg.color,
              display: 'block',
              animation: connCfg.pulse ? 'pulse-dot 1s ease-in-out infinite' : undefined,
            }}
          />
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: connCfg.color,
            }}
          >
            {connCfg.label}
          </span>
        </div>

        {/* Divider */}
        <div style={{ width: '1px', height: '20px', background: 'var(--color-vault-700)' }} />

        {/* Clear button */}
        <button
          onClick={onClearHistory}
          title="Limpar histórico"
          style={{
            background: 'transparent',
            border: '1px solid var(--color-vault-700)',
            borderRadius: '5px',
            padding: '3px 10px',
            color: 'var(--color-vault-400)',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            cursor: 'pointer',
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-vault-500)';
            (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-vault-200)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-vault-700)';
            (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-vault-400)';
          }}
        >
          limpar
        </button>

        {/* Mode toggle */}
        <button
          onClick={toggleMode}
          title={`Mudar para modo ${mode === 'standard' ? 'Advanced' : 'Standard'}`}
          style={{
            background: isAdvanced ? 'rgba(210,168,255,0.1)' : 'transparent',
            border: `1px solid ${isAdvanced ? 'rgba(210,168,255,0.35)' : 'var(--color-vault-700)'}`,
            borderRadius: '5px',
            padding: '3px 10px',
            color: isAdvanced ? 'var(--color-tele-t2)' : 'var(--color-vault-400)',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            cursor: 'pointer',
            transition: 'all 0.2s',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
          }}
        >
          <span>{isAdvanced ? '⬡' : '○'}</span>
          <span>{isAdvanced ? 'ADVANCED' : 'STANDARD'}</span>
        </button>
      </div>
    </header>
  );
};

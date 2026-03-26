import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useUi } from '../../contexts/UiContext';
import type { Message } from '../../types';

interface IterationHistoryProps {
  messages: Message[];
  isProcessing: boolean;
}

// ==========================================
// TIER COLOR MAP
// ==========================================
const TIER_CONFIG: Record<string, { label: string; cssClass: string; color: string }> = {
  T1: { label: 'T1 Direct',     cssClass: 'tier-t1', color: '#58a6ff' },
  T2: { label: 'T2 Analytical', cssClass: 'tier-t2', color: '#d2a8ff' },
  T3: { label: 'T3 Complex',    cssClass: 'tier-t3', color: '#e3b341' },
};

// ==========================================
// SUB-COMPONENTS
// ==========================================

const TierBadge: React.FC<{ tier: string }> = ({ tier }) => {
  const cfg = TIER_CONFIG[tier] ?? { label: tier, cssClass: 'tier-t1', color: '#58a6ff' };
  return (
    <span className={`tier-badge ${cfg.cssClass}`}>{cfg.label}</span>
  );
};

const MetadataBlock: React.FC<{ metadata: NonNullable<Message['metadata']> }> = ({ metadata }) => (
  <div
    style={{
      marginTop: '12px',
      paddingTop: '12px',
      borderTop: '1px solid var(--color-vault-700)',
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '6px 16px',
      fontFamily: 'var(--font-mono)',
      fontSize: '11px',
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <span style={{ color: 'var(--color-vault-500)' }}>Tier</span>
      <TierBadge tier={metadata.tier} />
    </div>

    {metadata.elapsed_ms !== undefined && (
      <div>
        <span style={{ color: 'var(--color-vault-500)' }}>Latência </span>
        <span style={{ color: 'var(--color-vault-300)' }}>
          {metadata.elapsed_ms < 1000
            ? `${metadata.elapsed_ms}ms`
            : `${(metadata.elapsed_ms / 1000).toFixed(1)}s`}
        </span>
      </div>
    )}

    {metadata.tokens_used !== undefined && (
      <div>
        <span style={{ color: 'var(--color-vault-500)' }}>Tokens </span>
        <span style={{ color: 'var(--color-vault-300)' }}>
          {metadata.tokens_used.toLocaleString()}
        </span>
      </div>
    )}

    <div>
      <span style={{ color: 'var(--color-vault-500)' }}>Intent </span>
      <span style={{ color: 'var(--color-tele-info)' }}>
        {metadata.primary_intent || '—'}
      </span>
    </div>

    <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
      <span style={{ color: 'var(--color-vault-500)', flexShrink: 0 }}>Auditoria</span>
      <span
        style={{
          color: metadata.audit_approved
            ? 'var(--color-tele-audit)'
            : 'var(--color-tele-alert)',
        }}
      >
        {metadata.audit_approved
          ? '✓ Aprovado'
          : `✗ Reprovado — ${metadata.audit_critique ?? 'sem critique'}`}
      </span>
    </div>
  </div>
);

const TypingIndicator: React.FC = () => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
      padding: '12px 16px',
    }}
  >
    {[0, 150, 300].map(delay => (
      <span
        key={delay}
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: 'var(--color-vault-500)',
          animation: `pulse-dot 1.4s ease-in-out ${delay}ms infinite`,
        }}
      />
    ))}
    <span
      style={{
        marginLeft: '8px',
        fontSize: '11px',
        color: 'var(--color-vault-500)',
        fontFamily: 'var(--font-mono)',
      }}
    >
      processando...
    </span>
  </div>
);

const EmptyState: React.FC = () => (
  <div
    style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '16px',
      padding: '48px 24px',
      textAlign: 'center',
    }}
  >
    <div
      style={{
        width: '64px',
        height: '64px',
        borderRadius: '16px',
        background: 'var(--color-vault-800)',
        border: '1px solid var(--color-vault-700)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '28px',
      }}
    >
      🔮
    </div>
    <div>
      <div
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.1rem',
          fontWeight: 600,
          color: 'var(--color-vault-200)',
          marginBottom: '6px',
        }}
      >
        Grimoire — Cognitive OS
      </div>
      <div style={{ fontSize: '0.8rem', color: 'var(--color-vault-500)', maxWidth: '320px' }}>
        O Sistema Operacional Cognitivo está ativo. Envie uma solicitação para iniciar o ciclo de raciocínio.
      </div>
    </div>
    <div
      style={{
        display: 'flex',
        gap: '8px',
        flexWrap: 'wrap',
        justifyContent: 'center',
        marginTop: '8px',
      }}
    >
      {[
        'Pesquise sobre IA em 2026',
        'Analise minhas notas sobre React',
        'Crie um plano de projeto',
      ].map(hint => (
        <span
          key={hint}
          style={{
            padding: '4px 12px',
            background: 'var(--color-vault-800)',
            border: '1px solid var(--color-vault-700)',
            borderRadius: '99px',
            fontSize: '11px',
            color: 'var(--color-vault-400)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {hint}
        </span>
      ))}
    </div>
  </div>
);

const MessageBubble: React.FC<{ message: Message; isAdvanced: boolean }> = ({
  message,
  isAdvanced,
}) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div
        className="animate-fade-in-up"
        style={{
          display: 'flex',
          justifyContent: 'center',
          padding: '4px 0',
        }}
      >
        <div
          style={{
            padding: '6px 12px',
            background: 'rgba(248,81,73,0.08)',
            border: '1px solid rgba(248,81,73,0.2)',
            borderRadius: '6px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--color-tele-alert)',
          }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      </div>
    );
  }

  return (
    <div
      className="animate-fade-in-up"
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        gap: '10px',
        alignItems: 'flex-start',
      }}
    >
      {/* Avatar (Grimoire only) */}
      {!isUser && (
        <div
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '8px',
            background: 'var(--color-vault-750)',
            border: '1px solid var(--color-vault-700)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '13px',
            flexShrink: 0,
            marginTop: '4px',
          }}
        >
          🔮
        </div>
      )}

      {/* Bubble */}
      <div
        style={{
          maxWidth: 'min(680px, 85%)',
          background: isUser
            ? 'var(--color-vault-750)'
            : 'var(--color-vault-800)',
          border: `1px solid ${isUser ? 'var(--color-vault-600)' : 'var(--color-vault-700)'}`,
          borderRadius: isUser ? '12px 12px 2px 12px' : '2px 12px 12px 12px',
          padding: '12px 16px',
        }}
      >
        {/* Timestamp & Role */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px',
          }}
        >
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-vault-500)',
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
            }}
          >
            {isUser ? 'você' : 'grimoire'}
          </span>
          {isAdvanced && message.trace_id && !isUser && (
            <span
              style={{
                fontSize: '9px',
                fontFamily: 'var(--font-mono)',
                color: 'var(--color-vault-600)',
                userSelect: 'all',
              }}
            >
              {message.trace_id}
            </span>
          )}
        </div>

        {/* Content */}
        <div className={isUser ? '' : 'prose-vault'}>
          {isUser ? (
            <span style={{ fontSize: '0.875rem', color: 'var(--color-vault-200)' }}>
              {message.content}
            </span>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Advanced Metadata Block */}
        {isAdvanced && !isUser && message.metadata && (
          <MetadataBlock metadata={message.metadata} />
        )}
      </div>
    </div>
  );
};

// ==========================================
// MAIN COMPONENT
// ==========================================

export const IterationHistory: React.FC<IterationHistoryProps> = ({
  messages,
  isProcessing,
}) => {
  const { isAdvanced } = useUi();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  if (messages.length === 0 && !isProcessing) {
    return <EmptyState />;
  }

  return (
    <div
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px 24px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      {messages.map(msg => (
        <MessageBubble key={msg.id} message={msg} isAdvanced={isAdvanced} />
      ))}

      {isProcessing && (
        <div
          className="animate-fade-in-up"
          style={{
            display: 'flex',
            justifyContent: 'flex-start',
            gap: '10px',
            alignItems: 'flex-start',
          }}
        >
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '8px',
              background: 'var(--color-vault-750)',
              border: '1px solid var(--color-vault-700)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '13px',
              flexShrink: 0,
              marginTop: '4px',
            }}
          >
            🔮
          </div>
          <div
            className="vault-surface"
            style={{ borderRadius: '2px 12px 12px 12px', padding: '12px 16px' }}
          >
            <TypingIndicator />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};

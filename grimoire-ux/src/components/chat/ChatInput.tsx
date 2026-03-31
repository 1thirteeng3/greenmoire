import React, { useCallback, useRef, useState, type KeyboardEvent } from 'react';
import type { CognitiveCycleStatus } from '../../types';

interface ChatInputProps {
  onSend: (prompt: string) => void;
  status: CognitiveCycleStatus;
  disabled?: boolean;
}

const STATUS_HINTS: Partial<Record<CognitiveCycleStatus, string>> = {
  classifying: 'Classificando intenção...',
  planning:    'Gerando plano de execução...',
  executing:   'Executando etapas do plano...',
  auditing:    'Auditando saída para conformidade...',
};

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, status, disabled }) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isProcessing = status !== 'idle' && status !== 'completed' && status !== 'error';
  const isDisabled = disabled || isProcessing;

  // Auto-resize textarea
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  };

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isDisabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, isDisabled, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const hint = isProcessing ? STATUS_HINTS[status] : undefined;

  return (
    <div
      style={{
        padding: '12px 16px 16px',
        borderTop: '1px solid var(--color-vault-700)',
        background: 'var(--color-vault-900)',
        flexShrink: 0,
      }}
    >
      {/* Processing hint */}
      {hint && (
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--color-vault-500)',
            marginBottom: '6px',
            paddingLeft: '2px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span
            style={{
              width: '5px',
              height: '5px',
              borderRadius: '50%',
              background: 'var(--color-tele-t3)',
              animation: 'pulse-dot 1s ease-in-out infinite',
              display: 'block',
            }}
          />
          {hint}
        </div>
      )}

      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: '8px',
          background: 'var(--color-vault-800)',
          border: `1px solid ${isProcessing ? 'var(--color-vault-600)' : 'var(--color-vault-700)'}`,
          borderRadius: '8px',
          padding: '8px 8px 8px 14px',
          transition: 'border-color 0.2s',
        }}
        onClick={() => textareaRef.current?.focus()}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
          placeholder={
            isProcessing
              ? 'Processando...'
              : 'Envie uma mensagem ao Grimoire... (Enter para enviar, Shift+Enter para nova linha)'
          }
          rows={1}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            resize: 'none',
            color: isDisabled ? 'var(--color-vault-500)' : 'var(--color-vault-200)',
            fontFamily: 'var(--font-ui)',
            fontSize: '13px',
            lineHeight: 1.6,
            minHeight: '22px',
            maxHeight: '180px',
            overflowY: 'auto',
          }}
          onFocus={e => {
            e.currentTarget.parentElement!.style.borderColor = 'var(--color-vault-500)';
          }}
          onBlur={e => {
            e.currentTarget.parentElement!.style.borderColor = isProcessing
              ? 'var(--color-vault-600)'
              : 'var(--color-vault-700)';
          }}
        />

        {/* Send button */}
        <button
          onClick={handleSubmit}
          disabled={isDisabled || !value.trim()}
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '6px',
            background:
              isDisabled || !value.trim()
                ? 'var(--color-vault-700)'
                : 'var(--color-tele-t1)',
            border: 'none',
            cursor: isDisabled || !value.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            transition: 'all 0.2s',
            opacity: isDisabled ? 0.5 : 1,
          }}
        >
          {isProcessing ? (
            // Spinner
            <svg
              width="14"
              height="14"
              viewBox="0 0 14 14"
              fill="none"
              style={{ animation: 'spin 1s linear infinite' }}
            >
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              <circle
                cx="7" cy="7" r="5"
                stroke="var(--color-vault-400)"
                strokeWidth="1.5"
                strokeDasharray="20"
                strokeDashoffset="10"
              />
            </svg>
          ) : (
            // Arrow up
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M7 11V3M7 3L3.5 6.5M7 3L10.5 6.5"
                stroke={!value.trim() ? 'var(--color-vault-500)' : 'white'}
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </button>
      </div>

      {/* Keyboard hint */}
      <div
        style={{
          marginTop: '6px',
          textAlign: 'right',
          fontFamily: 'var(--font-mono)',
          fontSize: '9px',
          color: 'var(--color-vault-700)',
        }}
      >
        ↵ enviar · Shift+↵ nova linha
      </div>
    </div>
  );
};

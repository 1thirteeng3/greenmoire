
import { useUi } from '../contexts/UiContext';
import ReactMarkdown from 'react-markdown';

// Tipagem baseada na resposta da nossa API FastAPI
export interface MessagePayload {
  id: string;
  role: 'user' | 'grimoire';
  content: string;
  metadata?: {
    tier_used?: string;
    primary_intent?: string;
    agent_selected?: string;
    auditor_critique?: string;
    execution_time_ms?: number;
  };
}

export const CognitiveMessage: React.FC<{ message: MessagePayload }> = ({ message }) => {
  const { mode } = useUi();
  const isUser = message.role === 'user';

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div className={`max-w-3xl w-full flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
        
        {/* Renderização do Texto Principal (Comum a ambos os modos) */}
        <div className={`
          px-6 py-4 rounded-xl shadow-sm
          ${isUser ? 'bg-vault-700 text-white rounded-br-none' : 'bg-vault-800 text-gray-300 rounded-bl-none border border-vault-700'}
        `}>
          <article className="prose prose-invert prose-p:leading-relaxed prose-pre:bg-vault-900 max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </article>
        </div>

        {/* ========================================== */}
        {/* MODO ADVANCED: Telemetria e Observabilidade */}
        {/* ========================================== */}
        {!isUser && mode === 'advanced' && message.metadata && (
          <div className="w-full mt-1 bg-vault-900 border border-vault-700 rounded-lg p-3 text-xs font-mono text-gray-400 shadow-inner">
            <div className="flex items-center justify-between border-b border-vault-700 pb-2 mb-2">
              <span className="text-cognitive-t1 font-bold">TRACE ID: {message.id}</span>
              <span className="text-gray-500">{message.metadata.execution_time_ms}ms</span>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="block text-gray-500 mb-1">ROTEAMENTO COGNITIVO</span>
                <div className="flex flex-col gap-1">
                  <span>Intenção: <span className="text-white">{message.metadata.primary_intent}</span></span>
                  <span>Camada: <span className={`
                    ${message.metadata.tier_used === 'T1' ? 'text-cognitive-t1' : ''}
                    ${message.metadata.tier_used === 'T2' ? 'text-cognitive-t2' : ''}
                    ${message.metadata.tier_used === 'T3' ? 'text-cognitive-t3' : ''}
                  `}>{message.metadata.tier_used}</span></span>
                  {message.metadata.agent_selected && (
                    <span>Persona: <span className="text-white">{message.metadata.agent_selected}</span></span>
                  )}
                </div>
              </div>

              {message.metadata.auditor_critique && (
                <div>
                  <span className="block text-gray-500 mb-1">AUDITORIA (Red Team)</span>
                  <div className={`p-2 rounded bg-vault-800 border-l-2 ${message.metadata.auditor_critique === 'OK' ? 'border-cognitive-success text-cognitive-success' : 'border-cognitive-alert text-cognitive-alert'}`}>
                    {message.metadata.auditor_critique}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        
      </div>
    </div>
  );
};

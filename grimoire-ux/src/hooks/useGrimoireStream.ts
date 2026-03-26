import { useState, useEffect, useRef, useCallback } from 'react';
import type { MessagePayload } from '../components/CognitiveMessage';

export const useGrimoireStream = () => {
  const [messages, setMessages] = useState<MessagePayload[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Inicializa o WebSocket
  useEffect(() => {
    // Altere para a porta do seu FastAPI
    const ws = new WebSocket('ws://127.0.0.1:8000/api/v1/stream/ws');
    
    ws.onopen = () => {
      console.log('Conectado ao Cérebro do Grimoire.');
      setIsConnected(true);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'status') {
        setStatusText(data.message);
      } 
      else if (data.type === 'final_response') {
        setIsProcessing(false);
        setStatusText('');
        setMessages((prev) => [
          ...prev, 
          {
            id: data.trace_id,
            role: 'grimoire',
            content: data.content,
            metadata: data.metadata
          }
        ]);
      }
    };

    ws.onclose = () => {
      console.log('Desconectado do Cérebro do Grimoire.');
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('Erro no WebSocket:', error);
      setIsProcessing(false);
      setIsConnected(false);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, []);

  const sendMessage = useCallback((prompt: string) => {
    if (!prompt.trim() || !wsRef.current) return;

    if (wsRef.current.readyState === WebSocket.OPEN) {
      const traceId = `usr-${Math.random().toString(36).substring(2, 9)}`;
      
      // Adiciona a mensagem do usuário na tela instantaneamente
      setMessages((prev) => [...prev, { id: traceId, role: 'user', content: prompt }]);
      setIsProcessing(true);
      setStatusText('Injetando evento no barramento...');

      // Envia o JSON pelo WebSocket
      wsRef.current.send(JSON.stringify({ prompt }));
    } else {
      console.warn('WebSocket não está conectado. Mensagem ignorada.');
    }
  }, []);

  return {
    messages,
    sendMessage,
    isProcessing,
    statusText,
    isConnected
  };
};

import React, { useState } from 'react';
import { UiProvider } from './contexts/UiContext';
import { TopBar } from './components/TopBar';
import { CognitiveMessage } from './components/CognitiveMessage';
import { useGrimoireStream } from './hooks/useGrimoireStream';

function App() {
  const { messages, sendMessage, isProcessing, statusText, isConnected } = useGrimoireStream();
  const [inputValue, setInputValue] = useState('');

  const handleSend = () => {
    if (inputValue.trim() && !isProcessing) {
      sendMessage(inputValue);
      setInputValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <UiProvider>
      <div className="flex flex-col h-screen">
        <TopBar />
        
        <main className="flex-1 overflow-y-auto w-full">
          <div className="max-w-4xl mx-auto px-6 py-8 pb-32">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center mt-20 opacity-50">
                <div className="w-16 h-16 rounded mb-4 bg-gradient-to-br from-cognitive-t1 to-cognitive-t2 flex items-center justify-center font-bold text-white text-2xl">
                  G
                </div>
                <h2 className="text-xl font-semibold text-white mb-2">Bem-vindo ao Grimoire OS</h2>
                <p className="text-sm font-mono">Conectado. Aguardando input cognitivo...</p>
              </div>
            ) : (
              messages.map((msg, index) => (
                <CognitiveMessage key={index} message={msg} />
              ))
            )}

            {isProcessing && (
              <div className="flex justify-start mb-6">
                <div className="max-w-3xl flex items-center gap-3 text-sm font-mono text-cognitive-t1 animate-pulse px-6 py-4">
                  <span className="w-2 h-2 bg-cognitive-t1 rounded-full inline-block"></span>
                  {statusText || 'Processando...'}
                </div>
              </div>
            )}
          </div>
        </main>
        
        <footer className="fixed bottom-0 w-full bg-vault-900 border-t border-vault-700/50 p-4">
          <div className="max-w-4xl mx-auto relative">
            {!isConnected && (
              <div className="absolute -top-10 left-0 w-full text-center">
                <span className="text-xs bg-red-500/10 text-red-400 border border-red-500/20 px-3 py-1 rounded-full">
                  ⚠️ Cérebro Offline (FastAPI não está a correr no porto 8000)
                </span>
              </div>
            )}
            <input 
              type="text" 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isConnected ? "Pergunte ao Grimoire..." : "Conexão de rede indisponível..."}
              className="w-full bg-vault-800 border border-vault-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:border-cognitive-t1 transition-colors disabled:opacity-50"
              disabled={isProcessing || !isConnected}
            />
            <button 
              onClick={handleSend}
              disabled={!inputValue.trim() || isProcessing || !isConnected}
              className="absolute right-2 top-1.5 p-1.5 bg-vault-700 text-gray-400 rounded-md hover:text-white hover:bg-vault-600 transition-colors disabled:opacity-50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
          </div>
        </footer>
      </div>
    </UiProvider>
  );
}

export default App;

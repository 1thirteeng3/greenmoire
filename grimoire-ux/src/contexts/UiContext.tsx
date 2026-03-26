import { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

type UiMode = 'standard' | 'advanced';

interface UiContextType {
  mode: UiMode;
  toggleMode: () => void;
}

const UiContext = createContext<UiContextType | undefined>(undefined);

export const UiProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<UiMode>('standard');

  const toggleMode = () => {
    setMode((prev) => (prev === 'standard' ? 'advanced' : 'standard'));
  };

  return (
    <UiContext.Provider value={{ mode, toggleMode }}>
      <div className="min-h-screen bg-vault-900 text-gray-200 font-sans selection:bg-cognitive-t1 selection:text-vault-900">
        {children}
      </div>
    </UiContext.Provider>
  );
};

export const useUi = () => {
  const context = useContext(UiContext);
  if (!context) throw new Error('useUi deve ser usado dentro de um UiProvider');
  return context;
};

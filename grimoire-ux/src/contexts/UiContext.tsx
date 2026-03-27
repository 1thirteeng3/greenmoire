import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { UiMode } from '../types';

interface UiContextData {
  mode: UiMode;
  toggleMode: () => void;
  isAdvanced: boolean;
}

const UiContext = createContext<UiContextData | undefined>(undefined);

const STORAGE_KEY = 'grimoire:ui_mode';

export const UiProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<UiMode>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return (stored === 'advanced' ? 'advanced' : 'standard') as UiMode;
    } catch {
      return 'standard';
    }
  });

  const toggleMode = () => {
    setMode(prev => {
      const next = prev === 'standard' ? 'advanced' : 'standard';
      try { localStorage.setItem(STORAGE_KEY, next); } catch { /* noop */ }
      return next;
    });
  };

  // Apply mode class to body for global CSS hooks
  useEffect(() => {
    if (mode === 'advanced') {
      document.body.classList.add('advanced-mode');
    } else {
      document.body.classList.remove('advanced-mode');
    }
  }, [mode]);

  return (
    <UiContext.Provider value={{ mode, toggleMode, isAdvanced: mode === 'advanced' }}>
      {children}
    </UiContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useUi = (): UiContextData => {
  const ctx = useContext(UiContext);
  if (!ctx) throw new Error('useUi must be used within UiProvider');
  return ctx;
};

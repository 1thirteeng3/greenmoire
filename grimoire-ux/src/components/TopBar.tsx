
import { useUi } from '../contexts/UiContext';

export const TopBar: React.FC = () => {
  const { mode, toggleMode } = useUi();

  return (
    <header className="sticky top-0 z-10 bg-vault-900/80 backdrop-blur-md border-b border-vault-700 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-gradient-to-br from-cognitive-t1 to-cognitive-t2 flex items-center justify-center font-bold text-white">
          G
        </div>
        <h1 className="font-sans font-semibold text-lg tracking-wide text-gray-100">
          Grimoire <span className="text-gray-500 font-normal text-sm">OS</span>
        </h1>
      </div>

      <button
        onClick={toggleMode}
        className={`
          flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-mono transition-colors border
          ${mode === 'advanced' 
            ? 'bg-cognitive-alert/10 border-cognitive-alert/50 text-cognitive-alert' 
            : 'bg-vault-800 border-vault-700 text-gray-400 hover:text-white'}
        `}
      >
        <span className={`w-2 h-2 rounded-full ${mode === 'advanced' ? 'bg-cognitive-alert animate-pulse' : 'bg-gray-500'}`}></span>
        {mode === 'advanced' ? 'ADVANCED MODE ON' : 'STANDARD MODE'}
      </button>
    </header>
  );
};

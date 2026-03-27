import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import { UiProvider } from './contexts/UiContext.tsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <UiProvider>
      <App />
    </UiProvider>
  </React.StrictMode>,
);

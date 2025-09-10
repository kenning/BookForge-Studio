import React, { createContext, useContext, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import VoiceModesPage from './voice-modes-page/VoiceModesPage';
import ActorsPage from './actors-page/ActorsPage';
import TextWorkflowsPage from './text-workflows-page/TextWorkflowsPage';
import TimelinePage from './timeline-page/TimelinePage';
import { webSocketService } from './services/websocketService';
import { useLogPanelStore } from './store/logPanelStore';
import './themes.css';
import './App.css';

// Theme context
interface ThemeContextType {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Initialize theme from localStorage immediately to avoid flash
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    // Check for saved theme preference first
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
    if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
      return savedTheme;
    }
    // Fall back to system preference, but default to dark
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    // Default to dark
    return 'dark';
  });

  useEffect(() => {
    // Apply theme to document root and save to localStorage
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
};

function App() {
  const { addLog, setConnected } = useLogPanelStore();

  useEffect(() => {
    // Set up log handlers (these can be reset on remount)
    webSocketService.setHandlers({
      onLog: data => {
        addLog(data.message);
      },
      onError: data => {
        addLog(`❌ Error: ${data.error}`);
      },
    });

    setConnected(true);
    addLog('✅ Connected to log stream via WebSocket');

    // Don't disconnect on cleanup - let the connection persist
    return () => {
      // no-op
    };
  }, [addLog, setConnected]);

  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/text-workflows" replace />} />
          <Route path="/voice-modes" element={<VoiceModesPage />} />
          <Route path="/actors" element={<ActorsPage />} />
          <Route path="/text-workflows" element={<TextWorkflowsPage />} />
          <Route path="/timeline" element={<TimelinePage />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;

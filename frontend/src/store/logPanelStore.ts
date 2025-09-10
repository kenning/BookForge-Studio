import { create } from 'zustand';

interface LogPanelState {
  isOpen: boolean;
  logs: string[];
  isConnected: boolean;
  isAutoScroll: boolean;

  // Actions
  openPanel: () => void;
  closePanel: () => void;
  togglePanel: () => void;
  addLog: (log: string) => void;
  clearLogs: () => void;
  setConnected: (connected: boolean) => void;
  setAutoScroll: (autoScroll: boolean) => void;
}

export const useLogPanelStore = create<LogPanelState>((set, get) => ({
  isOpen: false,
  logs: [],
  isConnected: false,
  isAutoScroll: true,

  openPanel: () => set({ isOpen: true }),
  closePanel: () => set({ isOpen: false }),
  togglePanel: () => set(state => ({ isOpen: !state.isOpen })),

  addLog: (log: string) =>
    set(state => ({
      logs: [...state.logs, log].slice(-1000), // Keep only last 1000 logs to prevent memory issues
    })),

  clearLogs: () => set({ logs: [] }),

  setConnected: (connected: boolean) => set({ isConnected: connected }),

  setAutoScroll: (autoScroll: boolean) => set({ isAutoScroll: autoScroll }),
}));

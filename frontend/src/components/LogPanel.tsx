import React, { useEffect, useRef } from 'react';
import { useLogPanelStore } from '../store/logPanelStore';
import { logsApi } from '../api/api';

interface LogPanelProps {
  className?: string;
}

const logLevelColors = {
  DEBUG: 'var(--text-tertiary)',
  INFO: 'var(--accent-primary)',
  WARNING: 'var(--accent-warning)',
  ERROR: 'var(--accent-danger)',
};

const LogPanel: React.FC<LogPanelProps> = ({ className = '' }) => {
  const {
    isOpen,
    logs,
    isConnected,
    isAutoScroll,
    openPanel,
    closePanel,
    addLog,
    clearLogs,
    setAutoScroll,
  } = useLogPanelStore();

  const logContainerRef = useRef<HTMLDivElement>(null);

  // Load historical logs when panel opens for the first time
  useEffect(() => {
    if (isOpen && logs.length === 0) {
      logsApi
        .getLogHistory(50)
        .then(response => {
          response.lines.forEach(line => addLog(line));
        })
        .catch(console.error);
    }
  }, [isOpen, logs.length, addLog]);

  // WebSocket connection is now handled at the app level

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (isAutoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, isAutoScroll]);

  const toggleCollapsed = () => {
    if (isOpen) {
      closePanel();
    } else {
      openPanel();
    }
  };

  return (
    <div className={`log-panel ${isOpen ? 'expanded' : 'collapsed'} ${className}`}>
      {/* Handle area - always visible and clickable */}
      <div className="log-panel-handle" onClick={toggleCollapsed}>
        <span className="log-panel-handle-text">
          {isOpen ? '↓' : '↑'} Server Logs
          {isOpen && (
            <span className={`connection-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
              {isConnected ? '●' : '○'}
            </span>
          )}
        </span>
      </div>

      {/* Content area - only visible when expanded */}
      {isOpen && (
        <>
          <div className="log-panel-controls">
            <label className="auto-scroll-checkbox">
              <input
                type="checkbox"
                checked={isAutoScroll}
                onChange={e => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>

            <button onClick={closePanel} className="hide-logs-btn" title="Hide">
              <span style={{ fontWeight: 800 }}>Hide logs</span>
            </button>

            <button onClick={clearLogs} className="clear-logs-btn" title="Clear logs">
              Clear
            </button>
          </div>

          <div ref={logContainerRef} className="log-content">
            {logs.map((log, index) => {
              const splitLog = log.split(' - ');
              const logLevel = splitLog[0];
              const logColor = logLevelColors[logLevel as keyof typeof logLevelColors];
              const logMessage = splitLog.slice(2).join(' - ');

              return (
                <div key={index} className="log-entry">
                  <span style={{ color: logColor }}>{splitLog[0]}</span>{' '}
                  <span style={{ color: 'var(--text-tertiary)' }}>{splitLog[1]}</span>{' '}
                  <span>{logMessage}</span>
                </div>
              );
            })}
            {logs.length === 0 && (
              <div className="log-entry placeholder">
                {isConnected
                  ? 'Connected to log stream. Waiting for logs...'
                  : 'Connecting to log stream...'}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default LogPanel;

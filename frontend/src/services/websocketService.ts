/**
 * Centralized WebSocket service for managing a single persistent connection
 * and routing messages to appropriate handlers
 */

export interface WebSocketHandlers {
  onLog?: (data: any) => void;
  onPong?: () => void;
  onError?: (data: any) => void;
  onExecutionProgress?: (data: any) => void;
  onExecutionComplete?: (data: any) => void;
  onExecutionError?: (data: any) => void;
  onTextWorkflowProgress?: (data: any) => void;
  onTextWorkflowComplete?: (data: any) => void;
  onTextWorkflowError?: (data: any) => void;
  onExportStart?: (data: any) => void;
  onExportProgress?: (data: any) => void;
  onExportComplete?: (data: any) => void;
  onExportError?: (data: any) => void;
}

class WebSocketService {
  private websocket: WebSocket | null = null;
  private handlers: WebSocketHandlers = {};
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isIntentionallyClosed = false;
  private baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  /**
   * Set handlers for WebSocket messages
   */
  setHandlers(handlers: WebSocketHandlers): void {
    this.handlers = { ...this.handlers, ...handlers };
  }

  /**
   * Clear specific handlers
   */
  clearHandlers(handlerKeys: (keyof WebSocketHandlers)[]): void {
    handlerKeys.forEach(key => {
      delete this.handlers[key];
    });
  }

  /**
   * Initialize the WebSocket connection
   */
  initialize(): void {
    if (!this.websocket) {
      this.connect();
    }
  }

  /**
   * Get the current WebSocket instance (for sending messages)
   */
  getWebSocket(): WebSocket | null {
    return this.websocket;
  }

  /**
   * Send a message via WebSocket
   */
  send(message: string): void {
    if (this.websocket?.readyState === WebSocket.OPEN) {
      this.websocket.send(message);
    }
  }

  private connect(): void {
    if (this.isConnecting || this.websocket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isConnecting = true;
    this.isIntentionallyClosed = false;

    try {
      this.websocket = this.createConnection();

      this.websocket.onopen = () => {
        this.isConnecting = false;
      };

      this.websocket.onmessage = event => {
        try {
          const message = JSON.parse(event.data);
          // console.log('WebSocketService: Message:', message);

          // Route message to handlers
          switch (message.type) {
            case 'log':
              this.handlers.onLog?.(message.data);
              break;
            case 'pong':
              this.handlers.onPong?.();
              break;
            case 'log_error':
              this.handlers.onError?.(message.data);
              break;
            case 'execution_progress':
              this.handlers.onExecutionProgress?.(message);
              break;
            case 'execution_complete':
              this.handlers.onExecutionComplete?.(message);
              break;
            case 'execution_error':
              this.handlers.onExecutionError?.(message);
              break;
            case 'text-workflow-progress':
              this.handlers.onTextWorkflowProgress?.(message);
              break;
            case 'text-workflow-complete':
              this.handlers.onTextWorkflowComplete?.(message);
              break;
            case 'text-workflow-error':
              this.handlers.onTextWorkflowError?.(message);
              break;
            case 'export-start':
              this.handlers.onExportStart?.(message);
              break;
            case 'export-progress':
              this.handlers.onExportProgress?.(message);
              break;
            case 'export-complete':
              this.handlers.onExportComplete?.(message);
              break;
            case 'export-error':
              this.handlers.onExportError?.(message);
              break;
            default:
              console.log('WebSocketService: Unknown message type:', message.type);
          }
        } catch (error) {
          console.error('WebSocketService: Error parsing message:', error);
        }
      };

      this.websocket.onclose = event => {
        this.isConnecting = false;
        this.websocket = null;

        // Attempt reconnection if not intentionally closed
        if (!this.isIntentionallyClosed && event.code !== 1000) {
          this.reconnectTimeout = setTimeout(() => {
            this.connect();
          }, 3000);
        }
      };

      this.websocket.onerror = error => {
        console.error('WebSocketService: Error:', error);
        this.isConnecting = false;

        // Notify handlers of error
        this.handlers.onError?.({ error: 'WebSocket connection error' });
      };
    } catch (error) {
      console.error('WebSocketService: Failed to create connection:', error);
      this.isConnecting = false;
    }
  }

  /**
   * Disconnect the WebSocket connection
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.websocket) {
      this.websocket.close(1000, 'Service shutdown');
      this.websocket = null;
    }
  }

  /**
   * Create WebSocket connection for real-time updates
   */
  createConnection(): WebSocket {
    let baseUrl = this.baseUrl;
    if (baseUrl === 'no_port') baseUrl = '';
    const wsUrl = baseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    return new WebSocket(`${wsUrl}/ws/connect`);
  }

  /**
   * Create WebSocket connection for logs only
   */
  createLogsConnection(): WebSocket {
    let baseUrl = this.baseUrl;
    if (baseUrl === 'no_port') baseUrl = '';
    const wsUrl = baseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    return new WebSocket(`${wsUrl}/ws/logs-only`);
  }

  /**
   * Send ping to keep connection alive
   */
  ping(): void {
    if (this.websocket?.readyState === WebSocket.OPEN) {
      this.websocket.send('ping');
    }
  }

  /**
   * Request task list via WebSocket
   */
  requestTaskList(): void {
    if (this.websocket?.readyState === WebSocket.OPEN) {
      this.websocket.send('get_tasks');
    }
  }
}

// Export singleton instance
export const webSocketService = new WebSocketService();

// Add cleanup on page unload to gracefully disconnect WebSocket
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    webSocketService.disconnect();
  });
}

// Initialize connection immediately when module loads
webSocketService.initialize();

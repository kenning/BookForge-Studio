import {
  FileListResponse,
  TextContentResponse,
  GenericSaveRequest,
  GenericSaveResponse,
  StepExecutionRequest,
  Script,
  Step,
  ModelMetadata,
  ServicesStatusResponse,
  TextToScriptViaOllamaRequest,
  LoadScriptResponse,
} from '../types/readableBackendTypes';

let BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
if (BASE_URL === 'no_port') BASE_URL = '';

// Generic API error handling
class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = 'Request failed';
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // If we can't parse error, use status text
      errorMessage = response.statusText || errorMessage;
    }
    throw new ApiError(response.status, errorMessage);
  }
  return response.json();
}

// File system API
export const filesApi = {
  /**
   * List files in a directory
   */
  async listFiles(directoryType: string): Promise<FileListResponse> {
    const response = await fetch(`${BASE_URL}/api/files/list?directory_type=${directoryType}`);
    return handleApiResponse<FileListResponse>(response);
  },

  /**
   * Get text content of a file
   */
  async getTextContent(filePath: string): Promise<TextContentResponse> {
    const response = await fetch(`${BASE_URL}/api/files/textcontent/${filePath}`);
    return handleApiResponse<TextContentResponse>(response);
  },

  /**
   * Save a file
   */
  async saveFile(request: GenericSaveRequest): Promise<GenericSaveResponse> {
    const response = await fetch(`${BASE_URL}/api/files/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return handleApiResponse<GenericSaveResponse>(response);
  },

  /**
   * Load a script file
   */
  async loadScript(filename: string): Promise<LoadScriptResponse> {
    const response = await fetch(`${BASE_URL}/api/files/load-script/${filename}`);
    return handleApiResponse<LoadScriptResponse>(response);
  },

  /**
   * Save a script file
   */
  async saveScript(
    directoryType: string,
    filename: string,
    script: Script
  ): Promise<GenericSaveResponse> {
    const response = await fetch(`${BASE_URL}/api/files/save-script`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory_type: directoryType,
        filename,
        script,
      }),
    });
    return handleApiResponse<GenericSaveResponse>(response);
  },

  /**
   * Export timeline by concatenating all active audio clips
   */
  async exportTimeline(
    script: Script,
    outputSubfolder: string
  ): Promise<{ message: string; output_file_path: string }> {
    const response = await fetch(`${BASE_URL}/api/files/export-timeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        script,
        output_subfolder: outputSubfolder,
      }),
    });
    return handleApiResponse<{ message: string; output_file_path: string }>(response);
  },

  /**
   * Get a file URL for serving (audio, etc.)
   */
  getFileUrl(filename: string): string {
    return `${BASE_URL}/api/files/serve/${filename}`;
  },

  /**
   * Upload a file from desktop drag and drop
   */
  async uploadFile(file: File): Promise<{
    filename: string;
    original_filename: string;
    file_path: string;
    file_info: any;
  }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${BASE_URL}/api/files/upload`, {
      method: 'POST',
      body: formData,
    });

    return handleApiResponse(response);
  },
};

// Steps API
export const stepsApi = {
  /**
   * Get all available steps
   */
  async getSteps(): Promise<Step[]> {
    const response = await fetch(`${BASE_URL}/api/steps/`);
    return handleApiResponse<Step[]>(response);
  },

  /**
   * Execute a workflow in the background (non-blocking - returns execution ID)
   */
  async executeWorkflowBackground(
    request: StepExecutionRequest
  ): Promise<{ execution_id: string }> {
    console.log('Executing workflow background', request);
    const response = await fetch(`${BASE_URL}/api/steps/execute-background`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    return handleApiResponse<{ execution_id: string }>(response);
  },
};

// Text Workflows API
export const textWorkflowsApi = {
  /**
   * Execute text workflow in background and return execution ID (results via WebSocket)
   */
  async executeWorkflowBackground(request: {
    workflow_name: string;
    parameters: any;
  }): Promise<{ execution_id: string }> {
    console.log('Executing workflow background', request);
    const response = await fetch(`${BASE_URL}/api/text-workflows/${request.workflow_name}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request.parameters),
    });
    return handleApiResponse<{ execution_id: string }>(response);
  },

  /**
   * Convert CSV file to Script object (background execution with websocket)
   */
  async csvToPsss(request: { filepath: string }): Promise<{ execution_id: string }> {
    return this.executeWorkflowBackground({
      workflow_name: 'csv-to-psss',
      parameters: request,
    });
  },

  /**
   * Convert text to Script object (background execution with websocket)
   */
  async textToPsss(request: { text: string }): Promise<{ execution_id: string }> {
    return this.executeWorkflowBackground({
      workflow_name: 'text-to-psss',
      parameters: request,
    });
  },

  /**
   * Process text file or text input using Gemini LLM API (background execution with websocket)
   */
  async textToLlmApi(request: {
    filepath?: string;
    text?: string;
    api_key: string;
  }): Promise<{ execution_id: string }> {
    return this.executeWorkflowBackground({
      workflow_name: 'text-to-llm-api',
      parameters: request,
    });
  },

  /**
   * Process text using local Ollama LLM (background execution with websocket)
   */
  async textToScriptViaOllama(
    request: TextToScriptViaOllamaRequest
  ): Promise<{ execution_id: string }> {
    return this.executeWorkflowBackground({
      workflow_name: 'text-to-script-via-ollama',
      parameters: request,
    });
  },
};

// Models API
export const modelsApi = {
  /**
   * Get all available models and their default workflow configurations
   */
  async getModels(): Promise<{ models: ModelMetadata[] }> {
    const response = await fetch(`${BASE_URL}/api/models/`);
    const result = await handleApiResponse<{ models: ModelMetadata[] }>(response);
    return result;
  },

  /**
   * Reload all model workflows (for development)
   */
  async reloadModels(): Promise<{ message: string }> {
    const response = await fetch(`${BASE_URL}/api/models/reload`, {
      method: 'POST',
    });
    return handleApiResponse(response);
  },

  /**
   * Get status of all microservices
   */
  async getServicesStatus(): Promise<ServicesStatusResponse> {
    const response = await fetch(`${BASE_URL}/api/models/status`);
    return handleApiResponse<ServicesStatusResponse>(response);
  },
};

// Logs API
export const logsApi = {
  /**
   * Get recent log history
   */
  async getLogHistory(
    lines: number = 100
  ): Promise<{ lines: string[]; total_lines: number; requested_lines: number }> {
    const response = await fetch(`${BASE_URL}/api/logs/history?lines=${lines}`);
    return handleApiResponse(response);
  },

  /**
   * Create EventSource for real-time log streaming
   */
  createLogStream(): EventSource {
    return new EventSource(`${BASE_URL}/api/logs/stream`);
  },
};

export { ApiError };

import { create } from 'zustand';
import {
  ActorData,
  FileInfo,
  Script,
  ScriptHistoryGridCell,
  StepExecutionRequest,
} from '../../types/readableBackendTypes';
import { filesApi, stepsApi, ApiError } from '../../api/api';
import { webSocketService } from '../../services/websocketService';

// Utility function to sanitize a string for use as a folder name
const sanitizeFolderName = (input: string): string => {
  if (!input || typeof input !== 'string') {
    throw new Error('Need project title');
  }

  // Replace spaces and common punctuation with underscores
  let sanitized = input
    // eslint-disable-next-line no-useless-escape
    .replace(/[\s\-\.]+/g, '_') // spaces, hyphens, dots -> underscores
    .replace(/[^\w]/g, '') // remove all non-alphanumeric and non-underscore characters
    .replace(/_+/g, '_') // collapse multiple underscores into one
    .replace(/^_+|_+$/g, '') // remove leading/trailing underscores
    .toLowerCase(); // convert to lowercase for consistency and mac issue

  // Ensure the result is not empty and not too long
  if (!sanitized) {
    return 'untitled_project';
  }

  // Limit length to avoid filesystem issues
  if (sanitized.length > 50) {
    sanitized = sanitized.substring(0, 50).replace(/_+$/, '');
  }

  // Ensure it doesn't start with a number (some systems don't like this)
  if (/^\d/.test(sanitized)) {
    sanitized = 'project_' + sanitized;
  }

  return sanitized;
};

const MAX_PROCESSING_ITEMS = 3;

// Waveform peak generation function
export const generateWaveformPeaks = async (
  audioUrl: string,
  numPeaks: number = 40
): Promise<number[]> => {
  try {
    const response = await fetch(audioUrl);
    const arrayBuffer = await response.arrayBuffer();

    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

    const channelData = audioBuffer.getChannelData(0); // Use first channel
    const blockSize = Math.floor(channelData.length / numPeaks);
    const peaks: number[] = [];

    for (let i = 0; i < numPeaks; i++) {
      let max = 0;
      const start = i * blockSize;
      const end = Math.min(start + blockSize, channelData.length);

      for (let j = start; j < end; j++) {
        const value = Math.abs(channelData[j]);
        if (value > max) {
          max = value;
        }
      }
      peaks[i] = max;
    }

    audioContext.close();
    return peaks;
  } catch (error) {
    throw new Error('Error generating waveform peaks:' + error);
  }
};

export const generateCellKey = (rowIndex: number, cellIndex: number) => `${rowIndex}-${cellIndex}`;

// Generation queue item
export interface GenerationQueueItem {
  id: string;
  executionId: string;
  rowIndex: number;
  cellIndex: number;
  texts: string[];
  actors: ActorData[]; // Changed from single actor to array of actors
  voiceMode: FileInfo;
  // voiceClonePath?: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  error?: string;
  // Progress information
  progress?: {
    percentage: number;
    stepName: string;
    timestamp: string;
    stepNum: number;
    totalSteps: number;
  };
}

interface TimelineGenerationState {
  // Data
  script: Script | null;
  setScript: (script: Script) => void;
  setScriptAndMarkDirty: (script: Script) => void;
  setDirty: (isDirty: boolean) => void;

  actors: FileInfo[];
  voiceModes: FileInfo[];
  generationQueue: GenerationQueueItem[];

  // Saving and ui state
  handleSaveScript: () => Promise<void>;
  isLoading: boolean;
  setIsLoading: (isLoading: boolean) => void;
  isSaving: boolean;
  currentScriptName: string;
  setCurrentScriptName: (name: string) => void;
  hasChangedSinceLastSave: boolean;
  isLoadingActors: boolean;
  isLoadingVoiceModes: boolean;
  isProcessingQueue: boolean;
  error: string | null;

  // Export state
  isExporting: boolean;
  exportProgress: number;
  exportStepName: string;
  exportedFilePath: string | null;

  // Background execution state
  websocket: WebSocket | null;

  // Actions
  loadActors: () => Promise<void>;
  loadVoiceModes: () => Promise<void>;
  enqueueCells: (selectedCells: Set<string>) => void;
  processQueue: () => Promise<void>;
  clearQueue: () => void;
  generateOneMissingWaveform: (rowIndex: number, cellIndex: number) => Promise<boolean>;
  generateMissingWaveformsAndCheckStatus: () => Promise<void>;
  setError: (error: string | null) => void;
  updateCellInScript: (
    rowIndex: number,
    cellIndex: number,
    updates: Partial<ScriptHistoryGridCell>,
    markDirty: boolean
  ) => void;

  // Export actions
  exportCurrentTimeline: () => Promise<void>;

  // Background task actions
  initializeWebSocket: () => void;
  disconnectWebSocket: () => void;
  handleEnqueueGeneration: (rowIndex: number, cellIndex: number) => void;
}

export const useTimelineGenerationStore = create<TimelineGenerationState>((set, get) => {
  const handleSaveScript = async () => {
    const { currentScriptName, setError, script } = get();
    try {
      if (!script) {
        setError('No script to save');
        return;
      }
      set({ isSaving: true, error: null });
      script.title = currentScriptName;
      console.log('saving script', currentScriptName, script);

      let filename = currentScriptName;

      // If no current script name, prompt for one
      if (!filename) {
        const userFilename = prompt('Enter script filename (without .json extension):');
        if (!userFilename) {
          set({ isSaving: false });
          return;
        }
        filename = userFilename;
      }

      // Ensure filename ends with .json
      if (!filename.endsWith('.json')) {
        filename += '.json';
      }

      await filesApi.saveScript('scripts', filename, script);
      set({ currentScriptName: filename.replace(/\.json$/, '') });

      // Update save states
      set({ hasChangedSinceLastSave: false });
    } catch (err) {
      const errorMessage =
        err instanceof ApiError ? err.message : 'Failed to save script: ' + (err as Error).message;
      setError(errorMessage);
    } finally {
      set({ isSaving: false });
    }
  };

  // Helper functions for queue management
  const findQueueItemByExecutionId = (executionId: string): GenerationQueueItem | null => {
    const state = get();
    const queueItem = state.generationQueue.find(item => item.executionId === executionId);
    return queueItem || null;
  };

  const updateQueueItem = (queueItemId: string, updates: Partial<GenerationQueueItem>) => {
    const previous = get().generationQueue.find(item => item.id === queueItemId);
    if (previous?.status === 'completed') {
      // Avoid race conditions by not updating the queue item if it's completed
      return;
    }

    set(state => ({
      generationQueue: state.generationQueue.map(item =>
        item.id === queueItemId ? { ...item, ...updates } : item
      ),
    }));
  };

  return {
    // Initial state
    script: null,
    setScript: (script: Script) => set({ script }),
    setScriptAndMarkDirty: (script: Script) => set({ script, hasChangedSinceLastSave: true }),
    setDirty: (isDirty: boolean) => set({ hasChangedSinceLastSave: isDirty }),
    handleSaveScript,
    isSaving: false,
    currentScriptName: '',
    setCurrentScriptName: (name: string) =>
      set({
        currentScriptName: name,
      }),
    actors: [],
    voiceModes: [],
    generationQueue: [],
    isLoadingActors: false,
    isLoadingVoiceModes: false,
    isProcessingQueue: false,
    error: null,
    hasChangedSinceLastSave: false,
    isLoading: false,
    setIsLoading: (isLoading: boolean) => set({ isLoading }),
    // Export state
    isExporting: false,
    exportProgress: 0,
    exportStepName: '',
    exportedFilePath: null,
    // Background execution state
    websocket: null,

    // Actions
    loadActors: async () => {
      try {
        set({ isLoadingActors: true, error: null });
        const response = await filesApi.listFiles('actors');
        set({ actors: response.flat_files || [] });
      } catch (err) {
        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to load actors: ' + (err as Error).message;
        set({ error: errorMessage });
      } finally {
        set({ isLoadingActors: false });
      }
    },

    loadVoiceModes: async () => {
      try {
        set({ isLoadingVoiceModes: true, error: null });
        const response = await filesApi.listFiles('voice_modes');
        set({ voiceModes: response.flat_files || [] });
      } catch (err) {
        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to load voice modes: ' + (err as Error).message;
        set({ error: errorMessage });
      } finally {
        set({ isLoadingVoiceModes: false });
      }
    },

    enqueueCells: async (selectedCells: Set<string>) => {
      const newItems: GenerationQueueItem[] = [];
      const { script } = get();
      if (!script) {
        console.error('No script found');
        return;
      }

      Array.from(selectedCells).forEach(cellKey => {
        const [rowIndex, cellIndex] = cellKey.split('-').map(Number);
        const cell = script.history_grid.grid[rowIndex]?.cells[cellIndex];

        if (cell && !cell.generated_filepath && !cell.hide) {
          const texts = cell.height > 1 ? cell.texts.slice(1) : cell.texts;
          const voiceModes = get().voiceModes;
          const voiceMode = voiceModes.find(v => v.path === cell.voice_mode);

          // Load all actors for this cell
          const actors: ActorData[] = [];
          for (const actorPath of cell.actors) {
            if (actorPath && actorPath.trim()) {
              const actor = get().actors.find(a => a.path === actorPath);
              if (actor) {
                actors.push(actor.actor_data as ActorData);
              } else {
                console.warn(`Actor not found for ${actorPath}`);
              }
            }
          }

          // Only enqueue if we have the required data
          if (texts?.length > 0 && actors.length > 0 && voiceMode) {
            newItems.push({
              id: generateCellKey(rowIndex, cellIndex),
              executionId: '',
              rowIndex,
              cellIndex,
              texts,
              actors,
              voiceMode,
              status: 'pending',
              progress: {
                percentage: 0,
                stepName: '',
                timestamp: '',
                stepNum: 0,
                totalSteps: 0,
              },
            });
          }
        }
      });

      if (newItems.length > 0) {
        set(state => ({
          generationQueue: [...state.generationQueue, ...newItems],
        }));

        // Auto-start processing
        setTimeout(() => {
          get().processQueue();
        }, 100);
      }
    },

    removeFromQueue: (id: string) => {
      set(state => ({
        generationQueue: state.generationQueue.filter(item => item.id !== id),
      }));
    },

    clearQueue: () => {
      set({ generationQueue: [] });
    },

    processQueue: async () => {
      const { generationQueue, initializeWebSocket, script } = get();
      if (!script) {
        console.error('No script found');
        return;
      }
      const processingItems = [];
      const alreadyPendingItems = [];
      for (const item of generationQueue) {
        if (item.status === 'pending') {
          alreadyPendingItems.push(item);
        } else if (item.status === 'processing') {
          processingItems.push(item);
        }
      }
      const itemsToProcess = alreadyPendingItems.slice(
        0,
        MAX_PROCESSING_ITEMS - processingItems.length
      );

      if (itemsToProcess.length === 0) {
        return;
      }

      set({ isProcessingQueue: true });

      // Initialize WebSocket connection for progress updates
      initializeWebSocket();

      // Start all tasks in parallel
      for (const item of itemsToProcess) {
        try {
          const thisVoiceModeFileInfo = get().voiceModes.find(v => v.name === item.voiceMode.name);
          // Execute the generation workflow in background
          const voiceModePath = thisVoiceModeFileInfo?.path || '';
          if (!thisVoiceModeFileInfo || !voiceModePath) {
            console.error('Voice mode path not found for item', item);
            throw new Error('Voice mode path not found for item');
          }
          const voiceMode = thisVoiceModeFileInfo.voice_mode_data;
          if (!voiceMode) {
            console.error('Voice mode not found for item', item);
            throw new Error('Voice mode not found for item');
          }

          const stepNames = voiceMode.steps.map(config => config.name);
          const allParameters: Record<string, any> = {};

          let voiceClonePaths: string[] = [];
          let audioTranscriptions: string[] = [];
          if (voiceMode.steps[0].multi_speaker === true) {
            // Multi-speaker workflow - use 15s clips from all actors
            voiceClonePaths = item.actors
              .map(actor => (actor.clip_path || '').trim())
              .filter(path => path); // Remove empty paths
            audioTranscriptions = item.actors.map(actor => actor.clip_transcription || '');
          } else if (voiceMode.steps[0].multi_speaker === false) {
            if (item.actors.length > 1) {
              throw new Error('Multiple actors found for single-speaker workflow');
            }
            if (item.actors.length > 0) {
              if (item.actors.length > 1) {
                console.warn(
                  'Multiple actors found for single-speaker workflow, using first',
                  item.actors
                );
              }
              const firstActor = item.actors[0];
              const clipPath = (firstActor.clip_path || '').trim();
              if (clipPath) {
                voiceClonePaths = [clipPath];
              }
              audioTranscriptions = [(item.actors[0].clip_transcription || '').trim()];
            }
          } else {
            console.error(
              'Invalid multi-speaker value, should be true or false:',
              voiceMode.steps[0].multi_speaker
            );
          }

          voiceMode.steps.forEach(config => {
            Object.entries(config.parameters).forEach(([key, value]) => {
              if (value !== undefined && value !== null && value !== '') {
                allParameters[key] = value;
              }
            });
          });

          const output_subfolder = sanitizeFolderName(script.title);
          const output_file_name = `${item.rowIndex}-${item.cellIndex}`;

          get().updateCellInScript(
            item.rowIndex,
            item.cellIndex,
            {
              generated_filepath: `${output_subfolder}/${output_file_name}.wav`,
            },
            true
          );
          await handleSaveScript();

          const request: StepExecutionRequest = {
            texts: item.texts,
            voice_clone_paths: voiceClonePaths,
            audio_transcriptions: audioTranscriptions,
            steps: stepNames,
            parameters: allParameters as Record<string, never>,
            output_subfolder,
            output_file_name,
          };
          const executionResponse = await stepsApi.executeWorkflowBackground(request);

          const executionId = executionResponse.execution_id;

          // Track the execution and mark item as processing
          set(state => ({
            generationQueue: state.generationQueue.map(queueItem =>
              queueItem.id === item.id
                ? { ...queueItem, status: 'processing', executionId }
                : queueItem
            ),
          }));
        } catch (err) {
          const errorMessage =
            err instanceof ApiError ? err.message : 'Generation failed: ' + (err as Error).message;

          console.error(
            `❌ Failed to start task for cell ${item.rowIndex}-${item.cellIndex}:`,
            errorMessage
          );

          // Update item status to error
          set(state => ({
            generationQueue: state.generationQueue.map(queueItem =>
              queueItem.id === item.id
                ? { ...queueItem, status: 'error', error: errorMessage }
                : queueItem
            ),
          }));
        }
      }

      set({ isProcessingQueue: false });
    },

    generateOneMissingWaveform: async (rowIndex: number, cellIndex: number): Promise<boolean> => {
      const { script } = get();
      if (!script) {
        console.error('No script found');
        return false;
      }
      const cell = script.history_grid.grid[rowIndex]?.cells[cellIndex];
      if (!cell) {
        console.error('Cell not found');
        return false;
      }
      if (cell.generated_filepath && (!cell.waveform_data || cell.waveform_data.length === 0)) {
        try {
          if (cell.generated_filepath === 'error') {
            console.warn(`Cell ${rowIndex}-${cellIndex} has an error filepath`);
            return false;
          }
          const audioUrl = filesApi.getFileUrl(cell.generated_filepath);
          const waveformPeaks = await generateWaveformPeaks(audioUrl);

          get().updateCellInScript(
            rowIndex,
            cellIndex,
            {
              waveform_data: waveformPeaks,
            },
            true
          );
          return true;
        } catch (error) {
          console.warn(`Failed to generate waveform for cell ${rowIndex}-${cellIndex}:`, error);
          get().updateCellInScript(
            rowIndex,
            cellIndex,
            {
              generated_filepath: '',
              waveform_data: [],
            },
            true
          );
          return true;
        }
      }
      return false;
    },

    generateMissingWaveformsAndCheckStatus: async () => {
      const { script, handleSaveScript } = get();
      if (!script) {
        console.error('No script found');
        return;
      }
      let hasUpdates = false;

      // Scan all cells for missing waveforms
      for (let rowIndex = 0; rowIndex < script.history_grid.grid.length; rowIndex++) {
        const row = script.history_grid.grid[rowIndex];
        for (let cellIndex = 0; cellIndex < row.cells.length; cellIndex++) {
          const result = await get().generateOneMissingWaveform(rowIndex, cellIndex);
          if (result) {
            hasUpdates = true;
          }
        }
      }
      if (hasUpdates) {
        handleSaveScript();
      }
    },

    setError: (error: string | null) => set({ error }),

    // Export actions
    exportCurrentTimeline: async () => {
      const { script, currentScriptName, initializeWebSocket } = get();

      if (!script) {
        set({ error: 'No script to export' });
        return;
      }

      // Initialize WebSocket for progress updates
      initializeWebSocket();

      const subfolder = sanitizeFolderName(currentScriptName || script.title || 'untitled_project');

      try {
        set({
          isExporting: true,
          exportProgress: 0,
          exportStepName: 'Starting export...',
          error: null,
        });

        await filesApi.exportTimeline(script, subfolder);

        // The actual export will be handled via WebSocket messages
      } catch (err) {
        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to start export: ' + (err as Error).message;
        set({ error: errorMessage, isExporting: false });
      }
    },

    // Background task actions
    initializeWebSocket: () => {
      const { websocket } = get();
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        return; // Already connected
      }

      // Clear any existing handlers to avoid conflicts
      webSocketService.clearHandlers([
        'onExecutionComplete',
        'onExecutionError',
        'onExecutionProgress',
        'onExportStart',
        'onExportProgress',
        'onExportComplete',
        'onExportError',
      ]);

      // Set up handlers for timeline-specific messages
      webSocketService.setHandlers({
        onExecutionComplete: async (message: any) => {
          const { execution_id, result, output_subfolder } = message;
          if (output_subfolder !== sanitizeFolderName(get().currentScriptName)) {
            console.log('Got a message from another tab, ignoring', message);
            return;
          }
          // Find the queue item with this execution ID
          const foundItem = findQueueItemByExecutionId(execution_id);

          console.log('execution_complete', execution_id, result, foundItem);
          console.log('debug_chunks', result.debug_chunk_help_text, result.debug_chunks);

          if (foundItem && result.output_files && result.output_files.length > 0) {
            const result = await get().generateOneMissingWaveform(
              foundItem.rowIndex,
              foundItem.cellIndex
            );
            if (result) {
              updateQueueItem(foundItem.id, {
                status: 'completed',
                progress: undefined,
              });
            } else {
              updateQueueItem(foundItem.id, {
                status: 'error',
                error: 'Failed to generate waveform',
                progress: undefined,
              });
            }
          }

          // Resume processing
          setTimeout(() => {
            get().processQueue();
          }, 100);
        },
        onExecutionError: (message: any) => {
          const { execution_id: errorExecutionId, error, output_subfolder } = message;
          if (output_subfolder !== sanitizeFolderName(get().currentScriptName)) {
            console.log('Got a message from another tab, ignoring', message);
            return;
          }
          // Execution errors often get sent before the execution starts.
          new Promise(resolve => {
            setTimeout(() => {
              resolve(true);
            }, 10);
          }).then(() => {
            console.error(`❌ Timeline - Execution ${errorExecutionId} failed:`, error);

            // Find the queue item with this execution ID
            const errorFoundItem = findQueueItemByExecutionId(errorExecutionId);

            if (errorFoundItem) {
              updateQueueItem(errorFoundItem.id, {
                status: 'error',
                error: error,
                progress: undefined,
              });

              // Update cell to have 'error' as its output filepath
              get().updateCellInScript(
                errorFoundItem.rowIndex,
                errorFoundItem.cellIndex,
                {
                  generated_filepath: 'error',
                },
                false
              );
            }
          });
          // Resume processing
          setTimeout(() => {
            get().processQueue();
          }, 100);
        },
        onExecutionProgress: (message: any) => {
          const {
            execution_id: progressExecutionId,
            step_name,
            progress_percentage,
            step_num,
            total_steps,
            timestamp,
            output_subfolder,
          } = message;

          if (output_subfolder !== sanitizeFolderName(get().currentScriptName)) {
            console.log('Got a message from another tab, ignoring', message);
            return;
          }

          // Find the queue item with this execution ID and update its progress
          const progressFoundItem = findQueueItemByExecutionId(progressExecutionId);

          if (progressFoundItem) {
            updateQueueItem(progressFoundItem.id, {
              status: 'processing',
              progress: {
                percentage: progress_percentage || 0,
                stepNum: step_num || 0,
                totalSteps: total_steps || 0,
                stepName: step_name || 'Processing...',
                timestamp: timestamp || new Date().toISOString(),
              },
            });
          }
        },
        onExportStart: (message: any) => {
          set({
            isExporting: true,
            exportProgress: 0,
            exportStepName: 'Starting audio export...',
          });
        },
        onExportProgress: (message: any) => {
          const { progress_percentage: exportProgress, step_name: exportStepName } = message;
          set({
            exportProgress: exportProgress || 0,
            exportStepName: exportStepName || 'Processing...',
          });
        },
        onExportComplete: (message: any) => {
          const { output_file_path } = message;
          set({
            isExporting: false,
            exportProgress: 100,
            exportStepName: 'Export complete!',
            exportedFilePath: output_file_path,
          });
        },
        onExportError: (message: any) => {
          const { error: exportError } = message;
          set({
            isExporting: false,
            error: `Export failed: ${exportError}`,
            exportStepName: 'Export failed',
          });
        },
      });

      // Get the current websocket instance
      const ws = webSocketService.getWebSocket();
      set({ websocket: ws });
    },

    disconnectWebSocket: () => {
      // Clear timeline-specific handlers
      webSocketService.clearHandlers([
        'onExecutionComplete',
        'onExecutionError',
        'onExecutionProgress',
        'onExportStart',
        'onExportProgress',
        'onExportComplete',
        'onExportError',
      ]);
      set({ websocket: null });
    },

    updateCellInScript: (
      rowIndex: number,
      cellIndex: number,
      updates: Partial<ScriptHistoryGridCell>,
      markDirty: boolean
    ) => {
      const script = get().script;
      if (!script) {
        throw new Error('Script not found');
      }
      set({
        script: {
          ...script,
          history_grid: {
            ...script.history_grid,
            grid: script.history_grid.grid.map((row, rIndex) =>
              rIndex === rowIndex
                ? {
                    ...row,
                    cells: row.cells.map((cell, cIndex) =>
                      cIndex === cellIndex ? { ...cell, ...updates } : cell
                    ),
                  }
                : row
            ),
          },
        },
        hasChangedSinceLastSave: markDirty,
      });
    },

    handleEnqueueGeneration: (rowIndex: number, cellIndex: number) => {
      const { script, enqueueCells } = get();
      if (!script) return;
      const cell = script.history_grid.grid[rowIndex]?.cells[cellIndex];
      if (cell) {
        if (!cell.generated_filepath && !cell.hide) {
          // This code is literally just to check if it's valid or not.
          const text = cell.texts.join(' ');
          const actor = cell.actors[0] || '';
          const voiceMode = cell.voice_mode || '';
          if (text && actor && voiceMode) {
            enqueueCells(new Set([generateCellKey(rowIndex, cellIndex)]));
          }
        } else {
          console.warn('cell is hidden or already generated');
          get().updateCellInScript(
            rowIndex,
            cellIndex,
            {
              generated_filepath: '',
              waveform_data: [],
            },
            true
          );
        }
      }
    },
  };
});

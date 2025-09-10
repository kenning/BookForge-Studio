import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { ModelMetadata, ModelWorkflow, Step } from '../../types/readableBackendTypes';
import { ValidationError, ExecutionResult, WrappedStep } from '../types';
import { filesApi, stepsApi, modelsApi, ApiError } from '../../api/api';
import { webSocketService } from '../../services/websocketService';
import { FileInfo, VoiceModeData } from '../../types/readableBackendTypes';

interface MultiSpeakerInput {
  id: string;
  text: string;
  actorPath: string;
  transcription: string;
}

interface VoiceModesState {
  // Data
  availableSteps: Step[];
  availableModels: ModelMetadata[];
  currentWorkflow: WrappedStep[];
  voiceModes: VoiceModeData[];
  selectedVoiceMode: string | null;
  inputText: string;
  voiceClonePath: string;
  voiceCloneTranscription: string; // Add transcription field for single-speaker mode

  // Multi-speaker support
  isMultiSpeaker: boolean;
  multiSpeakerInputs: MultiSpeakerInput[];

  // UI State
  isLoading: boolean;
  isExecuting: boolean;
  error: string | null;
  validationErrors: ValidationError[];
  executionResult: ExecutionResult | null;

  // Background task state
  currentTaskId: string | null;
  taskProgress: number;
  taskMessage: string;
  websocket: WebSocket | null;

  // Drag state
  activeId: string | null;
  activeStep: Step | null;

  // Actions
  setAvailableSteps: (steps: Step[]) => void;
  setAvailableModels: (models: ModelMetadata[]) => void;
  setCurrentWorkflow: (workflow: WrappedStep[]) => void;
  addStepToWorkflow: (step: Step) => void;
  removeStepFromWorkflow: (stepId: string) => void;
  reorderWorkflow: (oldIndex: number, newIndex: number) => void;
  updateStepParameter: (stepId: string, paramName: string, value: any) => void;
  validateWorkflow: () => void;
  setInputText: (text: string) => void;
  setVoiceClonePath: (path: string) => void;
  setVoiceCloneTranscription: (transcription: string) => void; // Add setter for transcription

  // Multi-speaker actions
  setIsMultiSpeaker: (isMultiSpeaker: boolean) => void;
  setMultiSpeakerInputs: (inputs: MultiSpeakerInput[]) => void;
  addMultiSpeakerInput: () => void;
  removeMultiSpeakerInput: (id: string) => void;
  updateMultiSpeakerInput: (
    id: string,
    field: keyof Omit<MultiSpeakerInput, 'id'>,
    value: string
  ) => void;

  setActiveId: (id: string | null) => void;
  setActiveStep: (step: Step | null) => void;
  setError: (error: string | null) => void;
  setIsLoading: (loading: boolean) => void;
  setIsExecuting: (executing: boolean) => void;
  setExecutionResult: (result: ExecutionResult | null) => void;

  // Background task actions
  setCurrentTaskId: (taskId: string | null) => void;
  setTaskProgress: (progress: number) => void;
  setTaskMessage: (message: string) => void;
  initializeWebSocket: () => void;
  disconnectWebSocket: () => void;

  loadVoiceModes: () => Promise<void>;
  loadModels: () => Promise<void>;
  saveVoiceMode: (name: string) => Promise<void>;
  loadVoiceMode: (name: string) => Promise<void>;
  loadModelWorkflow: (modelName: string) => Promise<void>;
  executeWorkflow: () => Promise<void>;
}

export const useVoiceModesStore = create<VoiceModesState>((set, get) => ({
  // Initial state
  availableSteps: [],
  availableModels: [],
  currentWorkflow: [],
  voiceModes: [],
  selectedVoiceMode: null,
  inputText: '',
  voiceClonePath: '',
  voiceCloneTranscription: '',
  isMultiSpeaker: false,
  multiSpeakerInputs: [],
  isLoading: false,
  isExecuting: false,
  error: null,
  validationErrors: [],
  executionResult: null,
  activeId: null,
  activeStep: null,

  // Background task state
  currentTaskId: null,
  taskProgress: 0,
  taskMessage: '',
  websocket: null,

  // Actions
  setAvailableSteps: steps => set({ availableSteps: steps }),
  setAvailableModels: models => set({ availableModels: models }),

  setCurrentWorkflow: workflow => {
    set({ currentWorkflow: workflow });

    // Automatically determine if this is a multi-speaker workflow based on the first step
    if (workflow.length > 0) {
      const firstStep = workflow[0].step;
      if (firstStep.step_type === 'start_step' && 'multi-speaker' in firstStep) {
        const isMultiSpeaker = firstStep['multi-speaker'] === true;
        set({ isMultiSpeaker });

        // Initialize multi-speaker inputs if switching to multi-speaker mode and inputs are empty
        if (isMultiSpeaker && get().multiSpeakerInputs.length === 0) {
          set({
            multiSpeakerInputs: [
              {
                id: uuidv4(),
                text: '',
                actorPath: '',
                transcription: '',
              },
            ],
          });
        }
      }
    }

    get().validateWorkflow();
  },

  addStepToWorkflow: step => {
    const newStepConfig: WrappedStep = {
      id: uuidv4(),
      step,
    };

    const newWorkflow = [...get().currentWorkflow, newStepConfig];
    get().setCurrentWorkflow(newWorkflow);
  },

  removeStepFromWorkflow: stepId => {
    const newWorkflow = get().currentWorkflow.filter(s => s.id !== stepId);
    get().setCurrentWorkflow(newWorkflow);
  },

  reorderWorkflow: (oldIndex, newIndex) => {
    const { arrayMove } = require('@dnd-kit/sortable');
    const newWorkflow = arrayMove(get().currentWorkflow, oldIndex, newIndex);
    get().setCurrentWorkflow(newWorkflow);
  },

  updateStepParameter: (stepId, paramName, value) => {
    const newWorkflow = get().currentWorkflow.map(stepConfig =>
      stepConfig.id === stepId
        ? {
            ...stepConfig,
            step: {
              ...stepConfig.step,
              parameters: {
                ...stepConfig.step.parameters,
                [paramName]: value,
              },
            },
          }
        : stepConfig
    );
    get().setCurrentWorkflow(newWorkflow as WrappedStep[]);
  },

  validateWorkflow: () => {
    const workflow = get().currentWorkflow;
    const errors: ValidationError[] = [];

    for (let i = 0; i < workflow.length - 1; i++) {
      const currentStep = workflow[i];
      const nextStep = workflow[i + 1];

      const areTypesCompatible = (outputType: string, inputType: string) => {
        if (outputType === 'parameter' || inputType === 'parameter') {
          return true;
        }

        const outputTypes = outputType.split('|');
        const inputTypes = inputType.split('|');

        return outputTypes.some(out => inputTypes.some(inp => out.trim() === inp.trim()));
      };

      if (!areTypesCompatible(currentStep.step.output_type, nextStep.step.input_type)) {
        errors.push({
          stepId: nextStep.id,
          message: `Input type "${nextStep.step.input_type}" doesn't match previous output type "${currentStep.step.output_type}"`,
          type: 'input_mismatch',
        });
      }
    }

    set({ validationErrors: errors });
  },

  setInputText: text => set({ inputText: text }),
  setVoiceClonePath: path => set({ voiceClonePath: path }),
  setVoiceCloneTranscription: transcription => set({ voiceCloneTranscription: transcription }),

  // Multi-speaker actions
  setIsMultiSpeaker: (isMultiSpeaker: boolean) => set({ isMultiSpeaker }),

  setMultiSpeakerInputs: (inputs: MultiSpeakerInput[]) => set({ multiSpeakerInputs: inputs }),

  addMultiSpeakerInput: () => {
    const newInput: MultiSpeakerInput = {
      id: uuidv4(),
      text: '',
      actorPath: '',
      transcription: '',
    };
    set(state => ({ multiSpeakerInputs: [...state.multiSpeakerInputs, newInput] }));
  },

  removeMultiSpeakerInput: (id: string) => {
    set(state => ({
      multiSpeakerInputs: state.multiSpeakerInputs.filter(input => input.id !== id),
    }));
  },

  updateMultiSpeakerInput: (
    id: string,
    field: keyof Omit<MultiSpeakerInput, 'id'>,
    value: string
  ) => {
    set(state => ({
      multiSpeakerInputs: state.multiSpeakerInputs.map(input =>
        input.id === id ? { ...input, [field]: value } : input
      ),
    }));
  },

  setActiveId: id => set({ activeId: id }),
  setActiveStep: step => set({ activeStep: step }),
  setError: error => set({ error }),
  setIsLoading: loading => set({ isLoading: loading }),
  setIsExecuting: executing => set({ isExecuting: executing }),
  setExecutionResult: result => set({ executionResult: result }),

  // Background task actions
  setCurrentTaskId: taskId => set({ currentTaskId: taskId }),
  setTaskProgress: progress => set({ taskProgress: progress }),
  setTaskMessage: message => set({ taskMessage: message }),

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
    ]);

    // Set up handlers for voice modes specific messages
    webSocketService.setHandlers({
      onExecutionComplete: (message: any) => {
        const {
          // execution_id,
          result,
        } = message;

        set({
          executionResult: result as ExecutionResult,
          isExecuting: false,
          taskProgress: 100,
          taskMessage: 'Workflow completed successfully!',
          currentTaskId: null,
        });
      },
      onExecutionError: (message: any) => {
        const { execution_id: errorExecutionId, error } = message;
        console.error(`❌ Voice Modes - Execution ${errorExecutionId} failed:`, error);

        set({
          isExecuting: false,
          taskProgress: 0,
          taskMessage: `Execution failed: ${error}`,
          currentTaskId: null,
        });
      },
      onExecutionProgress: (message: any) => {
        const progressData = message?.data || message;
        set({
          taskProgress: progressData.progress_percentage || 0,
          taskMessage: progressData.step_name || '',
        });
      },
    });

    // Get the current websocket instance
    const ws = webSocketService.getWebSocket();
    set({ websocket: ws });
  },

  disconnectWebSocket: () => {
    // Clear voice modes specific handlers
    webSocketService.clearHandlers([
      'onExecutionComplete',
      'onExecutionError',
      'onExecutionProgress',
    ]);
    set({ websocket: null });
  },

  loadVoiceModes: async () => {
    try {
      set({ isLoading: true });
      const files = await filesApi.listFiles('voice_modes');
      const voiceModes: VoiceModeData[] = [];

      for (const file of files.flat_files || []) {
        if (file.name.endsWith('.json') && file.voice_mode_data) {
          try {
            voiceModes.push(file.voice_mode_data as VoiceModeData);
          } catch (err) {
            console.warn(`Failed to load voice mode ${file.name}:`, err);
          }
        }
      }

      set({ voiceModes });
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : 'Failed to load voice modes: ' + (err as Error).message;
      set({ error: errorMessage });
    } finally {
      set({ isLoading: false });
    }
  },

  loadModels: async () => {
    try {
      const modelsResponse = await modelsApi.getModels();
      set({ availableModels: modelsResponse.models });
    } catch (err) {
      const errorMessage =
        err instanceof ApiError ? err.message : 'Failed to load models: ' + (err as Error).message;
      console.error(errorMessage);
      set({ error: errorMessage });
    }
  },

  saveVoiceMode: async name => {
    try {
      const workflow = get().currentWorkflow;
      const voiceMode: VoiceModeData = {
        type: 'voice_mode',
        steps: workflow.map(step => step.step),
      };
      const voiceModeFile: FileInfo = {
        type: 'file',
        name: `${name}.json`,
        path: `voice_modes/${name}.json`,
        size: 0,
        extension: 'json',
        file_type: 'voice_mode',
        voice_mode_data: voiceMode,
      };

      await filesApi.saveFile({
        directory_type: 'voice_modes',
        filename: `${name}.json`,
        content: voiceModeFile as any,
      });

      get().loadVoiceModes();
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : 'Failed to save voice mode: ' + (err as Error).message;
      set({ error: errorMessage });
    }
  },

  loadVoiceMode: async name => {
    try {
      const modeData = await filesApi.getTextContent(`voice_modes/${name}.json`);
      const parsedContent = JSON.parse(modeData.content).voice_mode_data;

      const stepsWithIds = (parsedContent.steps || []).map((step: Step) => ({
        id: uuidv4(),
        step: {
          ...step,
          parameters: step.parameters || {},
        },
      }));

      get().setCurrentWorkflow(stepsWithIds);
      set({ selectedVoiceMode: name });
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : 'Failed to load voice mode: ' + (err as Error).message;
      set({ error: errorMessage });
    }
  },

  loadModelWorkflow: async (workflowName: string) => {
    try {
      const { availableSteps, availableModels } = get();

      let modelWorkflow: ModelWorkflow | undefined;
      for (const model of availableModels) {
        modelWorkflow = model.workflows.find(w => w.name === workflowName);
        if (modelWorkflow) {
          break;
        }
      }
      if (!modelWorkflow) {
        throw new Error(`Model workflow ${workflowName} not found`);
      }

      const workflowSteps: WrappedStep[] = [];

      for (const stepName of modelWorkflow.steps) {
        const step = availableSteps.find(s => s.name === stepName);
        if (step) {
          const parameterValues: Record<string, any> = {};

          // Use the actual defaults from step metadata
          if (step.parameters) {
            Object.entries(step.parameters).forEach(([key, paramDef]) => {
              parameterValues[key] = (paramDef as any).default;
            });
          }

          // Only override specific cases where we need different defaults for the workflow
          if (stepName === 'set_num_candidates') {
            parameterValues.num_candidates = 3;
          } else if (stepName === 'whisper_check') {
            parameterValues.whisper_model = 'tiny';
          }

          workflowSteps.push({
            id: uuidv4(),
            step: {
              ...step,
              parameters: parameterValues as Record<string, never>,
            },
          });
        } else {
          console.warn(`Step '${stepName}' not found in available steps`);
        }
      }

      get().setCurrentWorkflow(workflowSteps);
      set({ selectedVoiceMode: null });
    } catch (error) {
      console.error(`Failed to load ${workflowName} workflow:`, error);
      // Fallback to empty workflow or show error message
      get().setCurrentWorkflow([]);
    }
  },

  executeWorkflow: async () => {
    const {
      currentWorkflow,
      inputText,
      voiceClonePath,
      voiceCloneTranscription,
      isMultiSpeaker,
      multiSpeakerInputs,
      initializeWebSocket,
    } = get();

    // Validation for single-speaker mode
    if (!isMultiSpeaker && !inputText.trim()) {
      set({ error: 'Please provide input text' });
      return;
    }

    // Validation for multi-speaker mode
    if (isMultiSpeaker) {
      if (multiSpeakerInputs.length === 0) {
        set({ error: 'Please add at least one speaker input' });
        return;
      }

      const hasEmptyText = multiSpeakerInputs.some(input => !input.text.trim());
      if (hasEmptyText) {
        set({ error: 'Please provide text for all speaker inputs' });
        return;
      }

      const hasEmptyActor = multiSpeakerInputs.some(input => !input.actorPath.trim());
      if (hasEmptyActor) {
        set({ error: 'Please select an actor for all speaker inputs' });
        return;
      }
    }

    if (get().validationErrors.length > 0) {
      set({ error: 'Please fix validation errors before executing' });
      return;
    }

    try {
      set({
        isExecuting: true,
        error: null,
        executionResult: null,
        taskProgress: 0,
        taskMessage: 'Starting workflow...',
      });

      // Initialize WebSocket connection for progress updates
      initializeWebSocket();

      const stepNames = currentWorkflow.map(config => config.step.name);
      const allParameters: Record<string, any> = {};

      // Collect workflow parameters
      currentWorkflow.forEach(config => {
        Object.entries(config.step.parameters).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            allParameters[key] = value;
          }
        });
      });

      // Always use consolidated array format
      let texts: string[];
      let voiceClonePaths: string[] | undefined;
      let audioTranscriptions: string[] | undefined;

      if (isMultiSpeaker) {
        texts = multiSpeakerInputs.map(input => input.text.trim());
        voiceClonePaths = multiSpeakerInputs.map(input => input.actorPath);
        audioTranscriptions = multiSpeakerInputs.map(input => input.transcription || '');
      } else {
        texts = [inputText];
        if (voiceClonePath.trim()) {
          voiceClonePaths = [voiceClonePath.trim()];
          audioTranscriptions = [voiceCloneTranscription || ''];
        }
      }

      // Need to hash the name so it refetches
      const now = Date.now().toString();
      const hash = now.slice(now.length - 6); // Just use the last 6 digits of the timestamp
      // allParameters.output_subfolder = hash;

      if (!voiceClonePaths || !audioTranscriptions) {
        set({ error: 'Please provide a voice clone path and audio transcription' });
        return;
      }

      // Use background execution
      const executionResponse = await stepsApi.executeWorkflowBackground({
        texts,
        voice_clone_paths: voiceClonePaths,
        audio_transcriptions: audioTranscriptions,
        steps: stepNames,
        parameters: allParameters as Record<string, never>,
        output_subfolder: allParameters.output_subfolder || 'test_output',
        output_file_name: (allParameters.output_file_name || 'test') + '_' + hash,
      });

      const executionId = executionResponse.execution_id;
      set({ currentTaskId: executionId });
    } catch (err) {
      const errorMessage =
        err instanceof ApiError ? err.message : 'Execution failed: ' + (err as Error).message;
      console.error('❌ Workflow execution failed:', errorMessage);
      set({
        error: errorMessage,
        isExecuting: false,
        currentTaskId: null,
        taskProgress: 0,
        taskMessage: '',
      });
    }
  },
}));

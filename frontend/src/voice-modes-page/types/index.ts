import { Step } from '../../types/readableBackendTypes';

export interface ValidationError {
  stepId: string;
  message: string;
  type: 'input_mismatch' | 'missing_step' | 'invalid_parameter';
}

export interface WrappedStep {
  step: Step;
  id: string;
}

export interface ExecutionResult {
  multiple_speaker_text_array?: string[] | null;
  output_files: string[];
  parameters: Record<string, any>;
  step_results: Array<{
    step_name: string;
    metadata: Step;
    has_audio: boolean;
    parameters_set: string[];
    output_files: string[];
  }>;
}

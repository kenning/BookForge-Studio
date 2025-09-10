import { components } from './backendTypes';

export type FileInfo = components['schemas']['FileInfo'];
export type DirectoryInfo = components['schemas']['DirectoryInfo'];

export type ActorData = components['schemas']['ActorData'];
export type VoiceModeData = components['schemas']['VoiceModeData'];
export type Step = components['schemas']['Step'];
export type ModelMetadata = components['schemas']['ModelMetadata'];
export type ModelWorkflow = components['schemas']['ModelWorkflow'];

export type Script = components['schemas']['Script-Input'];
export type ScriptHistoryGrid = components['schemas']['ScriptHistoryGrid-Input'];
export type ScriptHistoryGridRow = components['schemas']['ScriptHistoryGridRow'];
export type ScriptHistoryGridCell = components['schemas']['ScriptHistoryGridCell'];
export type BetweenLineElement = components['schemas']['BetweenLineElement'];

// API requests + responses
export type FileListResponse = components['schemas']['FileListResponse'];
export type TextContentResponse = components['schemas']['TextContentResponse'];
export type GenericSaveRequest = components['schemas']['GenericSaveRequest'];
export type GenericSaveResponse = components['schemas']['GenericSaveResponse'];
export type SaveScriptRequest = components['schemas']['SaveScriptRequest'];
export type ServiceStatus = components['schemas']['ServiceStatus'];
export type ServicesStatusResponse = components['schemas']['ServicesStatusResponse'];
export type TextToScriptViaOllamaRequest = components['schemas']['TextToScriptViaOllamaRequest'];
export type LoadScriptResponse = components['schemas']['ScriptResponse'];

export type StepExecutionRequest = components['schemas']['StepExecutionRequest'];

export type HTTPValidationError = components['schemas']['HTTPValidationError'];
export type ValidationError = components['schemas']['ValidationError'];

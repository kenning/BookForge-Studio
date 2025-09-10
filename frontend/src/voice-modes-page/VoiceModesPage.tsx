import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useVoiceModesStore } from './store/voiceModesStore';
import SaveLoadBrowser from '../components/SaveLoadBrowser';
import CollapsibleSidebar from '../components/CollapsibleSidebar';
import PageHeader from '../components/PageHeader';
import NavigationSidebar from '../components/NavigationSidebar';
import NewPageMessage from '../components/NewPageMessage';
import FileDropdown from '../components/FileDropdown';
import AudioPlayer from '../components/AudioPlayer';
import { ActorData, FileInfo } from '../types/readableBackendTypes';
import { DragDropProvider } from './components/DragDropProvider';
import AvailableStepsContainer from './components/AvailableStepsContainer';
import WorkflowContainer from './components/WorkflowContainer';
import LogPanel from '../components/LogPanel';

const VoiceModesPage: React.FC = () => {
  const {
    availableSteps,
    availableModels,
    currentWorkflow,
    inputText,
    voiceClonePath,
    voiceCloneTranscription,
    isMultiSpeaker,
    multiSpeakerInputs,
    isExecuting,
    error,
    validationErrors,
    executionResult,
    taskProgress,
    taskMessage,
    setInputText,
    setVoiceClonePath,
    setVoiceCloneTranscription,
    addMultiSpeakerInput,
    removeMultiSpeakerInput,
    updateMultiSpeakerInput,
    reorderWorkflow,
    executeWorkflow,
    loadVoiceModes,
    loadModels,
    saveVoiceMode,
    loadVoiceMode,
    loadModelWorkflow,
    setError,
    setCurrentWorkflow,
    setAvailableSteps,
  } = useVoiceModesStore();

  // Local state for SaveLoadBrowser integration
  const [currentVoiceModeName, setCurrentVoiceModeName] = useState<string>('');
  const [workflowName, setWorkflowName] = useState<string>('');
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [refreshFileList, setRefreshFileList] = useState<(() => void) | null>(null);

  // Wrapped handlers that update dirty state
  const handleSetCurrentWorkflow = useCallback(
    (workflow: any) => {
      setCurrentWorkflow(workflow);
      if (currentVoiceModeName) {
        setIsDirty(true);
      }
    },
    [setCurrentWorkflow, currentVoiceModeName]
  );

  const handleReorderWorkflow = useCallback(
    (startIndex: number, endIndex: number) => {
      reorderWorkflow(startIndex, endIndex);
      if (currentVoiceModeName) {
        setIsDirty(true);
      }
    },
    [reorderWorkflow, currentVoiceModeName]
  );

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        const { stepsApi } = await import('../api/api');
        const steps = await stepsApi.getSteps();
        setAvailableSteps(steps);

        await loadVoiceModes();
        await loadModels();
      } catch (err) {
        setError('Failed to load application data: ' + (err as Error).message);
      }
    };

    loadData();
  }, [setAvailableSteps, setError, loadModels, loadVoiceModes]);

  // Track changes to workflow, input text, voice clone path, transcription, multi-speaker inputs, and workflow name
  useEffect(() => {
    if (currentVoiceModeName) {
      setIsDirty(true);
    }
  }, [
    currentVoiceModeName,
    currentWorkflow,
    inputText,
    voiceClonePath,
    voiceCloneTranscription,
    multiSpeakerInputs,
    workflowName,
  ]);

  const handleInputTextChange = (text: string) => {
    setInputText(text);
    if (currentVoiceModeName) {
      setIsDirty(true);
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleActorSelect = (filePath: string, actorData: ActorData | null) => {
    if (actorData && actorData.clip_path) {
      setVoiceClonePath(actorData.clip_path);
      setVoiceCloneTranscription(actorData.clip_transcription || '');
    } else {
      console.error('no actor data or no voice clone clip!');
      setVoiceClonePath('');
      setVoiceCloneTranscription('');
    }
    if (currentVoiceModeName) {
      setIsDirty(true);
    }
  };

  const handleMultiSpeakerActorSelect = (
    inputId: string,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    filePath: string,
    actorData: ActorData | null
  ) => {
    if (actorData && actorData.clip_path) {
      updateMultiSpeakerInput(inputId, 'actorPath', actorData.clip_path);
      updateMultiSpeakerInput(inputId, 'transcription', actorData.clip_transcription || '');
    } else {
      console.error('no actor data or no voice clone clip!');
      updateMultiSpeakerInput(inputId, 'actorPath', '');
      updateMultiSpeakerInput(inputId, 'transcription', '');
    }
    if (currentVoiceModeName) {
      setIsDirty(true);
    }
  };

  const handleLoadModelWorkflow = (workflowName: string) => {
    loadModelWorkflow(workflowName);
    if (currentVoiceModeName) {
      setIsDirty(true);
    }
  };

  const handleRefreshReady = useCallback((refreshFn: () => void) => {
    setRefreshFileList(() => refreshFn);
  }, []);

  const handleWorkflowNameChange = (name: string) => {
    setWorkflowName(name);
    if (currentVoiceModeName) {
      setIsDirty(true);
    }
  };

  // Memoized fileFilter to prevent unnecessary re-renders
  const fileFilter = useCallback((file: FileInfo) => file.name.endsWith('.json'), []);
  const actorFileFilter = useCallback((file: FileInfo) => file.name.endsWith('.json'), []);

  // Memoized callbacks to prevent unnecessary re-renders
  const callbacks = useMemo(() => {
    const handleSaveVoiceMode = async () => {
      if (!workflowName.trim()) {
        setError('Please enter a workflow name');
        return;
      }

      try {
        setIsSaving(true);
        await saveVoiceMode(workflowName);
        setCurrentVoiceModeName(workflowName);
        setIsDirty(false);

        // Refresh the file list to show the newly saved file
        if (refreshFileList) {
          refreshFileList();
        }
      } catch (err) {
        setError('Failed to save voice mode: ' + (err as Error).message);
      } finally {
        setIsSaving(false);
      }
    };
    const handleVoiceModeFileClick = (file: FileInfo) => {
      const name = file.name.replace('.json', '');
      loadVoiceMode(name);
      setCurrentVoiceModeName(name);
      setWorkflowName(name);
      setIsDirty(false); // Mark as clean when loading
    };

    const handleNewVoiceMode = async () => {
      const name = prompt('Enter voice mode name:');
      if (name) {
        try {
          // Create a new empty voice mode (don't load default workflow yet)
          setCurrentVoiceModeName(name);
          setWorkflowName(name);
          setCurrentWorkflow([]); // Clear workflow
          // Clear input fields for new voice mode
          setInputText('');
          setVoiceClonePath('');
          setVoiceCloneTranscription('');
          setIsDirty(true);
        } catch (err) {
          setError('Failed to create new voice mode: ' + (err as Error).message);
        }
      }
    };
    return {
      onFileClick: handleVoiceModeFileClick,
      onSave: handleSaveVoiceMode,
      onNew: handleNewVoiceMode,
      onRefreshReady: handleRefreshReady,
    };
  }, [
    handleRefreshReady,
    loadVoiceMode,
    refreshFileList,
    saveVoiceMode,
    setCurrentWorkflow,
    setError,
    setInputText,
    setVoiceClonePath,
    setVoiceCloneTranscription,
    workflowName,
  ]);

  const modelWorkflows = useMemo(() => {
    const workflows = [];
    for (const model of availableModels) {
      for (const workflow of model.workflows) {
        workflows.push(workflow);
      }
    }
    return workflows;
  }, [availableModels]);

  return (
    <div className="app-with-navigation">
      <NavigationSidebar isDirty={isDirty} />

      <div className="page-content-with-navigation">
        <PageHeader title="🎨 Voice Modes" />

        <DragDropProvider
          availableSteps={availableSteps}
          currentWorkflow={currentWorkflow}
          validationErrors={validationErrors}
          onSetCurrentWorkflow={handleSetCurrentWorkflow}
          onReorderWorkflow={handleReorderWorkflow}
        >
          <div className="page-content">
            <CollapsibleSidebar>
              <SaveLoadBrowser
                directoryType="voice_modes"
                title={
                  <>
                    Voice
                    <br />
                    Modes
                  </>
                }
                currentItemName={currentVoiceModeName}
                isDirty={isDirty}
                isSaving={isSaving}
                externalError={error}
                callbacks={callbacks}
                fileFilter={fileFilter}
                className="sidebar-section"
              />

              <div className="sidebar-section workflow-components-browser">
                <AvailableStepsContainer availableSteps={availableSteps} />
              </div>
            </CollapsibleSidebar>

            <div
              className="not-sidebar-content"
              style={{
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                paddingRight: '10px',
              }}
            >
              {!currentVoiceModeName && currentWorkflow.length === 0 ? (
                <NewPageMessage itemType="voice mode" />
              ) : (
                <>
                  {/* Workflow Name Section */}
                  <div className="workflow-name-section">
                    <label className="workflow-name-label">
                      File name:
                      <input
                        type="text"
                        value={workflowName}
                        onChange={e => handleWorkflowNameChange(e.target.value)}
                        placeholder="Enter workflow name..."
                        className="workflow-name-input"
                      />
                      <div className="workflow-name-section-info">
                        {currentWorkflow.length} steps
                      </div>
                    </label>
                  </div>

                  {/* Scrollable Workflow Section */}
                  <div
                    className="workflow-section"
                    style={{ flex: 1, overflowY: 'auto', marginBottom: '20px' }}
                  >
                    {currentWorkflow.length === 0 ? (
                      <div className="empty-workflow-container">
                        <p className="empty-workflow-text">
                          Choose a default workflow to get started:
                        </p>
                        <div className="default-workflow-buttons">
                          {modelWorkflows.map(workflow => (
                            <button
                              key={workflow.name}
                              onClick={() => handleLoadModelWorkflow(workflow.name)}
                              className={`${workflow.name}-workflow-btn`}
                            >
                              {workflow.name}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <WorkflowContainer
                        currentWorkflow={currentWorkflow}
                        validationErrors={validationErrors}
                      />
                    )}
                  </div>

                  {/* Fixed Bottom Section - Input and Execution */}
                  <div
                    className={`input-execution-section ${isMultiSpeaker ? 'multi-speaker' : ''}`}
                    style={{ flexShrink: 0 }}
                  >
                    {isMultiSpeaker ? (
                      /* Multi-speaker DIA mode */
                      <div className="multi-speaker-inputs">
                        <h3>Multi-Speaker Dialogue Inputs</h3>
                        {multiSpeakerInputs.map((input, index) => (
                          <div key={input.id} className="speaker-input-row">
                            <div className="speaker-label">Speaker {index + 1}:</div>
                            <div className="speaker-text-container">
                              <textarea
                                value={input.text}
                                onChange={e =>
                                  updateMultiSpeakerInput(input.id, 'text', e.target.value)
                                }
                                placeholder={`Enter text for Speaker ${index + 1}...`}
                                className="speaker-text-input"
                                rows={2}
                              />
                            </div>
                            <div className="speaker-actor-container">
                              <label>Actor:</label>
                              <FileDropdown
                                directoryType="actors"
                                fileFilter={actorFileFilter}
                                onFileSelect={(filePath, actorData) =>
                                  handleMultiSpeakerActorSelect(input.id, filePath, actorData)
                                }
                                placeholder="Select actor..."
                                className="speaker-actor-dropdown"
                              />
                            </div>
                            {input.actorPath ? <AudioPlayer filename={input.actorPath} /> : null}
                            {/* <div className="speaker-transcription-container">
                              <label>Audio Transcription:</label>
                              <input
                                type="text"
                                value={input.transcription}
                                onChange={e =>
                                  updateMultiSpeakerInput(input.id, 'transcription', e.target.value)
                                }
                                placeholder="Transcription of the 15s clip..."
                                className="speaker-transcription-input"
                                readOnly
                              />
                            </div> */}
                            {multiSpeakerInputs.length > 1 && (
                              <button
                                onClick={() => removeMultiSpeakerInput(input.id)}
                                className="remove-speaker-btn"
                                title="Remove this speaker"
                              >
                                ×
                              </button>
                            )}
                          </div>
                        ))}

                        <div className="multi-speaker-controls">
                          <button onClick={addMultiSpeakerInput} className="add-speaker-btn">
                            + Add Speaker
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* Single-speaker  */
                      <div className="input-row">
                        <div className="text-input-container">
                          <textarea
                            value={inputText}
                            onChange={e => handleInputTextChange(e.target.value)}
                            placeholder="Enter text to process..."
                            className="text-input"
                          />
                        </div>
                        <div className="actor-select-container">
                          <label htmlFor="actor-select">Actor:</label>
                          <FileDropdown
                            directoryType="actors"
                            fileFilter={actorFileFilter}
                            onFileSelect={handleActorSelect}
                            placeholder="Select an actor..."
                            className="actor-dropdown"
                          />
                        </div>
                        {voiceClonePath && (
                          <div>
                            <AudioPlayer filename={voiceClonePath} />
                            <div>
                              <input
                                readOnly
                                className="speaker-transcription-input"
                                type="text"
                                value={voiceCloneTranscription}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="execution-row">
                      <div>
                        <button
                          onClick={executeWorkflow}
                          disabled={
                            isExecuting ||
                            (!isMultiSpeaker && !inputText.trim()) ||
                            (!isMultiSpeaker && !voiceClonePath.trim()) ||
                            (isMultiSpeaker && multiSpeakerInputs.length === 0) ||
                            validationErrors.length > 0
                          }
                          className={`execute-btn ${validationErrors.length > 0 ? 'disabled' : ''}`}
                        >
                          {isExecuting ? 'Processing...' : 'Test Voice Mode'}
                        </button>
                      </div>

                      {validationErrors.length > 0 && (
                        <div className="validation-summary">
                          {validationErrors.length} validation error(s) - fix them to execute
                        </div>
                      )}
                      {error && <div className="error-message">{error}</div>}
                      {taskMessage?.length > 0 && <div className="task-message">{taskMessage}</div>}
                      {!executionResult && taskProgress > 0 && (
                        <div className="progress-bar">
                          <div className="progress-fill" style={{ width: `${taskProgress}%` }} />
                        </div>
                      )}

                      {/* Results */}
                      {executionResult && executionResult.output_files.length > 0 && (
                        <div className="output-files">
                          {executionResult.output_files.map((file, idx) => (
                            <AudioPlayer key={idx} filename={file} />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
              <LogPanel />
            </div>
          </div>
        </DragDropProvider>
      </div>
    </div>
  );
};

export default VoiceModesPage;

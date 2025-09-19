import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { DragEndEvent } from '@dnd-kit/core';
import FileBrowser from '../components/FileBrowser';
import CollapsibleSidebar from '../components/CollapsibleSidebar';
import SaveLoadBrowser from '../components/SaveLoadBrowser';
import NewPageMessage from '../components/NewPageMessage';
import PageHeader from '../components/PageHeader';
import NavigationSidebar from '../components/NavigationSidebar';
import DragDropProvider from '../components/DragDropProvider';
import NewTextWorkflowsPage from './NewTextWorkflowsPage';
import TextWorkflowScriptEditor, { TextWorkflowScriptEditorRef } from './TextWorkflowScriptEditor';
import './TextWorkflowsPage.css';
import { FileInfo, Script } from '../types/readableBackendTypes';
import { filesApi, ApiError } from '../api/api';
import { useLogPanelStore } from '../store/logPanelStore';
import { NotSidebarContentWithWrapper } from '../components/NotSidebarContentWithWrapper';

const TextWorkflowsPage: React.FC = () => {
  // Core script state
  const [currentScript, setCurrentScript] = useState<Script | null>(null);
  const [scriptName, setScriptName] = useState<string>('');
  const [scriptTitle, setScriptTitle] = useState<string>('');
  const [currentWorkflowName, setCurrentWorkflowName] = useState<string>('');
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [refreshFileList, setRefreshFileList] = useState<(() => void) | null>(null);
  const [scriptWasGeneratedRecently, setScriptWasGeneratedRecently] = useState(false);

  const [error, setError] = useState<string | null>(null);

  // Log panel controls from Zustand store
  const { openPanel } = useLogPanelStore();

  // CSV file state for NewTextWorkflowsPage
  const [csvDroppedFile, setCsvDroppedFile] = useState<FileInfo | null>(null);

  // Text file state for NewTextWorkflowsPage
  const [textDroppedFile, setTextDroppedFile] = useState<FileInfo | null>(null);

  // Ref to access script editor's save function
  const scriptEditorRef = useRef<TextWorkflowScriptEditorRef>(null);

  // Helper function to create empty script
  const createEmptyScript = (): Script => ({
    type: 'script',
    title: '',
    speaker_to_actor_map: {},
    speaker_to_voice_mode_map: {},
    history_grid: {
      grid: [],
      between_lines_elements: [],
    },
  });

  // SaveLoadBrowser handlers
  const handleScriptSave = async (scriptToSave: Script) => {
    try {
      setIsSaving(true);
      setError(null);

      // Update the script with the current title before saving
      const finalScriptToSave = {
        ...scriptToSave,
        title: scriptTitle,
      };

      await filesApi.saveFile({
        directory_type: 'scripts',
        filename: `${scriptName}.json`,
        content: finalScriptToSave as any,
      });

      setCurrentWorkflowName(scriptName);
      setIsDirty(false);
      setScriptWasGeneratedRecently(false);

      // Refresh the file list to show the newly saved file
      if (refreshFileList) {
        refreshFileList();
      }
    } catch (err) {
      const errorMessage =
        err instanceof ApiError ? err.message : 'Failed to save script: ' + (err as Error).message;
      setError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDirtyStateChange = (dirty: boolean) => {
    setIsDirty(dirty);
  };

  const handleRefreshReady = useCallback((refreshFn: () => void) => {
    setRefreshFileList(() => refreshFn);
  }, []);

  const handleScriptNameChange = (name: string) => {
    setScriptName(name);
    if (currentWorkflowName) {
      setIsDirty(true);
    }
  };

  const handleScriptTitleChange = (title: string) => {
    setScriptTitle(title);
    if (currentWorkflowName) {
      setIsDirty(true);
    }
  };

  // Track changes to script for dirty state
  useEffect(() => {
    if (currentWorkflowName) {
      setIsDirty(true);
    }
  }, [currentScript, scriptName, scriptTitle, currentWorkflowName]);

  // Handle script generation from workflow component
  const handleScriptGenerated = (script: Script) => {
    setCurrentScript(script);
    setScriptTitle(script.title || '');
    setScriptWasGeneratedRecently(true);
  };

  const handleRemoveCsvFile = () => {
    setCsvDroppedFile(null);
  };

  const handleRemoveTextFile = () => {
    setTextDroppedFile(null);
  };

  // Helper function to check if script is empty or near-empty
  const isScriptEmptyOrNearEmpty = (script: Script | null): boolean => {
    if (!script) return true;
    return script.history_grid.grid.length === 0;
  };

  // Memoized fileFilter and callbacks to prevent unnecessary re-renders
  const fileFilter = useCallback((file: FileInfo) => file.name.endsWith('.json'), []);

  const callbacks = useMemo(() => {
    const handleNewWorkflow = async () => {
      const name = prompt('Enter script file name:');
      if (name) {
        try {
          setCurrentScript(createEmptyScript());
          setCurrentWorkflowName(name);
          setScriptName(name);
          setScriptTitle('');
          setIsDirty(true);
          setError(null);
          setCsvDroppedFile(null);
          setTextDroppedFile(null);
        } catch (err) {
          setError('Failed to create new script: ' + (err as Error).message);
        }
      }
    };
    const handleWorkflowFileClick = async (file: FileInfo) => {
      try {
        const scriptData = await filesApi.getTextContent(file.path);
        const parsedScript = JSON.parse(scriptData.content);
        setCurrentScript(parsedScript);
        setCurrentWorkflowName(file.name.replace('.json', ''));
        setScriptName(file.name.replace('.json', ''));
        setScriptTitle(parsedScript.title || '');
        setIsDirty(false);
        setError(null);
      } catch (err) {
        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to load script: ' + (err as Error).message;
        setError(errorMessage);
      }
    };

    const handleSaveWorkflow = async () => {
      if (!scriptName.trim()) {
        setError('Please enter a script name');
        return;
      }

      // Open log panel to show save activity
      openPanel();

      // Trigger save via script editor ref
      if (scriptEditorRef.current) {
        scriptEditorRef.current.saveChanges();
      }
    };

    return {
      onFileClick: handleWorkflowFileClick,
      onSave: handleSaveWorkflow,
      onNew: handleNewWorkflow,
      onRefreshReady: handleRefreshReady,
    };
  }, [handleRefreshReady, openPanel, scriptName]);

  const handleCsvFileDrop = (file: FileInfo) => {
    // Only accept CSV files
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Only CSV files can be dropped here');
      return;
    }

    setCsvDroppedFile(file);
    setError(null);
  };

  const handleTextFileDrop = (file: FileInfo) => {
    if (
      !file.name.toLowerCase().endsWith('.txt') &&
      !file.name.toLowerCase().endsWith('.md') &&
      !file.name.toLowerCase().endsWith('.text')
    ) {
      setError('Only text files (.txt, .md, .text) can be dropped here');
      return;
    }

    setTextDroppedFile(file);
    setError(null);
  };

  // Drag and drop handlers for file browser integration
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (!over || !active.data.current) return;

    const file = active.data.current.file as FileInfo;

    // Handle CSV drops for NewTextWorkflowsPage functionality
    if (over.id === 'csv-drop') {
      handleCsvFileDrop(file);
    } else if (over.id === 'text-drop') {
      handleTextFileDrop(file);
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const renderDragOverlay = (activeId: string | null, activeData: any) => {
    if (!activeData?.file) return null;

    const file = activeData.file as FileInfo;
    return (
      <div className="drag-overlay">
        <span className="file-icon">📄</span>
        <span className="file-name">{file.name}</span>
      </div>
    );
  };

  return (
    <div className="app-with-navigation">
      <NavigationSidebar isDirty={isDirty} />

      <div className="page-content-with-navigation">
        <div className="text-workflows-page">
          <PageHeader title="📝 Text Workflows" />

          <DragDropProvider onDragEnd={handleDragEnd} renderDragOverlay={renderDragOverlay}>
            <div className="page-content">
              {/* Column 1: Sidebar */}
              <CollapsibleSidebar>
                <SaveLoadBrowser
                  directoryType="scripts"
                  title="Scripts"
                  currentItemName={currentWorkflowName}
                  isDirty={isDirty || scriptWasGeneratedRecently}
                  isSaving={isSaving}
                  externalError={error}
                  callbacks={callbacks}
                  fileFilter={fileFilter}
                  className="sidebar-section"
                />

                <FileBrowser
                  initialFileTypeFilter={['text']}
                  viewMode="tree"
                  className="sidebar-section"
                />
              </CollapsibleSidebar>

              <NotSidebarContentWithWrapper
                style={{ overflowY: 'auto', paddingRight: '0.5rem', height: '100%' }}
              >
                {!currentWorkflowName ? (
                  <NewPageMessage itemType="text workflow" />
                ) : (
                  <>
                    {error && <div className="error-message">{error}</div>}

                    {/* Script Name Section */}
                    <div className="script-name-section">
                      <div className="script-name-row">
                        <label>
                          Script Name (also the filename in files/scripts/ folder):
                          <input
                            type="text"
                            value={scriptName}
                            onChange={e => handleScriptNameChange(e.target.value)}
                            placeholder="Enter script name..."
                            className="script-name-input"
                          />
                        </label>
                      </div>
                    </div>

                    {/* Content based on script state */}
                    {isScriptEmptyOrNearEmpty(currentScript) ? (
                      <NewTextWorkflowsPage
                        onScriptGenerated={handleScriptGenerated}
                        onError={setError}
                        csvDroppedFile={csvDroppedFile}
                        onCsvFileRemove={handleRemoveCsvFile}
                        textDroppedFile={textDroppedFile}
                        onTextFileRemove={handleRemoveTextFile}
                        onCsvFileDrop={handleCsvFileDrop}
                        onTextFileDrop={handleTextFileDrop}
                      />
                    ) : (
                      <TextWorkflowScriptEditor
                        ref={scriptEditorRef}
                        script={currentScript!}
                        title={scriptTitle}
                        onScriptChange={setCurrentScript}
                        onTitleChange={handleScriptTitleChange}
                        onSave={handleScriptSave}
                        onDirtyStateChange={handleDirtyStateChange}
                        isSaving={isSaving}
                        scriptWasGeneratedRecently={scriptWasGeneratedRecently}
                      />
                    )}
                  </>
                )}
              </NotSidebarContentWithWrapper>
            </div>
          </DragDropProvider>
        </div>
      </div>
    </div>
  );
};

export default TextWorkflowsPage;

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { DragEndEvent } from '@dnd-kit/core';
import DragDropProvider from '../components/DragDropProvider';
import SaveLoadBrowser from '../components/SaveLoadBrowser';
import CollapsibleSidebar from '../components/CollapsibleSidebar';
import FileBrowser from '../components/FileBrowser';
import DropZone from '../components/DropZone';
import PageHeader from '../components/PageHeader';
import NavigationSidebar from '../components/NavigationSidebar';
import NewPageMessage from '../components/NewPageMessage';
import { ActorData, FileInfo, ModelMetadata } from '../types/readableBackendTypes';
import { filesApi, ApiError, modelsApi } from '../api/api';
import { NotSidebarContentWithWrapper } from '../components/NotSidebarContentWithWrapper';

interface TipSection {
  modelName: string;
  tips: string[];
}

const ActorsPage: React.FC = () => {
  const [currentActor, setCurrentActor] = useState<ActorData>({
    type: 'actor',
    clip_path: '',
    clip_transcription: '',
    notes: '',
    is_favorite: false,
  });

  const [droppedFiles, setDroppedFiles] = useState<{
    clip?: FileInfo;
  }>({});

  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [currentActorName, setCurrentActorName] = useState<string>('');
  const [isDirty, setIsDirty] = useState(false);
  const [refreshFileList, setRefreshFileList] = useState<(() => void) | null>(null);

  const [availableModels, setAvailableModels] = useState<ModelMetadata[]>([]);
  const [tips, setTips] = useState<TipSection[]>([]);

  useEffect(() => {
    modelsApi.getModels().then(result => {
      setAvailableModels(result.models);
    });
  }, []);

  useEffect(() => {
    const tips: TipSection[] = [];
    for (const model of availableModels) {
      tips.push({ modelName: model.model_name, tips: model.voice_clone_tips });
    }
    setTips(tips);
  }, [availableModels]);

  const handleAudioFileDrop = (file: FileInfo) => {
    setDroppedFiles(prev => ({ ...prev, clip: file }));
    setCurrentActor(prev => ({ ...prev, clip_path: file.path }));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (!over || !active.data.current) return;

    const file = active.data.current.file as FileInfo;
    const dropZoneId = over.id as string;

    // Only accept audio files
    if (file.file_type !== 'audio') {
      setError('Only audio files can be dropped here');
      return;
    }

    setError(null);
    setIsDirty(true); // Mark as dirty when files are dropped

    if (dropZoneId === 'clip-drop') {
      handleAudioFileDrop(file);
    }
  };

  const handleRemoveFile = (clipType: 'clip') => {
    setDroppedFiles(prev => ({ ...prev, [clipType]: undefined }));
    setCurrentActor(prev => ({
      ...prev,
      [`${clipType}_path`]: '',
    }));
    setIsDirty(true); // Mark as dirty when files are removed
  };

  const handleActorChange = (updates: Partial<ActorData>) => {
    setCurrentActor(prev => ({ ...prev, ...updates }));
    setIsDirty(true); // Mark as dirty when actor data changes
  };

  const handleRefreshReady = React.useCallback((refreshFn: () => void) => {
    setRefreshFileList(() => refreshFn);
  }, []);

  const renderDragOverlay = (activeId: string | null, activeData: any) => {
    if (!activeData?.file) return null;

    const file = activeData.file as FileInfo;
    return (
      <div className="drag-overlay">
        <span className="file-icon">🎵</span>
        <span className="file-name">{file.name}</span>
      </div>
    );
  };

  // Memoized fileFilter to prevent unnecessary re-renders
  const fileFilter = useCallback((file: FileInfo) => file.name.endsWith('.json'), []);

  // Memoized callbacks to prevent unnecessary re-renders
  const callbacks = useMemo(() => {
    const handleSaveActor = async (possibleForcedActorData?: ActorData) => {
      if (!currentActorName.trim()) {
        setError('Please enter an actor name');
        return;
      }

      try {
        setIsSaving(true);
        setError(null);

        const actorData: ActorData = possibleForcedActorData || currentActor;
        console.log('actorData', actorData);

        const actorToSave: FileInfo = {
          file_type: 'actor',
          name: currentActorName,
          path: `${currentActorName}.json`,
          type: 'file',
          size: null,
          extension: 'json',
          actor_data: actorData,
        };

        await filesApi.saveFile({
          directory_type: 'actors',
          filename: `${currentActorName}.json`,
          content: actorToSave as any,
        });

        setIsDirty(false); // Mark as clean after saving
        console.log('Actor saved successfully');

        // Refresh the file list to show the newly saved file
        if (refreshFileList) {
          refreshFileList();
        }
      } catch (err) {
        const errorMessage =
          err instanceof ApiError ? err.message : 'Failed to save actor: ' + (err as Error).message;
        setError(errorMessage);
      } finally {
        setIsSaving(false);
      }
    };
    const handleActorFileClick = async (file: FileInfo) => {
      try {
        const parsedActor: ActorData = file.actor_data || {
          type: 'actor',
          clip_path: '',
          clip_transcription: '',
          notes: '',
          is_favorite: false,
        };
        console.log('📋 Parsed actor data:', parsedActor);
        setCurrentActor(parsedActor);
        setCurrentActorName(file.path.replace('.json', '').replace('actors/', ''));

        // Populate dropped files from stored paths
        const newDroppedFiles: { clip?: FileInfo } = {};

        if (parsedActor.clip_path) {
          const pathParts = parsedActor.clip_path.split('/');
          const fileName = pathParts[pathParts.length - 1];
          const extension = fileName.includes('.') ? fileName.split('.').pop() || null : null;
          newDroppedFiles.clip = {
            name: fileName,
            path: parsedActor.clip_path,
            type: 'file',
            size: null, // We don't have size info, but it's not critical for display
            extension: extension,
            file_type: 'audio',
          };
        }

        setDroppedFiles(newDroppedFiles);
        setError(null);
        setIsDirty(false); // Mark as clean when loading
      } catch (err) {
        const errorMessage =
          err instanceof ApiError ? err.message : 'Failed to load actor: ' + (err as Error).message;
        setError(errorMessage);
      }
    };

    const handleNewActor = async () => {
      const name = prompt('Enter actor name:');
      if (name) {
        try {
          // Create a new empty actor
          const newActor: ActorData = {
            type: 'actor',
            clip_path: '',
            clip_transcription: '',
            notes: '',
            is_favorite: false,
          };

          setCurrentActor(newActor);
          setCurrentActorName(name);
          setDroppedFiles({});
          setIsDirty(true);
          setError(null);
        } catch (err) {
          setError('Failed to create new actor: ' + (err as Error).message);
        }
      }
    };
    return {
      onFileClick: handleActorFileClick,
      onSave: handleSaveActor,
      onNew: handleNewActor,
      onRefreshReady: handleRefreshReady,
    };
  }, [handleRefreshReady, currentActorName, currentActor, refreshFileList]);

  return (
    <DragDropProvider onDragEnd={handleDragEnd} renderDragOverlay={renderDragOverlay}>
      <div className="app-with-navigation">
        <NavigationSidebar isDirty={isDirty} />

        <div className="page-content-with-navigation">
          <div className="actors-page">
            <PageHeader title="🎭 Actors" />

            <div className="page-content">
              <CollapsibleSidebar>
                <SaveLoadBrowser
                  directoryType="actors"
                  title="Actors"
                  currentItemName={currentActorName}
                  isDirty={isDirty}
                  isSaving={isSaving}
                  externalError={error}
                  callbacks={callbacks}
                  fileFilter={fileFilter}
                  className="sidebar-section"
                />
                <FileBrowser
                  initialFileTypeFilter={['audio']}
                  viewMode="tree"
                  className="sidebar-section"
                />
              </CollapsibleSidebar>

              <NotSidebarContentWithWrapper>
                {!currentActorName ? (
                  <NewPageMessage itemType="actor" />
                ) : (
                  <div className="actor-editor">
                    <div className="actor-name-section">
                      <label>
                        Actor Name (also the filename in files/actors/ folder):
                        <input
                          type="text"
                          value={currentActorName}
                          onChange={e => {
                            setCurrentActorName(e.target.value);
                            setIsDirty(true);
                          }}
                          placeholder="Enter actor name..."
                          className="actor-name-input"
                        />
                      </label>
                      <button
                        className={`favorite-btn ${currentActor.is_favorite ? 'favorited' : ''}`}
                        onClick={async () => {
                          const newFavoriteStatus = !currentActor.is_favorite;
                          handleActorChange({ is_favorite: newFavoriteStatus });
                          // Auto-save when favorite status changes
                          if (currentActorName.trim()) {
                            await callbacks.onSave({
                              ...currentActor,
                              is_favorite: newFavoriteStatus,
                            });
                          }
                        }}
                        title={
                          currentActor.is_favorite ? 'Remove from favorites' : 'Add to favorites'
                        }
                      >
                        {currentActor.is_favorite ? '★ Favorite' : '☆'}
                      </button>
                    </div>

                    <div className="clips-section">
                      <div className="clip-column">
                        <h3>Voice Clone Clip - Drag from Input Files (Lower Left)</h3>

                        <DropZone
                          id="clip-drop"
                          label="Voice Clone Audio Clip"
                          acceptedTypes={['audio']}
                          droppedFile={droppedFiles.clip}
                          onFileRemove={() => handleRemoveFile('clip')}
                          onFileDrop={handleAudioFileDrop}
                          className="audio-drop-zone"
                        />

                        <div className="transcription-section">
                          <label>
                            Transcription:
                            <textarea
                              value={currentActor.clip_transcription || ''}
                              onChange={e =>
                                handleActorChange({ clip_transcription: e.target.value })
                              }
                              placeholder="Enter transcription for voice clone clip..."
                              className="transcription-input"
                              rows={8}
                            />
                          </label>
                        </div>

                        <div className="notes-section">
                          <label>
                            Notes:
                            <br />
                            <textarea
                              value={currentActor.notes || ''}
                              onChange={e => handleActorChange({ notes: e.target.value })}
                              placeholder="Add any notes about this actor..."
                              className="notes-input"
                              rows={4}
                            />
                          </label>
                        </div>
                      </div>

                      <div className="clip-column">
                        <div className="tips-section">
                          {tips.map(tip => (
                            <div key={tip.modelName}>
                              <h4>Tips: {tip.modelName}</h4>
                              <ul>
                                {tip.tips.map(tip => (
                                  <li key={tip}>{tip}</li>
                                ))}
                              </ul>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </NotSidebarContentWithWrapper>
            </div>
          </div>
        </div>
      </div>
    </DragDropProvider>
  );
};

export default ActorsPage;

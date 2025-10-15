import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Script, FileInfo, ScriptHistoryGridCell } from '../types/readableBackendTypes';
import NavigationSidebar from '../components/NavigationSidebar';
import SaveLoadBrowser from '../components/SaveLoadBrowser';
import CollapsibleSidebar from '../components/CollapsibleSidebar';
import NewPageMessage from '../components/NewPageMessage';
import TimelineContainer from './components/TimelineContainer';
import GenerationQueue from './components/GenerationQueue';
import PlaybackQueue from './components/PlaybackQueue';
import SpeakerAssignmentSection from './components/SpeakerAssignmentSection';
import CellEditModal from './components/CellEditModal';
import {
  handleAddCell,
  createDialogueCellFromSelection,
  handleAddDialogueCell,
} from './utils/cellOperations';
import { filesApi, ApiError } from '../api/api';
import { generateCellKey, useTimelineGenerationStore } from './store/timelineGenerationStore';
import './TimelinePage.css';
import PageHeader from '../components/PageHeader';
import { NotSidebarContentWithWrapper } from '../components/NotSidebarContentWithWrapper';
import { usePlaybackStore } from './store/timelinePlaybackStore';

const TimelinePage: React.FC = () => {
  const [selectedCells, setSelectedCells] = useState<Set<string>>(new Set());

  const [titleInput, setTitleInput] = useState<string>('');

  // Modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingCell, setEditingCell] = useState<{
    cell: ScriptHistoryGridCell;
    rowIndex: number;
    cellIndex: number;
  } | null>(null);

  // Ref for auto-scrolling to current track
  const timelineContainerRef = useRef<HTMLDivElement>(null);

  // Generation store
  const {
    script,
    setScript,
    setScriptAndMarkDirty,
    currentScriptName,
    setCurrentScriptName,
    actors,
    voiceModes,
    generationQueue,
    isProcessingQueue,
    error,
    setDirty,
    isSaving,
    setIsLoading,
    loadActors,
    loadVoiceModes,
    enqueueCells,
    generateMissingWaveformsAndCheckStatus,
    setError,
    hasChangedSinceLastSave,
    handleSaveScript,
    clearQueue: clearGenerationQueue,
  } = useTimelineGenerationStore();

  const { reset: resetPlaybackStore } = usePlaybackStore();

  // Auto-scroll to currently playing row
  const handleScrollToRow = (rowIndex: number) => {
    const timelineContainer = timelineContainerRef.current;
    if (!timelineContainer) return;

    // Calculate row height (approximately 218px per row including borders)
    const rowHeight = 198;
    const targetScrollTop = rowIndex * rowHeight - 30;

    // Smooth scroll to the row
    timelineContainer.scrollTo({
      top: targetScrollTop,
      behavior: 'smooth',
    });
  };

  const handleScriptFileSelect = async (file: FileInfo) => {
    try {
      resetPlaybackStore();
      clearGenerationQueue();
      setIsLoading(true);
      setError(null);

      // Use the specific script loading endpoint
      const response = await filesApi.loadScript(file.path);
      const scriptName =
        response.script.title || file.path.replace(/\.json$/, '').replace('scripts/', '');
      setCurrentScriptName(scriptName);
      setTitleInput(scriptName);
      const _script = { ...response.script, title: scriptName };
      setScript(_script);

      // Reset save states when loading a new script
      setDirty(true);

      // Generate missing waveforms for the newly loaded script
      generateMissingWaveformsAndCheckStatus();
    } catch (err) {
      const errorMessage =
        err instanceof ApiError ? err.message : 'Failed to load script: ' + (err as Error).message;
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTitleBlur = () => {
    if (!script) return;
    setCurrentScriptName(titleInput);
    setScript({ ...script, title: titleInput });
    setDirty(true);
  };

  const handleNewScript = async () => {
    const name = prompt('Enter script name:');
    if (name) {
      try {
        // Create a new empty script
        const newScript: Script = {
          type: 'script',
          title: name,
          speaker_to_actor_map: {},
          speaker_to_voice_mode_map: {},
          history_grid: {
            grid: [
              {
                current_index: 0,
                cells: [
                  {
                    speakers: ['narrator'],
                    actors: [''],
                    texts: [''],
                    voice_mode: '',
                    generated_filepath: '',
                    waveform_data: [],
                    height: 100,
                    hide: false,
                  },
                ],
              },
            ],
            between_lines_elements: [],
          },
        };

        setScript(newScript);
        setCurrentScriptName(name);
        setTitleInput(name);
        setDirty(true);
        setError(null);
        resetPlaybackStore();
        clearGenerationQueue();
      } catch (err) {
        setError('Failed to create new script: ' + (err as Error).message);
      }
    }
  };

  const handleCellToggleCheckbox = (rowIndex: number, cellIndex: number) => {
    const cellKey = generateCellKey(rowIndex, cellIndex);
    setSelectedCells(prev => {
      const newSet = new Set(prev);
      if (newSet.has(cellKey)) {
        newSet.delete(cellKey);
      } else {
        newSet.add(cellKey);
      }
      return newSet;
    });
  };

  const handleAddCellClick = (rowIndex: number) => {
    if (!script) return;
    setScript(handleAddCell(script, rowIndex, selectedCells));
    // Clear selected cells
    setSelectedCells(new Set());
    setDirty(true);
  };

  const handleAddDialogueCellClick = (rowIndex: number) => {
    if (!script) return;
    setScript(handleAddDialogueCell(script, rowIndex));
    setSelectedCells(new Set());
    setDirty(true);
  };

  const handleEnqueueSelected = () => {
    if (!script) return;
    enqueueCells(selectedCells);
    setSelectedCells(new Set());
  };

  const handleCreateDialogue = () => {
    if (!script || selectedCells.size <= 1) return;
    const sortedSelectedCells = Array.from(selectedCells).sort((a, b) => {
      return Number(a.split('-')[0]) - Number(b.split('-')[0]);
    });

    setScript(createDialogueCellFromSelection(script, new Set(sortedSelectedCells)));
    setSelectedCells(new Set());
    setDirty(true);
  };

  // Modal handlers
  const handleOpenEditModal = (rowIndex: number, cellIndex: number) => {
    if (!script) return;
    const cell = script.history_grid.grid[rowIndex].cells[cellIndex];
    setEditingCell({ cell, rowIndex, cellIndex });
    setIsEditModalOpen(true);
  };

  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setEditingCell(null);
  };

  // Get main track cells that need generation
  const getMainTrackCellsForGeneration = (): { cellKeys: Set<string>; count: number } => {
    if (!script) return { cellKeys: new Set(), count: 0 };

    const cellKeys = new Set<string>();

    script.history_grid.grid.forEach((row, rowIndex) => {
      const cellIndex = row.current_index;
      const cell = row.cells[cellIndex];

      if (
        cell &&
        (!cell.generated_filepath || cell.generated_filepath === '') &&
        !cell.hide &&
        cell.texts &&
        cell.texts.length > 0 &&
        cell.texts.join(' ').trim() &&
        cell.actors &&
        cell.actors.length > 0 &&
        cell.actors[0] &&
        cell.voice_mode
      ) {
        cellKeys.add(generateCellKey(rowIndex, cellIndex));
      }
    });

    return { cellKeys, count: cellKeys.size };
  };

  const handleEnqueueMainTrack = () => {
    if (!script) return;
    const { cellKeys } = getMainTrackCellsForGeneration();
    enqueueCells(cellKeys);
  };

  // Check if a cell is currently enqueued
  // Memoized fileFilter to prevent unnecessary re-renders
  const fileFilter = useCallback(
    (file: FileInfo) => file.file_type === 'script' || file.name.endsWith('.json'),
    []
  );

  // Load actors and voice modes on component mount
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        await Promise.all([loadActors(), loadVoiceModes()]);
      } catch (err) {
        console.error('Failed to load initial data:', err);
      }
    };

    loadInitialData();
  }, [loadActors, loadVoiceModes]);

  // Determine whether script is 'set up' i.e. has any non-assigned speakers or voice modes
  let scriptIsBeingSetUp = false;
  let speakers: string[] = [];

  // Analyze script and determine speakers and assignment status
  const speakerSet = new Set<string>();

  // Look through all rows and get speakers from current_index cells
  if (script) {
    script.history_grid.grid.forEach(row => {
      const currentCell = row.cells[row.current_index];
      if (currentCell && !currentCell.hide) {
        currentCell.speakers.forEach(speaker => speakerSet.add(speaker));

        // Check if this cell is missing assignments
        if (!currentCell.actors[0] || !currentCell.voice_mode) {
          scriptIsBeingSetUp = true;
        }
      }
    });

    speakers = Array.from(speakerSet);
  }

  return (
    <div className="app-layout">
      <NavigationSidebar isDirty={hasChangedSinceLastSave} />
      <div className="timeline-page">
        <PageHeader title="Script Timeline" />

        <div className="page-content">
          {/* Script Browser Sidebar */}
          <CollapsibleSidebar>
            <SaveLoadBrowser
              directoryType="scripts"
              title="Scripts"
              className={`script-file-browser sidebar-section`}
              currentItemName={currentScriptName}
              isDirty={hasChangedSinceLastSave}
              isSaving={isSaving}
              fileFilter={fileFilter}
              externalError={error}
              callbacks={{
                onFileClick: handleScriptFileSelect,
                onSave: () => handleSaveScript(),
                onNew: handleNewScript,
                onRefresh: () => {},
              }}
            />

            <div className="sidebar-section queues-sidebar-section">
              <PlaybackQueue script={script} onScrollToRow={handleScrollToRow} />

              <GenerationQueue
                queue={generationQueue}
                isProcessing={isProcessingQueue}
                selectedCount={selectedCells.size}
                onEnqueueSelected={handleEnqueueSelected}
              />
            </div>
          </CollapsibleSidebar>

          {/* Timeline Container */}
          <NotSidebarContentWithWrapper className="timeline-main">
            {script ? (
              <>
                <div className="current-script-info">
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'row',
                      gap: '10px',
                      alignItems: 'center',
                    }}
                  >
                    <input
                      id="script-title"
                      type="text"
                      value={titleInput}
                      onChange={e => setTitleInput(e.target.value)}
                      onBlur={handleTitleBlur}
                      placeholder="Enter script title..."
                      className="script-title-input"
                    />
                    {!scriptIsBeingSetUp && (
                      <div className="main-track-generation-section">
                        {(() => {
                          const { count } = getMainTrackCellsForGeneration();
                          return (
                            <button
                              className="generate-main-track-btn"
                              onClick={handleEnqueueMainTrack}
                              disabled={count === 0 || isProcessingQueue}
                            >
                              Generate Main Track ({count})
                            </button>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                  {/* <div className="script-filename">
                    File: {currentScriptName || 'Unnamed Script'}
                  </div> */}
                </div>

                <div className="speaker-section-container">
                  <SpeakerAssignmentSection
                    script={script}
                    actors={actors}
                    speakers={speakers}
                    voiceModes={voiceModes}
                    onScriptUpdate={setScriptAndMarkDirty}
                    scriptIsBeingSetUp={scriptIsBeingSetUp}
                  />
                </div>
                {!scriptIsBeingSetUp && (
                  <div className="timeline-container" ref={timelineContainerRef}>
                    <TimelineContainer
                      selectedCells={selectedCells}
                      actors={actors}
                      voiceModes={voiceModes}
                      onCellToggleCheckbox={handleCellToggleCheckbox}
                      onAddCell={handleAddCellClick}
                      onAddDialogueCell={handleAddDialogueCellClick}
                      onCreateDialogue={handleCreateDialogue}
                      onEditCell={handleOpenEditModal}
                    />
                  </div>
                )}
              </>
            ) : (
              <NewPageMessage itemType="script" timelineAdjustment={true} />
            )}
          </NotSidebarContentWithWrapper>
        </div>

        {/* Edit Cell Modal */}
        {editingCell && (
          <CellEditModal
            cell={editingCell.cell}
            rowIndex={editingCell.rowIndex}
            cellIndex={editingCell.cellIndex}
            actors={actors}
            voiceModes={voiceModes}
            isOpen={isEditModalOpen}
            onClose={handleCloseEditModal}
          />
        )}
      </div>
    </div>
  );
};

export default TimelinePage;

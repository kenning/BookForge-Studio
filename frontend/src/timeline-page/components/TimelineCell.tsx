import React, { useCallback } from 'react';
import { TimelineCellGenerationDisplayStatus } from '../types';
import { calculateCellPosition } from '../utils/timelineUtils';
import { FileInfo, ScriptHistoryGridCell } from '../../types/readableBackendTypes';
import WaveformPlayer from '../../components/WaveformPlayer';
import { usePlaybackStore, generateTrackKey } from '../store/timelinePlaybackStore';
import { useTimelineGenerationStore } from '../store/timelineGenerationStore';
import { handleCellSelection } from '../utils/cellOperations';

export interface TimelineCellProps {
  actors: FileInfo[];
  voiceModes: FileInfo[];
  cell: ScriptHistoryGridCell;
  isActive: boolean;
  isSelected: boolean;
  onToggleCheckbox: () => void;
  rowIndex: number;
  cellIndex: number;
  currentIndex: number;
  height?: number;
}

const TimelineCell: React.FC<TimelineCellProps> = ({
  cell,
  isActive,
  isSelected,
  onToggleCheckbox,
  rowIndex,
  cellIndex,
  currentIndex,
  height,
  actors,
  voiceModes,
}) => {
  const { registerAudioRef, unregisterAudioRef, _getCurrentPlaybackTrack, pause } =
    usePlaybackStore();
  const { updateCellInScript, handleEnqueueGeneration, script, generationQueue, setScript } =
    useTimelineGenerationStore();

  // Generate track key for audio ref management
  const trackKey = generateTrackKey(rowIndex, cellIndex);

  // Audio ref handlers for playback control (must be before early return)
  const handleAudioRefReady = useCallback(
    (audioElement: HTMLAudioElement) => {
      registerAudioRef(trackKey, audioElement);
    },
    [registerAudioRef, trackKey]
  );

  const handleCellSelect = useCallback(() => {
    if (!script) return;
    const { isPlaying } = usePlaybackStore.getState();
    if (isPlaying) {
      const currentPlaybackTrack = _getCurrentPlaybackTrack();
      if (currentPlaybackTrack) {
        if (
          currentPlaybackTrack.rowIndex === rowIndex &&
          currentPlaybackTrack.cellIndex !== cellIndex
        ) {
          pause();
        }
      }
    }

    const newScript = handleCellSelection(script, rowIndex, cellIndex);
    if (newScript) {
      setScript(newScript);
    }
  }, [script, rowIndex, cellIndex, setScript]);

  const handleAudioRefCleanup = useCallback(() => {
    unregisterAudioRef(trackKey);
  }, [unregisterAudioRef, trackKey]);

  if (cell.hide) {
    return null;
  }

  const isMultipleSpeaker = cell.speakers.length > 1;
  const displayText = isMultipleSpeaker ? cell.texts.join('\n') : cell.texts[0] || 'Blah blah blah';

  const cellHeight = height || cell.height || 1;
  let buttonText = '';

  let cellGenerationStatus: TimelineCellGenerationDisplayStatus = 'not_generated_yet';
  if (!script) {
    cellGenerationStatus = 'error';
  } else if (!cell) {
    cellGenerationStatus = 'error';
  } else if (cell.generated_filepath === 'error') {
    cellGenerationStatus = 'error';
  } else if (cell.waveform_data.length === 0) {
    const foundQueueStats = generationQueue.find(
      item => item.rowIndex === rowIndex && item.cellIndex === cellIndex
    );
    if (foundQueueStats) cellGenerationStatus = foundQueueStats.status;
  } else if (cell.generated_filepath && cell.waveform_data.length > 0) {
    cellGenerationStatus = 'completed';
  } else {
    cellGenerationStatus = 'not_generated_yet';
  }

  switch (cellGenerationStatus) {
    case 'pending':
      buttonText = 'Enqueued';
      break;
    case 'processing':
      buttonText = 'Generating...';
      break;
    case 'completed':
      buttonText = ''; // Display waveform instead
      break;
    case 'error':
      buttonText = 'Error';
      break;
    case 'not_generated_yet':
      buttonText = 'Generate';
      break;
  }

  const isDropdownsDisabled =
    cellGenerationStatus !== 'not_generated_yet' && cellGenerationStatus !== 'error';

  // Handlers for dropdown changes
  const handleActorChangeAtIndex = (speakerIndex: number, value: string) => {
    if (!isDropdownsDisabled) {
      const newActors = [...cell.actors];
      newActors[speakerIndex] = value;
      updateCellInScript(rowIndex, cellIndex, { actors: newActors }, true);
    }
  };

  const handleSingleActorChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    handleActorChangeAtIndex(0, e.target.value);
  };

  const handleVoiceModeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (!isDropdownsDisabled) {
      updateCellInScript(rowIndex, cellIndex, { voice_mode: e.target.value }, true);
    }
  };

  const handleGenerateClick = () => {
    handleEnqueueGeneration(rowIndex, cellIndex);
  };

  // Calculate position using the unified positioning function
  const position = calculateCellPosition(rowIndex, cellIndex, currentIndex, cellHeight);

  const cellStyle: React.CSSProperties = {
    position: 'absolute',
    left: `${position.left}px`,
    top: `${position.top}px`,
    width: `${position.width}px`,
    height: `${position.height}px`,
  };

  let speakerPluralityWarning = '';
  const thisVoiceModeData = voiceModes.find(voiceMode => voiceMode.path === cell.voice_mode);
  if (
    cell.speakers.length > 1 &&
    thisVoiceModeData?.voice_mode_data?.steps[0].multi_speaker === false
  ) {
    speakerPluralityWarning = `WARNING: Single-speaker voice mode (${thisVoiceModeData?.name})`;
  } else if (
    cell.speakers.length === 1 &&
    thisVoiceModeData?.voice_mode_data?.steps[0].multi_speaker === true
  ) {
    speakerPluralityWarning = `WARNING: Multi-speaker voice mode (${thisVoiceModeData?.name})`;
  }

  const voiceModeDropdown = (
    <select
      required
      className={`voice-mode-dropdown ${isDropdownsDisabled ? 'disabled' : ''}`}
      value={cell.voice_mode || ''}
      onChange={handleVoiceModeChange}
      disabled={isDropdownsDisabled}
    >
      <option value="">Select Voice Mode</option>
      {voiceModes.map(voiceMode => (
        <option key={voiceMode.name} value={voiceMode.path}>
          {voiceMode.name.replace(/\.json$/, '')}
        </option>
      ))}
    </select>
  );

  const favoriteActors: FileInfo[] = [];
  const nonFavoriteActors: FileInfo[] = [];
  for (const actor of actors) {
    if (actor.actor_data?.is_favorite) {
      favoriteActors.push(actor);
    } else {
      nonFavoriteActors.push(actor);
    }
  }

  return (
    <div
      className={`timeline-cell ${isActive ? 'active' : ''} ${isSelected ? 'selected' : ''} ${cellHeight > 1 ? 'multi-speaker' : ''}`}
      onClick={handleCellSelect}
      style={cellStyle}
    >
      <div className="cell-checkbox-wrapper">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleCheckbox}
          onClick={e => e.stopPropagation()}
        />
      </div>

      <div className="cell-content">
        <div className="text-speaker-container">
          <div className="cell-text">
            {isMultipleSpeaker ? (
              <div className="multiple-speaker-text">
                {cell.speakers.map((speaker, i) => (
                  <div key={i} className="speaker-line">
                    <strong>{speaker}:</strong> {cell.texts[i + 1] || ''}
                  </div>
                ))}
              </div>
            ) : (
              displayText
            )}
          </div>
          {!isMultipleSpeaker && <div className="speaker-text">Speaker: {cell.speakers[0]}</div>}
          <button className="cell-edit-button">Edit cell</button>
        </div>

        <div className="audio-section">
          {cellGenerationStatus === 'completed' ? (
            <WaveformPlayer
              filename={cell.generated_filepath}
              waveformData={cell.waveform_data}
              onAudioRefReady={handleAudioRefReady}
              onAudioRefCleanup={handleAudioRefCleanup}
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                className={`generate-button ${cellGenerationStatus}`}
                onClick={handleGenerateClick}
                disabled={
                  !cell.voice_mode ||
                  cellGenerationStatus === 'pending' ||
                  cellGenerationStatus === 'processing' ||
                  (isMultipleSpeaker
                    ? cell.actors.some(actor => !actor) // Check all actors are assigned
                    : !cell.actors[0]) // Check first actor is assigned
                }
              >
                {buttonText}
              </button>
              <div style={{ color: 'var(--accent-danger)', textAlign: 'center' }}>
                {speakerPluralityWarning}
              </div>
            </div>
          )}
        </div>
      </div>

      <div
        className="cell-controls"
        style={{ flexDirection: isMultipleSpeaker ? 'column' : 'row' }}
      >
        {isMultipleSpeaker ? (
          <>
            {/* Multiple actor dropdowns for multi-speaker cells */}
            <div className="multi-speaker-controls">
              {cell.speakers.map((speaker, i) => (
                <div key={i} className="speaker-control-row">
                  <label className="speaker-label">{speaker}:</label>
                  <select
                    required
                    className={`actor-dropdown ${isDropdownsDisabled ? 'disabled' : ''}`}
                    value={cell.actors[i] || ''}
                    onChange={e => handleActorChangeAtIndex(i, e.target.value)}
                    disabled={isDropdownsDisabled}
                  >
                    <option value="">Select Actor</option>
                    <option key="favorite actors header" value="">
                      -- Favorite Actors --
                    </option>
                    {favoriteActors.map(actor => (
                      <option key={actor.path} value={actor.path}>
                        {actor.name.replace(/\.(json|wav|mp3)$/, '')}
                      </option>
                    ))}
                    <option key="other actors header" value="">
                      -- Other Actors --
                    </option>
                    {nonFavoriteActors.map(actor => (
                      <option key={actor.path} value={actor.path}>
                        {actor.name.replace(/\.(json|wav|mp3)$/, '')}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            {/* Single voice mode dropdown for the whole dialogue */}
            {voiceModeDropdown}
          </>
        ) : (
          <>
            {/* Single speaker controls */}
            <select
              required
              className={`actor-dropdown ${isDropdownsDisabled ? 'disabled' : ''}`}
              value={cell.actors[0] || ''}
              onChange={handleSingleActorChange}
              disabled={isDropdownsDisabled}
            >
              <option value="">Select Actor</option>
              <option value="">-- Favorite Actors --</option>
              {favoriteActors.map(actor => (
                <option key={actor.path} value={actor.path}>
                  {actor.name.replace(/\.(json|wav|mp3)$/, '')}
                </option>
              ))}
              <option value="">-- Other Actors --</option>
              {nonFavoriteActors.map(actor => (
                <option key={actor.path} value={actor.path}>
                  {actor.name.replace(/\.(json|wav|mp3)$/, '')}
                </option>
              ))}
            </select>

            {voiceModeDropdown}
          </>
        )}
      </div>
    </div>
  );
};

export default TimelineCell;

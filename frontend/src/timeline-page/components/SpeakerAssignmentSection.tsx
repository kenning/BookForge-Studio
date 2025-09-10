import React, { useState, useEffect } from 'react';
import { Script, FileInfo } from '../../types/readableBackendTypes';

interface SpeakerAssignmentProps {
  script: Script;
  actors: FileInfo[];
  voiceModes: FileInfo[];
  speakers: string[];
  onScriptUpdate: (script: Script) => void;
  scriptIsBeingSetUp: boolean;
}

type AssignmentMode = 'per-speaker' | 'clip-length';
type ComparisonOperator = 'less-than' | 'greater-than';

const SpeakerAssignmentSection: React.FC<SpeakerAssignmentProps> = ({
  script,
  actors,
  voiceModes,
  onScriptUpdate,
  speakers,
  scriptIsBeingSetUp,
}) => {
  const [isExpanded, setIsExpanded] = useState(scriptIsBeingSetUp);
  const [multiSpeakerVoiceModes, setMultiSpeakerVoiceModes] = useState<Record<string, boolean>>({});
  const [localSpeakerToActorMap, setLocalSpeakerToActorMap] = useState<Record<string, string>>({});
  const [localSpeakerToVoiceModeMap, setLocalSpeakerToVoiceModeMap] = useState<
    Record<string, string>
  >({});
  const [assignmentMode, setAssignmentMode] = useState<AssignmentMode>('per-speaker');
  const [clipLengthThreshold, setClipLengthThreshold] = useState<number>(15);
  const [clipLengthOperator, setClipLengthOperator] = useState<ComparisonOperator>('less-than');
  const [shortClipVoiceMode, setShortClipVoiceMode] = useState<string>('');
  const [longClipVoiceMode, setLongClipVoiceMode] = useState<string>('');

  // Initialize local state from script
  useEffect(() => {
    if (script) {
      setLocalSpeakerToActorMap({ ...script.speaker_to_actor_map });
      setLocalSpeakerToVoiceModeMap({ ...script.speaker_to_voice_mode_map });
    }
  }, [script]);

  // Should only happen once on load
  useEffect(() => {
    const multiSpeakerVoiceModes = voiceModes.filter(
      voiceMode => voiceMode.voice_mode_data?.steps[0].multi_speaker
    );
    setMultiSpeakerVoiceModes(
      multiSpeakerVoiceModes.reduce(
        (acc, voiceMode) => {
          acc[voiceMode.path] = true;
          return acc;
        },
        {} as Record<string, boolean>
      )
    );
  }, [voiceModes]);

  const handleActorChange = (speaker: string, actorPath: string) => {
    setLocalSpeakerToActorMap(prev => ({
      ...prev,
      [speaker]: actorPath,
    }));
  };

  const handleVoiceModeChange = (speaker: string, voiceModePath: string) => {
    setLocalSpeakerToVoiceModeMap(prev => ({
      ...prev,
      [speaker]: voiceModePath,
    }));
  };

  const assignSpeaker = (speaker: string, inputScript: Script): Script => {
    setIsExpanded(false);
    const updatedScript = { ...inputScript };

    const selectedActor = localSpeakerToActorMap[speaker];
    const selectedVoiceMode = localSpeakerToVoiceModeMap[speaker];

    // Go through all cells in the script
    updatedScript.history_grid.grid = updatedScript.history_grid.grid.map(row => ({
      ...row,
      cells: row.cells.map(cell => {
        if (cell.generated_filepath && cell.actors?.[0] && cell.voice_mode) {
          return cell;
        }

        if (cell.speakers.includes(speaker)) {
          return {
            ...cell,
            actors: [selectedActor],
            voice_mode: selectedVoiceMode,
          };
        }
        return cell;
      }),
    }));

    return updatedScript;
  };

  const assignSpeakerWithClipLength = (speaker: string, inputScript: Script): Script => {
    setIsExpanded(false);
    const updatedScript = { ...inputScript };

    const selectedActor = localSpeakerToActorMap[speaker];

    // Go through all cells in the script
    updatedScript.history_grid.grid = updatedScript.history_grid.grid.map(row => ({
      ...row,
      cells: row.cells.map(cell => {
        if (cell.generated_filepath && cell.actors?.[0] && cell.voice_mode) {
          return cell;
        }

        if (cell.speakers.includes(speaker)) {
          const wordCount = countWordsInText(cell.texts.join(' ') || '');
          const isShortClip =
            clipLengthOperator === 'less-than'
              ? wordCount < clipLengthThreshold
              : wordCount > clipLengthThreshold;

          const voiceModeToUse = isShortClip ? shortClipVoiceMode : longClipVoiceMode;

          return {
            ...cell,
            actors: [selectedActor],
            voice_mode: voiceModeToUse,
          };
        }
        return cell;
      }),
    }));

    return updatedScript;
  };

  const applyLocalChangesToScript = (inputScript: Script): Script => {
    return {
      ...inputScript,
      speaker_to_actor_map: { ...localSpeakerToActorMap },
      speaker_to_voice_mode_map: { ...localSpeakerToVoiceModeMap },
    };
  };

  const handleAssignAllUngenerated = () => {
    let wipScript = applyLocalChangesToScript(script);
    for (const speaker in localSpeakerToActorMap) {
      wipScript =
        assignmentMode === 'per-speaker'
          ? assignSpeaker(speaker, wipScript)
          : assignSpeakerWithClipLength(speaker, wipScript);
    }
    onScriptUpdate(wipScript);
  };

  const handleAssignSpeaker = (speaker: string) => {
    let wipScript = applyLocalChangesToScript(script);
    wipScript =
      assignmentMode === 'per-speaker'
        ? assignSpeaker(speaker, wipScript)
        : assignSpeakerWithClipLength(speaker, wipScript);
    onScriptUpdate(wipScript);
  };

  useEffect(() => {
    setIsExpanded(scriptIsBeingSetUp);
  }, [scriptIsBeingSetUp]);

  if (!script || speakers.length === 0) {
    return null;
  }

  const allowAssignment =
    assignmentMode === 'per-speaker'
      ? speakers.every(
          speaker => localSpeakerToActorMap[speaker] && localSpeakerToVoiceModeMap[speaker]
        )
      : speakers.every(speaker => localSpeakerToActorMap[speaker]) &&
        shortClipVoiceMode &&
        longClipVoiceMode;

  const countWordsInText = (text: string): number => {
    return text
      .trim()
      .split(/\s+/)
      .filter(word => word.length > 0).length;
  };

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
    <div className="speaker-assignment-section">
      <div className="speaker-assignment-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h3>Script Setup</h3>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {isExpanded && (
        <div className="speaker-assignment-content">
          <div
            className="assignment-mode-toggle"
            style={{ marginBottom: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}
          >
            <label>
              <input
                type="radio"
                value="per-speaker"
                checked={assignmentMode === 'per-speaker'}
                onChange={e => setAssignmentMode(e.target.value as AssignmentMode)}
              />
              Per-speaker voice modes
            </label>
            <label>
              <input
                type="radio"
                value="clip-length"
                checked={assignmentMode === 'clip-length'}
                onChange={e => setAssignmentMode(e.target.value as AssignmentMode)}
              />
              Voice modes by clip length
            </label>
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <div
              className="speakers-list"
              style={{ width: assignmentMode === 'per-speaker' ? '100%' : '70%' }}
            >
              {speakers.map(speaker => (
                <div key={speaker} className="speaker-row">
                  <div className="speaker-name">{speaker}</div>

                  <select
                    className="actor-dropdown-assignment"
                    value={localSpeakerToActorMap[speaker] || ''}
                    onChange={e => handleActorChange(speaker, e.target.value)}
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

                  {assignmentMode === 'per-speaker' && (
                    <>
                      <select
                        className="voice-mode-dropdown-assignment"
                        value={localSpeakerToVoiceModeMap[speaker] || ''}
                        onChange={e => handleVoiceModeChange(speaker, e.target.value)}
                      >
                        <option value="">Select Voice Mode</option>
                        {voiceModes.map(voiceMode => (
                          <option key={voiceMode.name} value={voiceMode.path}>
                            {voiceMode.name.replace(/\.json$/, '') +
                              (multiSpeakerVoiceModes[voiceMode.path]
                                ? ' (WARNING: Multi-speaker)'
                                : '')}
                          </option>
                        ))}
                      </select>
                      {!scriptIsBeingSetUp && (
                        <button
                          className="assign-button"
                          onClick={() => handleAssignSpeaker(speaker)}
                        >
                          Re-assign Speaker
                        </button>
                      )}
                    </>
                  )}

                  {assignmentMode === 'clip-length' && !scriptIsBeingSetUp && (
                    <button className="assign-button" onClick={() => handleAssignSpeaker(speaker)}>
                      Re-assign Speaker
                    </button>
                  )}
                </div>
              ))}
            </div>

            {assignmentMode === 'clip-length' && (
              <div
                className="clip-length-config"
                style={{
                  width: '30%',
                  padding: '1rem',
                }}
              >
                <h4 style={{ marginTop: 0, marginBottom: '1rem' }}>
                  Clip Length Voice Mode Assignment
                </h4>

                <div style={{ marginBottom: '1rem' }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      marginBottom: '0.5rem',
                    }}
                  >
                    <span>Clips</span>
                    <button
                      onClick={() =>
                        setClipLengthOperator(
                          clipLengthOperator === 'less-than' ? 'greater-than' : 'less-than'
                        )
                      }
                      className="clip-length-operator-button"
                    >
                      {clipLengthOperator === 'less-than' ? 'less than' : 'greater than'}
                    </button>
                    <input
                      type="number"
                      value={clipLengthThreshold}
                      onChange={e => setClipLengthThreshold(parseInt(e.target.value) || 0)}
                      style={{
                        width: '60px',
                        padding: '0.25rem',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                      }}
                    />
                    <span>words</span>
                  </div>
                  <div style={{ marginBottom: '0.5rem' }}>are handled by:</div>
                  <select
                    value={shortClipVoiceMode}
                    onChange={e => setShortClipVoiceMode(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                    }}
                  >
                    <option value="">Select Voice Mode</option>
                    {voiceModes.map(voiceMode => (
                      <option key={voiceMode.name} value={voiceMode.path}>
                        {voiceMode.name.replace(/\.json$/, '') +
                          (multiSpeakerVoiceModes[voiceMode.path]
                            ? ' (WARNING: Multi-speaker)'
                            : '')}
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ marginBottom: '0.5rem' }}>Remaining clips are handled by:</div>
                  <select
                    value={longClipVoiceMode}
                    onChange={e => setLongClipVoiceMode(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                    }}
                  >
                    <option value="">Select Voice Mode</option>
                    {voiceModes.map(voiceMode => (
                      <option key={voiceMode.name} value={voiceMode.path}>
                        {voiceMode.name.replace(/\.json$/, '') +
                          (multiSpeakerVoiceModes[voiceMode.path]
                            ? ' (WARNING: Multi-speaker)'
                            : '')}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '1rem' }}>
            <button
              className="assign-button"
              onClick={() => handleAssignAllUngenerated()}
              disabled={!allowAssignment}
            >
              {scriptIsBeingSetUp ? 'Set Up Script' : 'Re-assign All'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SpeakerAssignmentSection;

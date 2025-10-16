import React, { useState, useEffect } from 'react';
import { ScriptHistoryGridCell, FileInfo, Script } from '../../types/readableBackendTypes';
import './CellEditModal.css';

export interface CellEditModalProps {
  cell: ScriptHistoryGridCell;
  rowIndex: number;
  cellIndex: number;
  actors: FileInfo[];
  voiceModes: FileInfo[];
  script: Script;
  availableSpeakers: string[];
  isOpen: boolean;
  onClose: () => void;
  onSave: (rowIndex: number, cellIndex: number, updatedCell: ScriptHistoryGridCell) => void;
}

const CellEditModal: React.FC<CellEditModalProps> = ({
  cell,
  rowIndex,
  cellIndex,
  actors,
  voiceModes,
  script,
  availableSpeakers,
  isOpen,
  onClose,
  onSave,
}) => {
  // Local state for editing
  const [editedTexts, setEditedTexts] = useState<string[]>([]);
  const [editedSpeakers, setEditedSpeakers] = useState<string[]>([]);
  const [editedActors, setEditedActors] = useState<string[]>([]);
  const [editedVoiceMode, setEditedVoiceMode] = useState<string>('');
  const [shouldRemoveAudio, setShouldRemoveAudio] = useState(false);

  // Store original values for comparison
  const [originalTexts, setOriginalTexts] = useState<string[]>([]);
  const [originalSpeakers, setOriginalSpeakers] = useState<string[]>([]);
  const [originalActors, setOriginalActors] = useState<string[]>([]);
  const [originalVoiceMode, setOriginalVoiceMode] = useState<string>('');

  // Initialize state when modal opens or cell changes
  useEffect(() => {
    if (isOpen) {
      setEditedTexts([...cell.texts]);
      setEditedSpeakers([...cell.speakers]);
      setEditedActors([...cell.actors]);
      setEditedVoiceMode(cell.voice_mode);
      setShouldRemoveAudio(false);

      // Store originals
      setOriginalTexts([...cell.texts]);
      setOriginalSpeakers([...cell.speakers]);
      setOriginalActors([...cell.actors]);
      setOriginalVoiceMode(cell.voice_mode);
    }
  }, [isOpen, cell]);

  // Helper function to check if a field is dirty
  const isFieldDirty = (fieldName: string, index?: number): boolean => {
    if (fieldName === 'text' && index !== undefined) {
      return editedTexts[index] !== originalTexts[index];
    }
    if (fieldName === 'speaker' && index !== undefined) {
      return editedSpeakers[index] !== originalSpeakers[index];
    }
    if (fieldName === 'actor' && index !== undefined) {
      return editedActors[index] !== originalActors[index];
    }
    if (fieldName === 'voice_mode') {
      return editedVoiceMode !== originalVoiceMode;
    }
    if (fieldName === 'remove_audio') {
      return shouldRemoveAudio;
    }
    return false;
  };

  if (!isOpen) return null;

  const handleTextChange = (index: number, value: string) => {
    const newTexts = [...editedTexts];
    newTexts[index] = value;
    setEditedTexts(newTexts);
  };

  const handleSpeakerChange = (index: number, value: string) => {
    const newSpeakers = [...editedSpeakers];

    // If "New speaker..." is selected, prompt for custom input
    if (value === '__new_speaker__') {
      const customSpeaker = prompt('Enter new speaker name:');
      if (customSpeaker && customSpeaker.trim()) {
        newSpeakers[index] = customSpeaker.trim();
      } else {
        return; // User cancelled or entered empty string
      }
    } else {
      newSpeakers[index] = value;
    }

    setEditedSpeakers(newSpeakers);

    // Auto-fill actor and voice mode based on speaker assignment map
    const speaker = newSpeakers[index];
    const assignedActor = script.speaker_to_actor_map[speaker];
    const assignedVoiceMode = script.speaker_to_voice_mode_map[speaker];

    if (assignedActor) {
      const newActors = [...editedActors];
      newActors[index] = assignedActor;
      setEditedActors(newActors);
    }

    // Only auto-fill voice mode if single speaker
    if (assignedVoiceMode && editedSpeakers.length === 1) {
      setEditedVoiceMode(assignedVoiceMode);
    }
  };

  const handleActorChange = (index: number, value: string) => {
    const newActors = [...editedActors];
    newActors[index] = value;
    setEditedActors(newActors);
  };

  const handleVoiceModeChange = (value: string) => {
    setEditedVoiceMode(value);
  };

  const handleRemoveGeneratedAudio = () => {
    setShouldRemoveAudio(true);
  };

  const handleSaveChanges = () => {
    const updatedCell: ScriptHistoryGridCell = {
      ...cell,
      texts: editedTexts,
      speakers: editedSpeakers,
      actors: editedActors,
      voice_mode: editedVoiceMode,
      generated_filepath: shouldRemoveAudio ? '' : cell.generated_filepath,
      waveform_data: shouldRemoveAudio ? [] : cell.waveform_data,
    };

    // Call the onSave callback to actually update the script
    onSave(rowIndex, cellIndex, updatedCell);

    onClose();
  };

  const handleCancel = () => {
    onClose();
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Prepare actor options
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
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-content">
        <div className="modal-header">
          <h2>Edit Cell [{rowIndex}, {cellIndex}]</h2>
          <button className="modal-close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          {/* Texts */}
          <div className="modal-section">
            <label className="modal-label">
              {editedTexts.length === 1 ? 'Text' : 'Texts'}
            </label>
            {editedTexts.map((text, index) => {
              if (editedTexts.length > 1 && index == 0) return null
              return (
                <textarea
                  key={index}
                  className={`modal-textarea ${isFieldDirty('text', index) ? 'dirty' : ''}`}
                  value={text}
                  onChange={(e) => handleTextChange(index, e.target.value)}
                  rows={3}
                  placeholder={`Enter text ${editedTexts.length > 1 ? index + 1 : ''}...`}
                />
              )
            })}
          </div>

          {/* Speakers */}
          <div className="modal-section">
            <label className="modal-label">
              {editedSpeakers.length === 1 ? 'Speaker' : 'Speakers'}
            </label>
            {editedSpeakers.map((speaker, index) => (
              <select
                key={index}
                className={`modal-select ${isFieldDirty('speaker', index) ? 'dirty' : ''}`}
                value={speaker}
                onChange={(e) => handleSpeakerChange(index, e.target.value)}
              >
                <option value="">Select Speaker</option>
                {availableSpeakers.map((availSpeaker) => (
                  <option key={availSpeaker} value={availSpeaker}>
                    {availSpeaker}
                  </option>
                ))}
                <option value="__new_speaker__">New speaker...</option>
              </select>
            ))}
          </div>

          {/* Actors */}
          <div className="modal-section">
            <label className="modal-label">
              {editedActors.length === 1 ? 'Actor' : 'Actors'}
            </label>
            {editedActors.map((actor, index) => (
              <select
                key={index}
                className={`modal-select ${isFieldDirty('actor', index) ? 'dirty' : ''}`}
                value={actor}
                onChange={(e) => handleActorChange(index, e.target.value)}
              >
                <option value="">Select Actor</option>
                <option value="" disabled>
                  -- Favorite Actors --
                </option>
                {favoriteActors.map((actorFile) => (
                  <option key={actorFile.path} value={actorFile.path}>
                    {actorFile.name.replace(/\.(json|wav|mp3)$/, '')}
                  </option>
                ))}
                <option value="" disabled>
                  -- Other Actors --
                </option>
                {nonFavoriteActors.map((actorFile) => (
                  <option key={actorFile.path} value={actorFile.path}>
                    {actorFile.name.replace(/\.(json|wav|mp3)$/, '')}
                  </option>
                ))}
              </select>
            ))}
          </div>

          {/* Voice Mode */}
          <div className="modal-section">
            <label className="modal-label">Voice Mode</label>
            <select
              className={`modal-select ${isFieldDirty('voice_mode') ? 'dirty' : ''}`}
              value={editedVoiceMode}
              onChange={(e) => handleVoiceModeChange(e.target.value)}
            >
              <option value="">Select Voice Mode</option>
              {voiceModes.map((voiceMode) => (
                <option key={voiceMode.name} value={voiceMode.path}>
                  {voiceMode.name.replace(/\.json$/, '')}
                </option>
              ))}
            </select>
          </div>

          {/* Generated Audio */}
          {cell.generated_filepath && cell.generated_filepath !== '' && (
            <div className="modal-section">
              <label className="modal-label">Generated Audio</label>
              {!shouldRemoveAudio ? (
                <>
                  <button
                    className="modal-remove-audio-btn"
                    onClick={handleRemoveGeneratedAudio}
                  >
                    Remove Generated Audio
                  </button>
                  <div className="modal-info-text">
                    Current file: {cell.generated_filepath}
                  </div>
                </>
              ) : (
                <div className="modal-info-text" style={{ color: 'var(--accent-warning)' }}>
                  Audio will be removed when you save changes
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="modal-cancel-btn" onClick={handleCancel}>
            Cancel
          </button>
          <button className="modal-save-btn" onClick={handleSaveChanges}>
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

export default CellEditModal;

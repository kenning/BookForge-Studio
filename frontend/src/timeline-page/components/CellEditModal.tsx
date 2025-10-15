import React, { useState, useEffect } from 'react';
import { ScriptHistoryGridCell, FileInfo } from '../../types/readableBackendTypes';
import './CellEditModal.css';

export interface CellEditModalProps {
  cell: ScriptHistoryGridCell;
  rowIndex: number;
  cellIndex: number;
  actors: FileInfo[];
  voiceModes: FileInfo[];
  isOpen: boolean;
  onClose: () => void;
}

const CellEditModal: React.FC<CellEditModalProps> = ({
  cell,
  rowIndex,
  cellIndex,
  actors,
  voiceModes,
  isOpen,
  onClose,
}) => {
  // Local state for editing
  const [editedTexts, setEditedTexts] = useState<string[]>([]);
  const [editedSpeakers, setEditedSpeakers] = useState<string[]>([]);
  const [editedActors, setEditedActors] = useState<string[]>([]);
  const [editedVoiceMode, setEditedVoiceMode] = useState<string>('');
  const [shouldRemoveAudio, setShouldRemoveAudio] = useState(false);

  // Initialize state when modal opens or cell changes
  useEffect(() => {
    if (isOpen) {
      setEditedTexts([...cell.texts]);
      setEditedSpeakers([...cell.speakers]);
      setEditedActors([...cell.actors]);
      setEditedVoiceMode(cell.voice_mode);
      setShouldRemoveAudio(false);
    }
  }, [isOpen, cell]);

  if (!isOpen) return null;

  const handleTextChange = (index: number, value: string) => {
    const newTexts = [...editedTexts];
    newTexts[index] = value;
    setEditedTexts(newTexts);
  };

  const handleSpeakerChange = (index: number, value: string) => {
    const newSpeakers = [...editedSpeakers];
    newSpeakers[index] = value;
    setEditedSpeakers(newSpeakers);
  };

  const handleActorChange = (index: number, value: string) => {
    const newActors = [...editedActors];
    newActors[index] = value;
    setEditedActors(newActors);
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

    console.log('Updated cell:', {
      rowIndex,
      cellIndex,
      cell: updatedCell,
    });

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
                  className="modal-textarea"
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
              <input
                key={index}
                type="text"
                className="modal-input"
                value={speaker}
                onChange={(e) => handleSpeakerChange(index, e.target.value)}
                placeholder={`Enter speaker ${editedSpeakers.length > 1 ? index + 1 : ''}...`}
              />
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
                className="modal-select"
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
              className="modal-select"
              value={editedVoiceMode}
              onChange={(e) => setEditedVoiceMode(e.target.value)}
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
          <button className="modal-save-btn" onClick={handleSaveChanges}>
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

export default CellEditModal;

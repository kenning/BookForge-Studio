import React from 'react';

interface NewDialogueButtonProps {
  selectedCells: Set<string>;
  onCreateDialogue: () => void;
  style?: React.CSSProperties;
}

const NewDialogueButton: React.FC<NewDialogueButtonProps> = ({
  selectedCells,
  onCreateDialogue,
  style,
}) => {
  if (selectedCells.size <= 1) {
    return null;
  }

  return (
    <div
      className="new-dialogue-button"
      style={{
        position: 'absolute',
        zIndex: 30,
        ...style,
      }}
    >
      <button
        className="dialogue-button"
        onClick={onCreateDialogue}
        title={`Create dialogue from ${selectedCells.size} selected cells`}
      >
        <span className="dialogue-icon">💬</span>
        <span>New Dialogue</span>
      </button>
    </div>
  );
};

export default NewDialogueButton;

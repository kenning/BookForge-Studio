import React from 'react';
import { AddCellButtonProps } from '../types';

const AddCellButton: React.FC<AddCellButtonProps> = ({
  rowIndex,
  onAddCell,
  isMultiSpeaker = false,
  style,
}) => {
  return (
    <div
      className={`add-cell-button ${isMultiSpeaker ? 'multi-speaker-button' : ''}`}
      style={style}
    >
      <button className="new-button" onClick={() => onAddCell(rowIndex)}>
        <span className="plus-icon">+</span>
        <span>New{isMultiSpeaker ? ' Dialogue' : ''}</span>
      </button>
    </div>
  );
};

export default AddCellButton;

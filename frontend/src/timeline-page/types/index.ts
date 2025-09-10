export type TimelineCellGenerationDisplayStatus =
  | 'not_generated_yet'
  | 'pending'
  | 'processing'
  | 'completed'
  | 'error';

export interface TimelineRowProps {
  row: any;
  rowIndex: number;
  selectedCells: Set<string>;
  onCellSelect: (rowIndex: number, cellIndex: number) => void;
  onCellToggleCheckbox: (rowIndex: number, cellIndex: number) => void;
}

export interface AddCellButtonProps {
  rowIndex: number;
  onAddCell: (rowIndex: number) => void;
  isMultiSpeaker?: boolean;
  style?: React.CSSProperties;
}

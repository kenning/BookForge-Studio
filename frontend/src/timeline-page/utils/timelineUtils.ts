import { ScriptHistoryGridCell, ScriptHistoryGridRow } from '../../types/readableBackendTypes';

export const CELL_WIDTH = 320;
export const ROW_HEIGHT = 200;
export const LEFT_MARGIN = 80;

// Calculate the position of a cell based on its row, column, and the current slide offset
export const calculateCellPosition = (
  rowIndex: number,
  cellIndex: number,
  currentIndex: number,
  cellHeight: number = 1
) => {
  const slideOffset = -currentIndex * CELL_WIDTH;

  return {
    left: cellIndex * CELL_WIDTH + slideOffset + LEFT_MARGIN,
    top: 0,
    width: CELL_WIDTH - 20, // Account for margins
    height: cellHeight * ROW_HEIGHT - 20, // Account for margins
  };
};

export const makeHiddenCell = (row: ScriptHistoryGridRow): ScriptHistoryGridCell => {
  const lastCell = row.cells[row.cells.length - 1];
  return {
    ...lastCell,
    hide: true,
    generated_filepath: '',
    waveform_data: [],
  };
};

export const newPointerCell = (): ScriptHistoryGridCell => ({
  hide: false,
  height: 1,
  texts: ['Blah blah blah'],
  speakers: ['narrator'],
  actors: ['narrator'],
  voice_mode: 'voice_mode_1.json',
  generated_filepath: '',
  waveform_data: [],
});

// Timeline styling utilities
export const getGradientStyle = () => {
  const wht = 'var(--timeline-gradient-bg)';
  const purp = 'var(--timeline-gradient-fg)';
  const gradientMargin = 4;
  const left1 = LEFT_MARGIN - gradientMargin;
  const left2 = LEFT_MARGIN + gradientMargin;
  const right1 = LEFT_MARGIN + CELL_WIDTH - gradientMargin;
  const right2 = right1 + gradientMargin * 2;
  const firstpart = `linear-gradient(to right, ${wht} 0%, ${wht} ${left1}px, ${purp} ${left2}px,`;

  return {
    background: `${firstpart} ${purp} ${right1}px, ${wht} ${right2}px, ${wht} 100%)`,
  };
};

// Multi-speaker cell utilities
export const getMultiSpeakerInfo = (grid: any[]) => {
  const multiSpeakerCells = new Map<
    string,
    {
      startRow: number;
      height: number;
      cellIndex: number;
      cell: ScriptHistoryGridCell;
    }
  >();

  grid.forEach((row, rowIndex) => {
    row.cells.forEach((cell: ScriptHistoryGridCell, cellIndex: number) => {
      if (cell.height > 1 && !cell.hide) {
        const key = `${rowIndex}-${cellIndex}`;
        multiSpeakerCells.set(key, {
          startRow: rowIndex,
          height: cell.height,
          cellIndex,
          cell,
        });
      }
    });
  });

  return multiSpeakerCells;
};

export const isRowCoveredByMultiSpeaker = (
  multiSpeakerCells: Map<string, any>,
  rowIndex: number,
  cellIndex: number
) => {
  return Array.from(multiSpeakerCells.values()).some(
    (msInfo: any) =>
      msInfo.startRow < rowIndex &&
      msInfo.startRow + msInfo.height > rowIndex &&
      msInfo.cellIndex === cellIndex
  );
};

// Check if selected cells are consecutive (no gaps)
export const areSelectedCellsConsecutive = (selectedCells: Set<string>) => {
  if (selectedCells.size <= 1) {
    return false;
  }

  // Group cells by row
  const rowGroups: { [rowIndex: number]: number[] } = {};

  Array.from(selectedCells).forEach(cellKey => {
    const [rowIndex, cellIndex] = cellKey.split('-').map(Number);
    if (!rowGroups[rowIndex]) {
      rowGroups[rowIndex] = [];
    }
    rowGroups[rowIndex].push(cellIndex);
  });

  // Check each row has consecutive cells
  const rowIndices = Object.keys(rowGroups)
    .map(Number)
    .sort((a, b) => a - b);
  for (let i = 1; i < rowIndices.length; i++) {
    if (rowIndices[i] !== rowIndices[i - 1] + 1) {
      return false; // Gap found
    }
  }

  return true;
};

// Calculate center position for selected cells
export const calculateSelectedCellsCenter = (selectedCells: Set<string>) => {
  if (selectedCells.size === 0) {
    return { centerX: 0, centerY: 0 };
  }

  const positions = Array.from(selectedCells).map(cellKey => {
    const [rowIndex, cellIndex] = cellKey.split('-').map(Number);
    const position = calculateCellPosition(rowIndex, cellIndex, cellIndex, 1);
    return {
      centerY: rowIndex * ROW_HEIGHT + position.height / 2,
    };
  });

  // Off by one error for some reason.
  const centerY = positions.reduce((sum, pos) => sum + (pos.centerY - 1), 0) / positions.length;

  return { centerY };
};

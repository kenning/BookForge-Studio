import React from 'react';
import { GenerationQueueItem, useTimelineGenerationStore } from '../store/timelineGenerationStore';
import { filesApi } from '../../api/api';
import AudioPlayer from '../../components/AudioPlayer';
import { ScriptHistoryGridRow } from '../../types/readableBackendTypes';

interface GenerationQueueProps {
  queue: GenerationQueueItem[];
  isProcessing: boolean;
  selectedCount: number;
  onEnqueueSelected: () => void;
}

const QueueItem: React.FC<{ item: GenerationQueueItem }> = ({ item }) => {
  const { status, progress, texts, error } = item;
  const progressPercentage = (progress?.percentage || 0).toFixed(1);
  const stepName = progress?.stepName || '';
  const stepNum = progress?.stepNum || 0;
  const totalSteps = progress?.totalSteps || 0;

  return (
    <div
      className="queue-item"
      style={{
        marginBottom: '0.25rem',
        padding: '0.25rem',
        border: '1px solid var(--border-primary)',
        borderRadius: '6px',
      }}
    >
      <div className="queue-item-text">"{texts.join(' ')}"</div>
      {status === 'processing' && (
        <div className="progress-container">
          <div
            className="progress-bar-background"
            style={{
              width: '100%',
              height: '6px',
              backgroundColor: 'var(--text-secondary)',
              borderRadius: '3px',
              overflow: 'hidden',
            }}
          >
            <div
              className="progress-bar-fill"
              style={{
                width: `${progressPercentage}%`,
                height: '100%',
                backgroundColor: 'var(--accent-primary)',
                transition: 'width 0.3s ease',
                borderRadius: '3px',
              }}
            />
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              justifyContent: 'space-between',
              marginTop: '4px',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {progressPercentage}%&nbsp;&nbsp;&nbsp;({stepNum}/{totalSteps})
            </div>
            <div
              className="progress-step"
              style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}
            >
              {stepName || status}
            </div>
          </div>
        </div>
      )}
      {status === 'error' && error && (
        <div
          className="error-message"
          style={{
            fontSize: '12px',
            color: 'var(--accent-danger)',
            marginTop: '4px',
            marginBottom: '4px',
          }}
        >
          Error: {error}
        </div>
      )}
      {status === 'pending' && (
        <div
          className="completed-info"
          style={{ fontSize: '12px', color: 'var(--accent-warning)', marginTop: '4px' }}
        >
          Enqueued
        </div>
      )}
      {status === 'completed' && (
        <div
          className="completed-info"
          style={{ fontSize: '12px', color: 'var(--accent-success)', marginTop: '4px' }}
        >
          Completed
        </div>
      )}
    </div>
  );
};

const GenerationQueue: React.FC<GenerationQueueProps> = ({
  queue,
  isProcessing,
  selectedCount,
  onEnqueueSelected,
}) => {
  const {
    script,
    isExporting,
    exportProgress,
    exportStepName,
    exportedFilePath,
    exportCurrentTimeline,
  } = useTimelineGenerationStore();

  const totalItems = queue.length;
  const remainingItems = queue.filter(
    item => item.status === 'pending' || item.status === 'processing'
  ).length;
  const completedItems = queue.filter(item => item.status === 'completed').length;
  const errorItems = queue.filter(item => item.status === 'error').length;

  // Check if timeline has exportable audio
  const exportableAudioArr: Array<ScriptHistoryGridRow> = script
    ? script.history_grid.grid.filter(row => {
        const currentCell = row.cells[row.current_index];
        return (
          currentCell &&
          currentCell.generated_filepath &&
          currentCell.generated_filepath !== 'error' &&
          !currentCell.hide
        );
      })
    : [];
  const lenAllRows = script ? script.history_grid.grid.length : 0;
  const hasExportableAudio = exportableAudioArr.length > 0;

  return (
    <div className="generation-queue-container">
      <div className="generation-queue-header" style={{ marginBottom: '16px' }}>
        <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)' }}>Generation Queue</h3>

        {selectedCount > 0 && (
          <button
            className="enqueue-btn"
            onClick={onEnqueueSelected}
            disabled={isProcessing}
            style={{
              padding: '8px 16px',
              backgroundColor: isProcessing ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              marginBottom: '8px',
            }}
          >
            Generate {selectedCount} Selected
          </button>
        )}

        {totalItems > 0 && (
          <div
            className="queue-summary"
            style={{ fontSize: '14px', color: 'var(--text-secondary)' }}
          >
            {isProcessing ? (
              <span>Generating... {remainingItems} remaining</span>
            ) : (
              <span>
                {completedItems} completed, {errorItems} errors, {totalItems} total
              </span>
            )}
          </div>
        )}
      </div>

      <div className="generation-queue-content">
        {queue.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: '20px' }}>
            No items in queue. Select cells and click "Generate" to add them.
          </div>
        ) : (
          <div className="queue-items">
            {queue.map(item => (
              <QueueItem key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>

      {/* Export Section */}
      <div
        className="export-section"
        style={{
          marginTop: '24px',
          borderTop: '1px solid var(--border-primary)',
          paddingTop: '16px',
        }}
      >
        {/* <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)' }}>Export Timeline</h3> */}

        {hasExportableAudio && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: 'calc(100% - 8px)',
              gap: '8px',
            }}
          >
            <div style={{ width: '50%' }}>
              <button
                className="export-btn"
                onClick={exportCurrentTimeline}
                disabled={isExporting}
                style={{
                  padding: '8px 16px',
                  backgroundColor: isExporting ? 'var(--bg-tertiary)' : 'var(--accent-secondary)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isExporting ? 'not-allowed' : 'pointer',
                  marginRight: '8px',
                  width: '100%',
                }}
              >
                {isExporting
                  ? 'Exporting...'
                  : `Export ${exportableAudioArr.length} / ${lenAllRows}`}
              </button>
            </div>
            <div style={{ width: '50%', textAlign: 'right' }}>
              {exportedFilePath && (
                <a href={filesApi.getFileUrl(exportedFilePath)} download>
                  <button
                    className="export-btn"
                    style={{
                      padding: '8px 16px',
                      backgroundColor: 'var(--accent-primary)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      width: '100%',
                      marginLeft: '8px',
                    }}
                  >
                    Download
                  </button>
                </a>
              )}
            </div>
          </div>
        )}

        {!hasExportableAudio && (
          <div style={{ color: 'var(--text-tertiary)', fontSize: '14px', marginBottom: '8px' }}>
            No audio clips to export. Generate some audio first.
          </div>
        )}

        {isExporting && (
          <div className="export-progress">
            <div
              className="progress-bar-background"
              style={{
                width: '100%',
                height: '6px',
                backgroundColor: 'var(--text-secondary)',
                borderRadius: '3px',
                overflow: 'hidden',
                marginBottom: '4px',
              }}
            >
              <div
                className="progress-bar-fill"
                style={{
                  width: `${exportProgress}%`,
                  height: '100%',
                  backgroundColor: 'var(--accent-secondary)',
                  transition: 'width 0.3s ease',
                  borderRadius: '3px',
                }}
              />
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {exportProgress.toFixed(1)}% - {exportStepName}
            </div>
          </div>
        )}

        {exportedFilePath && !isExporting && (
          <div className="export-result" style={{ marginTop: '8px' }}>
            {/* <div style={{ fontSize: '12px', color: 'var(--accent-success)', marginBottom: '8px' }}>
              ✅ Export complete!
            </div> */}

            {/* Audio Player */}
            <div style={{ marginBottom: '8px' }}>
              <AudioPlayer filename={exportedFilePath} />
            </div>

            {/* Download Section */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                {exportedFilePath}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GenerationQueue;

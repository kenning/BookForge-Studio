import React, { ReactNode, useState } from 'react';
import { useDroppable } from '@dnd-kit/core';
import { FileInfo } from '../types/readableBackendTypes';
import AudioPlayer from './AudioPlayer';
import { filesApi } from '../api/api';

interface DropZoneProps {
  id: string;
  label: string;
  acceptedTypes?: string[];
  droppedFile?: FileInfo | null;
  onFileDrop?: (file: FileInfo) => void;
  onFileRemove?: () => void;
  className?: string;
}

const DropZone: React.FC<DropZoneProps> = ({
  id,
  label,
  acceptedTypes,
  droppedFile,
  onFileDrop,
  onFileRemove,
  className = '',
}) => {
  const [externalDropError, setExternalDropError] = useState<ReactNode | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);

  const { isOver, setNodeRef } = useDroppable({
    id,
    data: {
      accepts: acceptedTypes || ['file'],
    },
  });

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Check if files are being dragged using dataTransfer.types
    if (e.dataTransfer.types.includes('Files')) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Only clear drag over if we're leaving the dropzone itself
    if (e.currentTarget.contains(e.relatedTarget as Node) === false) {
      setIsDragOver(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Clear drag over state
    setIsDragOver(false);

    // Check if this is an external drop (files from desktop/OS)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0]; // Take only the first file

      // Validate file type
      const allowedExtensions = [
        '.txt',
        '.md',
        '.csv',
        '.wav',
        '.mp3',
        '.m4a',
        '.aac',
        '.ogg',
        '.flac',
      ];
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();

      if (!allowedExtensions.includes(fileExtension)) {
        setExternalDropError(
          <span>
            Unsupported file type '{fileExtension}'.
            <br />
            Allowed types: {allowedExtensions.join(', ')}
          </span>
        );
        setTimeout(() => setExternalDropError(null), 5000);
        return;
      }

      setIsUploading(true);
      setExternalDropError(null);

      try {
        // Upload the file
        const response = await filesApi.uploadFile(file);
        console.log('response', response);

        // Call onFileDrop with the new file info if callback is provided
        if (onFileDrop) {
          onFileDrop(response.file_info);
        }
      } catch (error: any) {
        console.error('Upload failed:', error);
        setExternalDropError(<span>Upload failed: {error.message || 'Unknown error'}</span>);
        setTimeout(() => setExternalDropError(null), 5000);
      } finally {
        setIsUploading(false);
      }
    }
  };

  return (
    <div
      ref={setNodeRef}
      className={`drop-zone ${isOver ? 'drop-zone--over' : ''} ${isDragOver ? 'drop-zone--drag-over' : ''} ${className}`}
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="drop-zone-label">{label}</div>

      {externalDropError && (
        <div
          className="drop-zone-error"
          style={{
            color: '#dc3545',
            background: '#f8d7da',
            border: '1px solid #f5c6cb',
            borderRadius: '4px',
            padding: '8px',
            margin: '8px 0',
            fontSize: '14px',
          }}
        >
          {externalDropError}
        </div>
      )}
      {isDragOver && (
        <div className="drop-zone-drag-over">
          <div className="drop-zone-text">Drop here!</div>
        </div>
      )}

      {isUploading && (
        <div
          className="drop-zone-uploading"
          style={{
            color: '#0066cc',
            background: '#e7f3ff',
            border: '1px solid #b3d9ff',
            borderRadius: '4px',
            padding: '8px',
            margin: '8px 0',
            fontSize: '14px',
          }}
        >
          Uploading file...
        </div>
      )}

      {droppedFile ? (
        <div className="drop-zone-content">
          {droppedFile.file_type === 'audio' ? (
            <AudioPlayer filename={droppedFile.path} />
          ) : (
            <div className="file-preview">
              <span className="file-icon">📄</span>
              <span className="file-name">{droppedFile.name}</span>
            </div>
          )}

          <button className="remove-file-btn" onClick={onFileRemove} title="Remove file">
            ×
          </button>
        </div>
      ) : (
        <div className="drop-zone-placeholder">
          <div className="drop-zone-icon">📁</div>
          {/* <div className="drop-zone-text">Drop {acceptedTypes?.join(' or ') || 'file'} here</div> */}
        </div>
      )}
    </div>
  );
};

export default DropZone;

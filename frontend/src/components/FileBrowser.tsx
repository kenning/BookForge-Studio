import React, { useState, useEffect } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { filesApi, ApiError } from '../api/api';
import { DirectoryInfo, FileInfo } from '../types/readableBackendTypes';

interface FileBrowserProps {
  initialFileTypeFilter?: string[];
  viewMode?: 'tree' | 'flat';
  className?: string;
  onFileSelect?: (file: FileInfo) => void;
}

interface DraggableFileItemProps {
  file: FileInfo;
  onSelect?: (file: FileInfo) => void;
}

const DraggableFileItem: React.FC<DraggableFileItemProps> = ({ file, onSelect }) => {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `file-${file.path}`,
    data: {
      type: 'file',
      file: file,
    },
  });

  const style = {
    opacity: isDragging ? 0.5 : 1,
  };

  let icon = '📄';
  switch (file.file_type) {
    case 'audio':
      icon = '🎵';
      break;
    case 'text':
      icon = '📄';
      break;
    case 'other':
      icon = '📁';
      break;
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`draggable-file-item ${isDragging ? 'dragging' : ''}`}
      onClick={() => onSelect?.(file)}
    >
      <span className="file-icon">{icon}</span>
      <span className="file-name">{file.name}</span>
      <span className="file-size">{formatFileSize(file.size || 0)}</span>
    </div>
  );
};

interface FolderItemProps {
  directory: DirectoryInfo;
  level: number;
  fileTypeFilter?: string[];
  onFileSelect?: (file: FileInfo) => void;
}

const FolderItem: React.FC<FolderItemProps> = ({
  directory,
  level,
  fileTypeFilter,
  onFileSelect,
}) => {
  const [isExpanded, setIsExpanded] = useState(level === 0); // Root folder starts expanded

  const filteredFiles = fileTypeFilter
    ? directory.files.filter(file => fileTypeFilter.includes(file.file_type))
    : directory.files;

  const hasVisibleContent =
    filteredFiles.length > 0 ||
    directory.directories.some(subdir => hasVisibleFiles(subdir, fileTypeFilter));

  if (!hasVisibleContent) return null;

  return (
    <div className="folder-item">
      <div
        className="folder-header"
        style={{ paddingLeft: `${level * 20}px` }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="folder-toggle">{isExpanded ? '📂' : '📁'}</span>
        <span className="folder-name">{directory.name}</span>
        <span className="folder-count">({filteredFiles.length} files)</span>
      </div>

      {isExpanded && (
        <div className="folder-content">
          {filteredFiles.map((file, index) => (
            <div key={`${file.path}-${index}`} style={{ paddingLeft: `${(level + 1) * 20}px` }}>
              <DraggableFileItem file={file} onSelect={onFileSelect} />
            </div>
          ))}

          {directory.directories.map((subdir, index) => (
            <FolderItem
              key={`${subdir.path}-${index}`}
              directory={subdir}
              level={level + 1}
              fileTypeFilter={fileTypeFilter}
              onFileSelect={onFileSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const FileBrowser: React.FC<FileBrowserProps> = ({
  initialFileTypeFilter,
  viewMode: initialViewMode = 'tree',
  className = '',
  onFileSelect,
}) => {
  const [directoryStructure, setDirectoryStructure] = useState<DirectoryInfo | null>(null);
  const [flatFiles, setFlatFiles] = useState<FileInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'tree' | 'flat'>(initialViewMode);
  const [fileTypeFilter, setFileTypeFilter] = useState<string[]>(initialFileTypeFilter || []);

  const loadFiles = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await filesApi.listFiles('input');

      setDirectoryStructure(response.directory_structure);
      setFlatFiles(response.flat_files || []);
    } catch (err) {
      const errorMessage =
        err instanceof ApiError ? err.message : 'Failed to load files: ' + (err as Error).message;
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter files whenever the filter changes
  const filteredFlatFiles =
    fileTypeFilter.length > 0
      ? flatFiles.filter(
          file => fileTypeFilter.length === 0 || fileTypeFilter.includes(file.file_type)
        )
      : flatFiles;

  useEffect(() => {
    loadFiles();
  }, []);

  if (isLoading) {
    return <div className={`file-browser loading ${className}`}>Loading files...</div>;
  }

  if (error) {
    return (
      <div className={`file-browser error ${className}`}>
        <p>Error: {error}</p>
        <button onClick={loadFiles}>Retry</button>
      </div>
    );
  }

  return (
    <div className={`file-browser workflow-components-browser ${className}`}>
      <h3>Input Files</h3>
      <div className="file-browser-header">
        <div className="filter-controls">
          <select
            value={fileTypeFilter.length === 1 ? fileTypeFilter[0] : 'all'}
            onChange={e => {
              if (e.target.value === 'all') {
                setFileTypeFilter([]);
              } else {
                setFileTypeFilter([e.target.value]);
              }
            }}
            className="file-type-filter"
          >
            <option value="all">All Files</option>
            <option value="audio">Audio Files</option>
            <option value="text">Text Files</option>
          </select>
        </div>
        <div className="view-controls">
          <button
            className={viewMode === 'tree' ? 'active' : ''}
            onClick={() => setViewMode('tree')}
          >
            Tree
          </button>
          <button
            className={viewMode === 'flat' ? 'active' : ''}
            onClick={() => setViewMode('flat')}
          >
            Flat
          </button>
        </div>
        <button onClick={loadFiles} className="refresh-btn">
          🔄
        </button>
      </div>

      <div className="file-content">
        {viewMode === 'tree' && directoryStructure && (
          <FolderItem
            directory={directoryStructure}
            level={0}
            fileTypeFilter={fileTypeFilter}
            onFileSelect={onFileSelect}
          />
        )}

        {viewMode === 'flat' && (
          <div className="flat-file-list">
            {filteredFlatFiles.map((file, index) => (
              <DraggableFileItem
                key={`${file.path}-${index}`}
                file={file}
                onSelect={onFileSelect}
              />
            ))}
          </div>
        )}

        {((viewMode === 'tree' && !hasVisibleFiles(directoryStructure, fileTypeFilter)) ||
          (viewMode === 'flat' && filteredFlatFiles.length === 0)) && (
          <div className="empty-file-list">
            No {fileTypeFilter.length > 0 ? fileTypeFilter.join(', ') : ''} files found
          </div>
        )}
      </div>
    </div>
  );
};

// Helper functions
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function hasVisibleFiles(directory: DirectoryInfo | null, fileTypeFilter?: string[]): boolean {
  if (!directory) return false;

  const visibleFiles = fileTypeFilter
    ? directory.files.filter(file => fileTypeFilter.includes(file.file_type))
    : directory.files;

  return (
    visibleFiles.length > 0 ||
    directory.directories.some(subdir => hasVisibleFiles(subdir, fileTypeFilter))
  );
}

export default FileBrowser;

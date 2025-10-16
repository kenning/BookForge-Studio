import React, { useEffect, useState } from 'react';
import { filesApi, ApiError } from '../api/api';
import { FileInfo, DirectoryInfo } from '../types/readableBackendTypes';

export interface SaveLoadBrowserCallbacks {
  onFileClick?: (file: FileInfo) => void;
  onSave?: () => void;
  onRefresh?: () => void;
  onNew?: () => void;
  onRefreshReady?: (refreshFn: () => void) => void;
}

interface SaveLoadBrowserProps {
  directoryType: string;
  title?: string | React.ReactNode;
  callbacks?: SaveLoadBrowserCallbacks;
  className?: string;
  fileFilter?: (file: FileInfo) => boolean;
  externalError?: string | null;

  // Props for current item management
  currentItemName?: string;
  isDirty?: boolean;
  isSaving?: boolean;
}

interface FolderItemProps {
  directory: DirectoryInfo;
  level: number;
  fileFilter?: (file: FileInfo) => boolean;
  onFileClick?: (file: FileInfo) => void;
  currentItemName?: string;
}

const FolderItem: React.FC<FolderItemProps> = ({
  directory,
  level,
  fileFilter,
  onFileClick,
  currentItemName,
}) => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(() => {
    const stored = localStorage.getItem('expandedFolders');
    console.log('initial load: ', stored)
    return stored ? new Set(JSON.parse(stored)) : new Set();
  });

  const isExpanded = level === 0 || expandedFolders.has(directory.path);

  const toggleExpanded = () => {
    const newExpanded = new Set(expandedFolders);
    if (isExpanded) {
      newExpanded.delete(directory.path);
    } else {
      newExpanded.add(directory.path);
    }
    setExpandedFolders(newExpanded);
    console.log(newExpanded)
    // @ts-ignore
    localStorage.setItem('expandedFolders', JSON.stringify([...newExpanded]));
  };

  const filteredFiles = fileFilter ? directory.files.filter(fileFilter) : directory.files;

  const hasVisibleContent =
    filteredFiles.length > 0 ||
    directory.directories.some(subdir => hasVisibleFiles(subdir, fileFilter));

  if (!hasVisibleContent) return null;

  return (
    <div className="folder-item">
      <div
        className="folder-header"
        style={{ paddingLeft: `${level * 20}px` }}
        onClick={toggleExpanded}
      >
        <span className="folder-toggle">{isExpanded ? '📂' : '📁'}</span>
        <span className="folder-name">{directory.name}</span>
        <span className="folder-count">({filteredFiles.length} files)</span>
      </div>

      {isExpanded && (
        <div className="folder-content">
          {filteredFiles.map((file, index) => {
            let icon = '📄';
            switch (file.file_type) {
              case 'audio':
                icon = '🎵';
                break;
              case 'text':
                icon = '📄';
                break;
              case 'actor':
                if (file.actor_data?.is_favorite) {
                  icon = '⭐';
                } else {
                  icon = '🎭';
                }
                break;
              case 'script':
                icon = '📝';
                break;
            }

            const isCurrentFile =
              currentItemName &&
              (file.name === currentItemName ||
                file.name === `${currentItemName}.json` ||
                file.name.replace(/\.(json|txt|csv)$/, '') === currentItemName);

            return (
              <div
                key={`${file.path}-${index}`}
                className={`file-item ${isCurrentFile ? 'current-file' : ''}`}
                style={{ paddingLeft: `${(level + 1) * 20}px` }}
                onClick={() => onFileClick?.(file)}
              >
                <span className="file-icon">{icon}</span>
                <span className="file-name">{file.name.replace(/\.(json|txt|csv)$/, '')}</span>
              </div>
            );
          })}

          {directory.directories.map((subdir, index) => (
            <FolderItem
              key={`${subdir.path}-${index}`}
              directory={subdir}
              level={level + 1}
              fileFilter={fileFilter}
              onFileClick={onFileClick}
              currentItemName={currentItemName}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Helper function to check if directory has visible files
function hasVisibleFiles(
  directory: DirectoryInfo | null,
  fileFilter?: (file: FileInfo) => boolean
): boolean {
  if (!directory) return false;

  const visibleFiles = fileFilter ? directory.files.filter(fileFilter) : directory.files;

  return (
    visibleFiles.length > 0 ||
    directory.directories.some(subdir => hasVisibleFiles(subdir, fileFilter))
  );
}

const SaveLoadBrowser: React.FC<SaveLoadBrowserProps> = ({
  directoryType,
  title,
  callbacks = {},
  className = '',
  fileFilter,
  externalError,
  currentItemName,
  isDirty = false,
  isSaving = false,
}) => {
  const [directoryStructure, setDirectoryStructure] = useState<DirectoryInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Internal state to track if current item has been saved in this session
  const [hasBeenSaved, setHasBeenSaved] = useState(false);
  const [lastCurrentItemName, setLastCurrentItemName] = useState<string>('');

  // Reset hasBeenSaved when currentItemName changes (new item loaded)
  useEffect(() => {
    if (currentItemName !== lastCurrentItemName) {
      setHasBeenSaved(false);
      setLastCurrentItemName(currentItemName || '');
    }
  }, [currentItemName, lastCurrentItemName]);

  const loadFiles = React.useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await filesApi.listFiles(directoryType);

      setDirectoryStructure(response.directory_structure);

      callbacks.onRefresh?.();
    } catch (err) {
      const errorMessage =
        err instanceof ApiError ? err.message : 'Failed to load files: ' + (err as Error).message;
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [directoryType, fileFilter]);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // Provide refresh function to parent - run only when onRefreshReady callback is first provided
  useEffect(() => {
    if (callbacks.onRefreshReady) {
      callbacks.onRefreshReady(loadFiles);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [callbacks.onRefreshReady]);

  const handleFileClick = (file: FileInfo) => {
    callbacks.onFileClick?.(file);
  };

  const handleSaveClick = () => {
    callbacks.onSave?.();
    setHasBeenSaved(true); // Mark as saved when save is clicked
  };

  const getSaveButtonLabel = () => {
    if (isSaving) return 'Saving...';
    if (!isDirty && hasBeenSaved) return 'Saved!';
    return 'Save';
  };

  const getSaveButtonClassName = () => {
    if (!isDirty && hasBeenSaved) return 'save-btn saved';
    return 'save-btn';
  };

  const isSaveButtonDisabled = () => {
    return isSaving || (!isDirty && !!currentItemName);
  };

  const displayTitle = title || `${directoryType.charAt(0).toUpperCase() + directoryType.slice(1)}`;

  return (
    <div className={`file-browser save-load-browser ${className}`}>
      <div className="file-browser-header">
        <h3>{displayTitle}</h3>
        <div className="header-buttons">
          {currentItemName && (
            <button
              className={getSaveButtonClassName()}
              onClick={handleSaveClick}
              disabled={isSaveButtonDisabled()}
            >
              {getSaveButtonLabel()}
            </button>
          )}
          <button
            className="new-btn"
            onClick={() => callbacks.onNew?.()}
            disabled={isLoading}
            title="Create New"
          >
            ✨ New
          </button>
          <button onClick={loadFiles} disabled={isLoading} className="refresh-btn" title="Refresh">
            🔄
          </button>
        </div>
      </div>

      {/* Current Item Display */}
      {/* {currentItemName && (
        <div className="current-item-section">
          <div className="current-item-display">
            <span className="current-item-label">Current:</span>
            <span className="current-item-name">{currentItemName}</span>
            {isDirty && <span className="dirty-indicator">●</span>}
          </div>
          <button
            className={getSaveButtonClassName()}
            onClick={handleSaveClick}
            disabled={isSaveButtonDisabled()}
          >
            {getSaveButtonLabel()}
          </button>
        </div>
      )} */}

      {isLoading && <div className="file-browser-loading">Loading files...</div>}

      {isLoading ? (
        <div className="file-list" />
      ) : (
        <div className="file-list">
          {directoryStructure && (
            <FolderItem
              directory={directoryStructure}
              level={0}
              fileFilter={fileFilter}
              onFileClick={handleFileClick}
              currentItemName={currentItemName}
            />
          )}

          {directoryStructure && !hasVisibleFiles(directoryStructure, fileFilter) && (
            <div className="empty-file-list">No files found in {directoryType}</div>
          )}
        </div>
      )}

      {(error || externalError) && (
        <div className="file-browser-error">
          <p>{externalError || error}</p>
          {error && <button onClick={loadFiles}>Retry</button>}
        </div>
      )}
    </div>
  );
};

export default SaveLoadBrowser;

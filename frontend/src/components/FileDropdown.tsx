import React, { useState, useEffect } from 'react';
import { filesApi, ApiError } from '../api/api';
import { FileInfo } from '../types/readableBackendTypes';

interface FileDropdownProps {
  directoryType: string;
  fileFilter?: (file: FileInfo) => boolean;
  onFileSelect: (filePath: string, fileContent: any) => void;
  placeholder?: string;
  value?: string;
  className?: string;
  disabled?: boolean;
}

// TODO use this in timeline page (timeline cell and speakerassignmentselection)
const FileDropdown: React.FC<FileDropdownProps> = ({
  directoryType,
  fileFilter,
  onFileSelect,
  placeholder = 'Select a file...',
  value,
  className = '',
  disabled = false,
}) => {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedValue, setSelectedValue] = useState<string>(value || '');

  // Load files when component mounts
  useEffect(() => {
    const loadFiles = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await filesApi.listFiles(directoryType);

        let fileList = response.flat_files || [];

        // Apply file filter if provided
        if (fileFilter) {
          fileList = fileList.filter(fileFilter);
        }

        setFiles(fileList);
      } catch (err) {
        const errorMessage =
          err instanceof ApiError ? err.message : 'Failed to load files: ' + (err as Error).message;
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    loadFiles();
  }, [directoryType, fileFilter]);

  // Update selected value when value prop changes
  useEffect(() => {
    setSelectedValue(value || '');
  }, [value]);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedFileName = event.target.value;
    setSelectedValue(selectedFileName);

    if (!selectedFileName) {
      onFileSelect('', null);
      return;
    }

    // Find the selected file
    const selectedFile = files.find(file => file.name === selectedFileName);
    if (!selectedFile) {
      console.error('Selected file not found:', selectedFileName);
      return;
    }

    try {
      // Use embedded data from FileInfo
      let fileData = null;
      if (selectedFile.actor_data) {
        fileData = selectedFile.actor_data;
      } else if (selectedFile.voice_mode_data) {
        fileData = selectedFile.voice_mode_data;
      }

      // Call the callback with the file path and data
      onFileSelect(selectedFile.path, fileData);
    } catch (err) {
      console.error('Failed to load file data:', err);
      setError('Failed to load file data');
    }
  };

  const fileToOption = (file: FileInfo, index: number) => (
    <option key={`${file.path}-${index}`} value={file.name}>
      {file.name.replace(/\.(json|txt|csv)$/, '')}
    </option>
  );

  const fileOptions: React.ReactNode[] = [];
  if (directoryType === 'actors') {
    const favoriteActors: FileInfo[] = [];
    const nonFavoriteActors: FileInfo[] = [];
    for (const file of files) {
      if (file.actor_data?.is_favorite) {
        favoriteActors.push(file);
      } else {
        nonFavoriteActors.push(file);
      }
    }

    fileOptions.push(
      <option key={`favorite header`} value={''}>
        -- Favorite Actors --
      </option>
    );
    fileOptions.push(favoriteActors.map(fileToOption));
    fileOptions.push(
      <option key="other actors header" value={''}>
        -- Other Actors --
      </option>
    );
    fileOptions.push(nonFavoriteActors.map(fileToOption));
  } else {
    fileOptions.push(files.map(fileToOption));
  }

  return (
    <div className={`file-dropdown ${className}`}>
      <select
        value={selectedValue}
        onChange={handleFileSelect}
        disabled={disabled || isLoading}
        className="file-dropdown-select"
      >
        <option value="">{isLoading ? 'Loading...' : placeholder}</option>
        {fileOptions}
      </select>
      {error && <div className="file-dropdown-error">{error}</div>}
    </div>
  );
};

export default FileDropdown;

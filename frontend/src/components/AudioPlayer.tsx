import React, { useEffect, useRef, useState } from 'react';
import { filesApi } from '../api/api';

interface AudioPlayerProps {
  filename: string;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({ filename }) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const audioUrl = filesApi.getFileUrl(filename);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('ended', handleEnded);
    };
  }, []);

  useEffect(() => {
    if (isPlaying) {
      setIsPlaying(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioUrl]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play();
      setIsPlaying(true);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const newTime = (clickX / rect.width) * duration;

    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const isAudioFile = (filename: string) => {
    const audioExtensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'];
    return audioExtensions.some(ext => filename.toLowerCase().endsWith(ext));
  };

  if (!isAudioFile(filename)) {
    return (
      <div className="file-item">
        <span className="file-icon">📄</span>
        <span className="file-name">{filename}</span>
      </div>
    );
  }

  return (
    <div className="audio-player">
      <audio ref={audioRef} src={audioUrl} preload="metadata" />
      <div className="audio-controls">
        <button onClick={togglePlay} className="play-pause-btn">
          {isPlaying ? '⏸️' : '▶️'}
        </button>
        <span className="file-name">{filename}</span>
        <span className="time-display">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>
      <div className="progress-container" onClick={handleSeek}>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%' }}
          />
        </div>
      </div>
    </div>
  );
};

export default AudioPlayer;

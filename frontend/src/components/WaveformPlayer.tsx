import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { filesApi } from '../api/api';
import { usePlaybackStore } from '../timeline-page/store/timelinePlaybackStore';

const WAVEFORM_WIDTH = 100;
const WAVEFORM_HEIGHT = 100;

interface WaveformPlayerProps {
  filename: string;
  width?: number;
  height?: number;
  waveformData?: number[]; // Pre-calculated peaks
  // New props for external control
  onAudioRefReady?: (audioElement: HTMLAudioElement) => void;
  onAudioRefCleanup?: () => void;
}

const WaveformPlayer: React.FC<WaveformPlayerProps> = React.memo(
  ({
    filename,
    width = WAVEFORM_WIDTH,
    height = WAVEFORM_HEIGHT,
    waveformData: preCalculatedPeaks,
    onAudioRefReady,
    onAudioRefCleanup,
  }) => {
    const audioRef = useRef<HTMLAudioElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    // const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [peaks, setPeaks] = useState<number[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const { goToIndex, isPlaying, play, playlist, currentTrackIndex } = usePlaybackStore();

    // Memoized computed values
    const { isCurrentTrack, preloadType, error, audioUrl } = useMemo(() => {
      const currentTrack = currentTrackIndex >= 0 ? playlist[currentTrackIndex] : null;
      const isCurrentTrack = Boolean(currentTrack && currentTrack.filename === filename);

      const nextTrackIndex = currentTrackIndex + 1;
      const nextTrack = nextTrackIndex < playlist.length ? playlist[nextTrackIndex] : null;
      const isNextTrack = Boolean(nextTrack && nextTrack.filename === filename);

      const preloadType = isNextTrack ? 'auto' : 'metadata';
      const error = filename === 'error';
      const audioUrl = filesApi.getFileUrl(filename);

      return { isCurrentTrack, isNextTrack, preloadType, error, audioUrl };
    }, [filename, currentTrackIndex, playlist]);

    // Register audio ref with external controller on mount
    useEffect(() => {
      if (error) {
        setIsLoading(false);
        return;
      }
      const audio = audioRef.current;
      if (audio && onAudioRefReady) {
        onAudioRefReady(audio);
      }

      return () => {
        if (onAudioRefCleanup) {
          onAudioRefCleanup();
        }
      };
    }, [onAudioRefReady, onAudioRefCleanup, error]);

    // Use pre-calculated peaks or fallback to empty array
    useEffect(() => {
      if (error) {
        setIsLoading(false);
        return;
      }
      if (preCalculatedPeaks && preCalculatedPeaks.length > 0) {
        setPeaks(preCalculatedPeaks);
        setIsLoading(false);
      } else {
        // If no pre-calculated peaks, show loading state
        setIsLoading(true);
        setPeaks([]);
      }
    }, [preCalculatedPeaks, error]);

    // Draw waveform on canvas (only when peaks change)
    const drawWaveform = useCallback(() => {
      if (error) {
        setIsLoading(false);
        return;
      }
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (!canvas || !ctx || peaks.length === 0) return;

      // Create diagonal gradient background (always orange, CSS filter will adjust for non-current tracks)
      const gradient = ctx.createLinearGradient(0, 0, width, height);
      gradient.addColorStop(0, '#f59e0b'); // Amber
      gradient.addColorStop(1, '#d97706'); // Orange
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Draw oscillating waveform line
      ctx.strokeStyle = '#ffffff'; // White line
      ctx.lineWidth = 2;
      ctx.shadowColor = '#ffffff';
      ctx.shadowBlur = 2;

      const pointSpacing = width / (peaks.length - 1);
      const centerY = height / 2;
      const maxAmplitude = (height - 16) / 2; // Leave some padding

      ctx.beginPath();

      for (let i = 0; i < peaks.length; i++) {
        const x = i * pointSpacing;
        // Alternate between positive and negative amplitudes for oscillation
        const amplitude = peaks[i] * maxAmplitude;
        const oscillation = i % 2 === 0 ? amplitude : -amplitude; // Even indices go up, odd go down
        const y = centerY + oscillation;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          const prevX = (i - 1) * pointSpacing;
          const prevAmplitude = peaks[i - 1] * maxAmplitude;
          const prevOscillation = (i - 1) % 2 === 0 ? prevAmplitude : -prevAmplitude;
          const prevY = centerY + prevOscillation;

          // Create smooth curve using quadratic bezier
          const cpX = (prevX + x) / 2;
          // const cpY = (prevY + y) / 2;
          ctx.quadraticCurveTo(cpX, prevY, x, y);
        }
      }

      ctx.stroke();
      ctx.shadowBlur = 0;
    }, [peaks, width, height, error]);

    // Audio event handlers
    useEffect(() => {
      const audio = audioRef.current;
      if (!audio) return;

      const updateTime = () => setCurrentTime(audio.currentTime);
      const updateDuration = () => setDuration(audio.duration);
      // const handleEnded = () => setIsPlaying(false);

      audio.addEventListener('timeupdate', updateTime);
      audio.addEventListener('loadedmetadata', updateDuration);
      // audio.addEventListener('ended', handleEnded);

      return () => {
        audio.removeEventListener('timeupdate', updateTime);
        audio.removeEventListener('loadedmetadata', updateDuration);
        // audio.removeEventListener('ended', handleEnded);
      };
    }, []);

    // Redraw waveform only when peaks change
    useEffect(() => {
      drawWaveform();
    }, [drawWaveform]);

    const togglePlay = () => {
      if (isCurrentTrack) {
        if (isPlaying) {
          console.log('isCurrentTrack and playing');
        } else {
          play();
        }
      } else {
        // Find the playlist index for this track by filename
        const playlistIndex = playlist.findIndex(track => track.filename === filename);
        if (playlistIndex >= 0) {
          goToIndex(playlistIndex);
          if (!isPlaying) {
            setTimeout(() => {
              play();
            }, 100);
          }
        }
      }
    };

    const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
      const audio = audioRef.current;
      if (!audio || !duration) return;

      const rect = e.currentTarget.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const newTime = (clickX / width) * duration;

      audio.currentTime = newTime;
      setCurrentTime(newTime);
      togglePlay();
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
      console.log('not an audio file', filename);
      return (
        <div className="file-item">
          <span className="file-icon">📄</span>
          <span className="file-name">{filename}</span>
        </div>
      );
    }

    return (
      <div className="waveform-player" style={{ width }}>
        <audio ref={audioRef} src={audioUrl} preload={preloadType} />

        <div
          className="waveform-controls"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '4px',
            fontSize: '12px',
          }}
        >
          <button
            onClick={togglePlay}
            className="play-pause-btn"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            {'▶️'}
          </button>
          <span className="time-display waveform-time-display">
            {formatTime(currentTime)} /<br />
            {formatTime(duration)}&nbsp;&nbsp;
          </span>
        </div>

        <div className="waveform-container" style={{ position: 'relative' }}>
          {isLoading && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: '#1e3a8a',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: '12px',
                zIndex: 2,
              }}
            >
              Loading waveform...
            </div>
          )}
          <canvas
            ref={canvasRef}
            width={width}
            height={height}
            onClick={handleCanvasClick}
            style={{
              cursor: 'pointer',
              borderRadius: '4px',
              display: 'block',
              filter: isCurrentTrack ? 'none' : 'hue-rotate(219deg) saturate(0.8) brightness(0.9)',
            }}
          />
          {duration > 0 && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                bottom: 0,
                width: '2px',
                backgroundColor: '#ffffff',
                boxShadow: '0 0 6px #ffffff',
                left: `${(currentTime / duration) * width * 0.98}px`,
                pointerEvents: 'none',
                zIndex: 1,
              }}
            />
          )}
        </div>
      </div>
    );
  }
);

export default WaveformPlayer;

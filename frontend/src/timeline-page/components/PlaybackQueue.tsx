import React, { useEffect } from 'react';
import { usePlaybackStore } from '../store/timelinePlaybackStore';
import { Script } from '../../types/readableBackendTypes';

interface PlaybackQueueProps {
  script: Script | null;
  onScrollToRow?: (rowIndex: number) => void;
}

const PlaybackQueue: React.FC<PlaybackQueueProps> = ({ script, onScrollToRow }) => {
  const {
    playlist,
    currentTrackIndex,
    isPlaying,
    buildPlaylist,
    play,
    pause,
    next,
    previous,
    reset,
    playbackSpeed,
    lowerPlaybackSpeed,
    raisePlaybackSpeed,
    setPlaybackSpeed,
  } = usePlaybackStore();

  // Rebuild playlist when script changes
  useEffect(() => {
    if (script) {
      buildPlaylist(script);
    } else {
      reset();
    }
  }, [script, buildPlaylist, reset]);

  // Auto-scroll to current track (only when playing)
  // Turned off cause its annoying
  // useEffect(() => {
  //   if (
  //     isPlaying &&
  //     currentTrackIndex >= 0 &&
  //     currentTrackIndex < playlist.length &&
  //     onScrollToRow
  //   ) {
  //     const currentTrack = playlist[currentTrackIndex];
  //     onScrollToRow(currentTrack.rowIndex);
  //   }
  // }, [currentTrackIndex, playlist, onScrollToRow, isPlaying]);

  // Don't render if no tracks available
  const currentTrack = currentTrackIndex >= 0 ? playlist[currentTrackIndex] : null;
  const hasNext = currentTrackIndex < playlist.length - 1;
  // const hasPrevious = currentTrackIndex > 0;

  return (
    <div className="playback-queue-container">
      <div className="playback-queue-content">
        <div className="playback-controls">
          {!script || playlist.length === 0 ? null : (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'row',
                    gap: '0.5rem',
                    alignItems: 'center',
                    justifyContent: 'space-around',
                  }}
                >
                  <button
                    className="playback-btn previous"
                    onClick={previous}
                    // disabled={!hasPrevious}
                    title="Previous track"
                  >
                    ⏮️
                  </button>

                  <button
                    className={`playback-btn play-pause${isPlaying ? ' play' : ' pause'}`}
                    onClick={isPlaying ? pause : play}
                    title={isPlaying ? 'Pause' : 'Play'}
                  >
                    {isPlaying ? '⏸️' : '▶️'}
                  </button>

                  <button
                    className="playback-btn next"
                    onClick={next}
                    disabled={!hasNext}
                    title="Next track"
                  >
                    ⏭️
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'row', gap: '0.5rem' }}>
                  <button className="playback-speed-btn change-btn" onClick={lowerPlaybackSpeed}>
                    🐢
                  </button>
                  <button
                    onClick={() => setPlaybackSpeed(1)}
                    className="playback-speed-btn playback-speed-display change-btn"
                  >
                    {playbackSpeed}x
                  </button>
                  <button className="playback-speed-btn change-btn" onClick={raisePlaybackSpeed}>
                    🐇
                  </button>
                </div>
              </div>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <div className={`playback-status ${isPlaying ? 'playing' : 'paused'}`}>
                  <span className="status-text">{isPlaying ? '▶️ Playing' : '⏸️ Paused'}</span>
                </div>
                <div className="track-position">
                  {currentTrackIndex + 1} / {playlist.length}
                </div>
              </div>
            </>
          )}
        </div>

        <div className="playback-info">
          {currentTrack && (
            <div
              className={`current-track-info ${currentTrack.filename ? '' : 'not-generated-yet'}`}
            >
              <span className="track-speaker">
                {currentTrack.speaker}: {currentTrack.filename ? '' : '(not generated yet)'}
              </span>
              <span className="track-text">{currentTrack.text}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PlaybackQueue;

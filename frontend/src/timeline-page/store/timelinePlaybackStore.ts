import { create } from 'zustand';
import { Script } from '../../types/readableBackendTypes';

export interface PlaybackTrack {
  rowIndex: number;
  cellIndex: number;
  filename: string;
  text: string;
  speaker: string;
}

interface PlaybackState {
  // Playback data
  playlist: PlaybackTrack[];
  currentTrackIndex: number;
  isPlaying: boolean;
  isLoading: boolean;

  // Audio control refs - tracks the actual audio elements
  audioRefs: Map<string, HTMLAudioElement>;

  // Actions
  buildPlaylist: (script: Script) => void;
  play: () => void;
  pause: () => void;
  next: () => void;
  previous: () => void;
  // jumpToTrack: (index: number) => void;
  goToIndex: (index: number) => void;
  registerAudioRef: (key: string, audioElement: HTMLAudioElement) => void;
  unregisterAudioRef: (key: string) => void;
  reset: () => void;

  // Playback speed
  playbackSpeed: number;
  lowerPlaybackSpeed: () => void;
  raisePlaybackSpeed: () => void;
  setPlaybackSpeed: (speed: number) => void;

  // Internal
  _playCurrentTrack: () => void;
  _pauseCurrentTrack: () => void;
  onTrackEnded: () => void;
  _getAudioElement: () => HTMLAudioElement | undefined;
  _getCurrentPlaybackTrack: () => PlaybackTrack | undefined;
}

const generateTrackKey = (rowIndex: number, cellIndex: number) => `${rowIndex}-${cellIndex}`;

export const usePlaybackStore = create<PlaybackState>((set, get) => ({
  // Initial state
  playlist: [],
  currentTrackIndex: -1,
  isPlaying: false,
  isLoading: false,
  audioRefs: new Map(),
  playbackSpeed: 1,

  buildPlaylist: (script: Script) => {
    const { currentTrackIndex } = get();
    const tracks: PlaybackTrack[] = [];

    // Build playlist from main track (current_index for each row)
    script.history_grid.grid.forEach((row, rowIndex) => {
      const cellIndex = row.current_index;
      const cell = row.cells[cellIndex];

      if (cell && !cell.hide) {
        const maybeFilename =
          cell.generated_filepath && cell.generated_filepath !== 'error'
            ? cell.generated_filepath
            : '';
        tracks.push({
          rowIndex,
          cellIndex,
          filename: maybeFilename,
          text: cell.texts.join(' '),
          speaker: cell.speakers[0] || 'Unknown',
        });
      }
    });

    set({
      playlist: tracks,
      currentTrackIndex: currentTrackIndex === -1 ? 0 : currentTrackIndex,
      // isPlaying: false,
    });
  },

  play: () => {
    const { playlist, currentTrackIndex } = get();
    if (playlist.length === 0 || currentTrackIndex < 0) return;

    set({ isPlaying: true });
    get()._playCurrentTrack();
  },

  pause: () => {
    set({ isPlaying: false });
    get()._pauseCurrentTrack();
  },

  next: () => {
    const { playlist, currentTrackIndex } = get();
    if (currentTrackIndex < playlist.length - 1) {
      get().goToIndex(currentTrackIndex + 1);
    } else {
      // End of playlist
      set({ isPlaying: false, currentTrackIndex: 0 });
    }
  },

  previous: () => {
    const audioElement = get()._getAudioElement();
    const { currentTrackIndex } = get();
    if (audioElement) {
      if (audioElement.currentTime < 1 && currentTrackIndex > 0) {
        get().goToIndex(currentTrackIndex - 1);
      } else {
        audioElement.currentTime = 0;
      }
    }
  },

  goToIndex: (index: number) => {
    if (get().isPlaying) {
      get().pause();
    }
    set({ currentTrackIndex: index });

    setTimeout(() => get().play(), 100);
  },

  // jumpToTrack: (index: number) => {
  //   const { playlist } = get();
  //   if (index >= 0 && index < playlist.length) {
  //     get().pauseCurrentTrack();
  //     set({ currentTrackIndex: index });

  //     // If we were playing, continue playing the selected track
  //     if (get().isPlaying) {
  //       setTimeout(() => get().playCurrentTrack(), 100);
  //     }
  //   }
  // },

  registerAudioRef: (key: string, audioElement: HTMLAudioElement) => {
    const { audioRefs } = get();
    const newRefs = new Map(audioRefs);
    newRefs.set(key, audioElement);

    // Add ended event listener for automatic progression
    audioElement.addEventListener('ended', get().onTrackEnded);

    set({ audioRefs: newRefs });
  },

  unregisterAudioRef: (key: string) => {
    const { audioRefs } = get();
    const audioElement = audioRefs.get(key);
    if (audioElement) {
      audioElement.removeEventListener('ended', get().onTrackEnded);
    }

    const newRefs = new Map(audioRefs);
    newRefs.delete(key);
    set({ audioRefs: newRefs });
  },

  reset: () => {
    get()._pauseCurrentTrack();
    set({
      playlist: [],
      currentTrackIndex: -1,
      isPlaying: false,
      isLoading: false,
    });
  },

  _playCurrentTrack: () => {
    const { playlist, currentTrackIndex } = get();
    if (currentTrackIndex < 0 || currentTrackIndex >= playlist.length) return;

    const audioElement = get()._getAudioElement();

    if (audioElement) {
      audioElement.playbackRate = get().playbackSpeed;
      audioElement.play().catch(error => {
        console.warn('Failed to play audio:', error);
      });
    } else {
      get().pause();
    }
  },

  _pauseCurrentTrack: () => {
    const { playlist, currentTrackIndex } = get();
    if (currentTrackIndex < 0 || currentTrackIndex >= playlist.length) return;

    const audioElement = get()._getAudioElement();

    if (audioElement) {
      audioElement.pause();
    }
  },

  onTrackEnded: () => {
    const { isPlaying } = get();
    if (isPlaying) {
      get().next();
    }
  },

  lowerPlaybackSpeed: () => {
    get().setPlaybackSpeed(Math.max(0.25, get().playbackSpeed - 0.25));
  },

  raisePlaybackSpeed: () => {
    get().setPlaybackSpeed(Math.min(4, get().playbackSpeed + 0.25));
  },

  setPlaybackSpeed: (speed: number) => {
    set({ playbackSpeed: speed });
    if (get().isPlaying) {
      get()._playCurrentTrack();
    }
  },

  _getAudioElement: () => {
    const { playlist, currentTrackIndex, audioRefs } = get();
    const track = playlist[currentTrackIndex];
    const trackKey = generateTrackKey(track.rowIndex, track.cellIndex);
    const audioElement = audioRefs.get(trackKey);
    return audioElement;
  },

  _getCurrentPlaybackTrack: () => {
    const { playlist, currentTrackIndex } = get();
    return playlist[currentTrackIndex];
  },
}));

export { generateTrackKey };

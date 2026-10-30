export const ASSISTANT_SPEECH_START_LEVEL = 0.035;
export const ASSISTANT_SPEECH_RELEASE_LEVEL = 0.018;
export const ASSISTANT_SPEECH_RELEASE_MS = 500;

type AudioLevelAnalyser = Pick<
  AnalyserNode,
  "getByteFrequencyData" | "getByteTimeDomainData"
>;

/**
 * Measures both spectral energy and time-domain RMS. Some browsers and voices
 * produce sparse frequency bins, while RMS remains representative of audible
 * playback, so the larger normalized signal is used for visualization/state.
 */
export function measureAudioLevel(
  analyser: AudioLevelAnalyser,
  frequencyData: Uint8Array<ArrayBuffer>,
  timeDomainData: Uint8Array<ArrayBuffer>,
): number {
  analyser.getByteFrequencyData(frequencyData);
  analyser.getByteTimeDomainData(timeDomainData);

  let frequencySum = 0;
  for (let index = 0; index < frequencyData.length; index += 1) {
    frequencySum += frequencyData[index];
  }
  const frequencyLevel = frequencySum / frequencyData.length / 100;

  let squareSum = 0;
  for (let index = 0; index < timeDomainData.length; index += 1) {
    const centeredSample = (timeDomainData[index] - 128) / 128;
    squareSum += centeredSample * centeredSample;
  }
  const rmsLevel = Math.sqrt(squareSum / timeDomainData.length) * 3.2;

  return Math.min(1, Math.max(frequencyLevel, rmsLevel));
}

/** Holds speech active through short pauses so the mascot does not flicker. */
export class AssistantSpeechGate {
  private active = false;
  private lastActiveAt = 0;

  isActive(): boolean {
    return this.active;
  }

  update(level: number, now: number): boolean {
    if (level >= ASSISTANT_SPEECH_START_LEVEL) {
      this.active = true;
      this.lastActiveAt = now;
    } else if (
      this.active &&
      level <= ASSISTANT_SPEECH_RELEASE_LEVEL &&
      now - this.lastActiveAt >= ASSISTANT_SPEECH_RELEASE_MS
    ) {
      this.active = false;
    }

    return this.active;
  }

  reset(): void {
    this.active = false;
    this.lastActiveAt = 0;
  }
}

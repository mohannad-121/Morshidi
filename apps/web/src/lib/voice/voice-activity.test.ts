import { describe, expect, it } from "vitest";
import {
  ASSISTANT_SPEECH_RELEASE_MS,
  AssistantSpeechGate,
  measureAudioLevel,
} from "./voice-activity";

describe("assistant voice activity", () => {
  it("uses time-domain RMS when frequency bins under-report audible playback", () => {
    const analyser = {
      getByteFrequencyData: (data: Uint8Array) => data.fill(0),
      getByteTimeDomainData: (data: Uint8Array) => {
        data.forEach((_, index) => {
          data[index] = index % 2 === 0 ? 136 : 120;
        });
      },
    };

    const level = measureAudioLevel(
      analyser,
      new Uint8Array(128),
      new Uint8Array(128),
    );

    expect(level).toBeGreaterThan(0.035);
  });

  it("holds assistant speech through brief pauses and releases after hysteresis", () => {
    const gate = new AssistantSpeechGate();

    expect(gate.update(0.06, 1_000)).toBe(true);
    expect(gate.update(0.01, 1_000 + ASSISTANT_SPEECH_RELEASE_MS - 1)).toBe(true);
    expect(gate.update(0.01, 1_000 + ASSISTANT_SPEECH_RELEASE_MS)).toBe(false);
  });

  it("does not activate on sub-threshold analyser noise", () => {
    const gate = new AssistantSpeechGate();
    expect(gate.update(0.02, 1_000)).toBe(false);
    expect(gate.update(0.034, 2_000)).toBe(false);
  });
});

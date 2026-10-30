import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ComponentProps } from "react";
import {
  AnimatedMorshidiMascot,
  getMascotMouthState,
} from "./AnimatedMorshidiMascot";

vi.mock("next/image", () => ({
  __esModule: true,
  default: ({ unoptimized: _unoptimized, ...props }: ComponentProps<"img"> & { unoptimized?: boolean }) => (
    <img {...props} />
  ),
}));

afterEach(cleanup);

describe("AnimatedMorshidiMascot", () => {
  it("maps only eligible remote assistant energy to closed, half, and open mouth states", () => {
    expect(getMascotMouthState(0, true)).toBe("closed");
    expect(getMascotMouthState(0.034, true)).toBe("closed");
    expect(getMascotMouthState(0.08, true)).toBe("half");
    expect(getMascotMouthState(0.14, true)).toBe("open");
    expect(getMascotMouthState(0.8, false)).toBe("closed");
  });

  it("renders the source-faithful layered rig with a stationary body", () => {
    const { container } = render(<AnimatedMorshidiMascot status="idle" />);
    const sources = Array.from(container.querySelectorAll("img")).map((image) =>
      image.getAttribute("src"),
    );

    expect(sources).toEqual(
      expect.arrayContaining([
        "/brand/mascot/morshidi-mascot.png",
        "/brand/mascot/rig/mouth-closed.svg",
        "/brand/mascot/rig/mouth-half.svg",
        "/brand/mascot/rig/mouth-open.svg",
      ]),
    );
    expect(screen.getByTestId("mascot-body-base").classList.contains("animate-mascot-breathe")).toBe(false);
    expect(screen.getByTestId("animated-morshidi-mascot").getAttribute("data-motion")).toBe(
      "still-body",
    );
  });

  it("opens and closes the mouth with assistant audio without transforming the torso", () => {
    const { rerender } = render(
      <AnimatedMorshidiMascot status="listening" assistantAudioLevel={0} />,
    );
    const mascot = screen.getByTestId("animated-morshidi-mascot");
    const body = screen.getByTestId("mascot-body-base");

    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");
    expect(body.className).toContain("mascot-rig-body");

    rerender(<AnimatedMorshidiMascot status="listening" assistantAudioLevel={0.08} />);
    expect(mascot.getAttribute("data-mouth-state")).toBe("half");

    rerender(<AnimatedMorshidiMascot status="speaking" assistantAudioLevel={0.3} />);
    expect(mascot.getAttribute("data-mouth-state")).toBe("open");
    expect(mascot.getAttribute("data-motion")).toBe("mouth-and-hands");

    rerender(<AnimatedMorshidiMascot status="listening" assistantAudioLevel={0} />);
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");
  });

  it("does not let student microphone energy trigger mouth or arm speech motion", () => {
    render(
      <AnimatedMorshidiMascot
        status="listening"
        micAudioLevel={0.9}
        assistantAudioLevel={0}
      />,
    );

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-speaking")).toBe("false");
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");
    expect(screen.getByTestId("mascot-arm-left").getAttribute("data-speaking")).toBe("false");
    expect(screen.getByTestId("mascot-arm-right").getAttribute("data-speaking")).toBe("false");
  });

  it("keeps delegation closed and still even if an audio level is supplied", () => {
    render(<AnimatedMorshidiMascot status="delegating" assistantAudioLevel={0.3} />);

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-speaking")).toBe("false");
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");
  });

  it("supports deterministic left and right gesture verification without moving the body", () => {
    const { rerender } = render(
      <AnimatedMorshidiMascot
        status="speaking"
        assistantAudioLevel={0.2}
        gestureOverride="left"
      />,
    );

    expect(screen.getByTestId("mascot-arm-left").getAttribute("data-gesture")).toBe("left");
    expect(screen.getByTestId("mascot-body-base").className).toContain("mascot-rig-body");

    rerender(
      <AnimatedMorshidiMascot
        status="speaking"
        assistantAudioLevel={0.2}
        gestureOverride="right"
      />,
    );
    expect(screen.getByTestId("mascot-arm-right").getAttribute("data-gesture")).toBe("right");
  });

  it("retains the state-aware aura independently from rig transforms", () => {
    const { container } = render(
      <AnimatedMorshidiMascot status="speaking" assistantAudioLevel={0.3} />,
    );
    const aura = container.querySelector(".blur-2xl") as HTMLElement;

    expect(aura.style.backgroundColor).toContain("255, 194, 26");
    expect(aura.style.transform).toBe("scale(1.135)");
  });
});

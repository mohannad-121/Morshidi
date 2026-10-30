import { render, screen, cleanup } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import { AnimatedMorshidiMascot } from "./AnimatedMorshidiMascot";

vi.mock("next/image", () => ({
  __esModule: true,
  default: (props: any) => <img {...props} />,
}));

afterEach(() => {
  cleanup();
});

describe("AnimatedMorshidiMascot", () => {
  it("renders accessible container with Arabic aria-label and status attributes", () => {
    render(<AnimatedMorshidiMascot status="idle" />);

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot).toBeDefined();
    expect(mascot.getAttribute("role")).toBe("img");
    expect(mascot.getAttribute("aria-label")).toContain("مرشدي");
    expect(mascot.getAttribute("data-status")).toBe("idle");
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");
  });

  it("renders all 5 official character layers from /brand/mascot/ with correct stacking order", () => {
    const { container } = render(<AnimatedMorshidiMascot status="listening" />);

    const images = Array.from(container.querySelectorAll("img"));
    const imageSources = images.map((img) => img.getAttribute("src"));

    expect(imageSources).toContain("/brand/mascot/torso-closed.png");
    expect(imageSources).toContain("/brand/mascot/torso-half.png");
    expect(imageSources).toContain("/brand/mascot/torso-open.png");
    expect(imageSources).toContain("/brand/mascot/arm-left.png");
    expect(imageSources).toContain("/brand/mascot/arm-right.png");
    expect(images.length).toBe(5);

    // Verify arms are placed after torso layers in DOM order so moving arms are never occluded by torso
    const torsoIndex = images.findIndex((img) => img.getAttribute("src")?.includes("torso"));
    const armLeftIndex = images.findIndex((img) => img.getAttribute("src")?.includes("arm-left"));
    const armRightIndex = images.findIndex((img) => img.getAttribute("src")?.includes("arm-right"));

    expect(armLeftIndex).toBeGreaterThan(torsoIndex);
    expect(armRightIndex).toBeGreaterThan(torsoIndex);
  });

  it("keeps mouth strictly closed when only student microphone is active", () => {
    render(
      <AnimatedMorshidiMascot
        status="listening"
        micAudioLevel={0.85}
        assistantAudioLevel={0.0}
      />
    );

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");

    const closed = screen.getByTestId("torso-closed");
    const half = screen.getByTestId("torso-half");
    const open = screen.getByTestId("torso-open");

    expect(closed.style.opacity).toBe("1");
    expect(half.style.opacity).toBe("0");
    expect(open.style.opacity).toBe("0");
  });

  it("reacts directly to remote assistant audio energy even if status is still listening (audio-driven speaking)", () => {
    render(
      <AnimatedMorshidiMascot
        status="listening"
        assistantAudioLevel={0.22}
      />
    );

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-speaking")).toBe("true");
    expect(mascot.getAttribute("data-mouth-state")).toBe("open");

    const open = screen.getByTestId("torso-open");
    expect(open.style.opacity).toBe("1");
  });

  it("transitions mouth: closed -> half -> open -> closed across speech intensity cycle", () => {
    const { rerender } = render(
      <AnimatedMorshidiMascot status="speaking" assistantAudioLevel={0.0} />
    );

    // Initial silent speaking state
    let mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");

    // Moderate audio: half mouth
    rerender(<AnimatedMorshidiMascot status="speaking" assistantAudioLevel={0.08} />);
    mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-mouth-state")).toBe("half");

    // Peak audio: full open mouth
    rerender(<AnimatedMorshidiMascot status="speaking" assistantAudioLevel={0.25} />);
    mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-mouth-state")).toBe("open");

    // Speech completed: closed mouth
    rerender(<AnimatedMorshidiMascot status="listening" assistantAudioLevel={0.0} />);
    mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");
  });

  it("activates explanatory hand gestures during speech and terminates gestures after speech", () => {
    const { rerender } = render(<AnimatedMorshidiMascot status="listening" assistantAudioLevel={0} />);

    const armLeft = screen.getByTestId("arm-left-container");
    const armRight = screen.getByTestId("arm-right-container");

    expect(armLeft.classList.contains("animate-mascot-gesture-left")).toBe(false);
    expect(armRight.classList.contains("animate-mascot-gesture-right")).toBe(false);

    // Assistant speaks
    rerender(<AnimatedMorshidiMascot status="speaking" assistantAudioLevel={0.15} />);
    expect(armLeft.classList.contains("animate-mascot-gesture-left")).toBe(true);
    expect(armRight.classList.contains("animate-mascot-gesture-right")).toBe(true);

    // Assistant stops speaking
    rerender(<AnimatedMorshidiMascot status="listening" assistantAudioLevel={0} />);
    expect(armLeft.classList.contains("animate-mascot-gesture-left")).toBe(false);
    expect(armRight.classList.contains("animate-mascot-gesture-right")).toBe(false);
  });

  it("keeps mouth closed during academic delegation state", () => {
    render(
      <AnimatedMorshidiMascot
        status="delegating"
        assistantAudioLevel={0.1}
      />
    );

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");
    expect(mascot.getAttribute("data-speaking")).toBe("false");
  });
});

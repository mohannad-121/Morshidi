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
  it("renders accessible container with Arabic aria-label", () => {
    render(<AnimatedMorshidiMascot status="idle" />);

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot).toBeDefined();
    expect(mascot.getAttribute("role")).toBe("img");
    expect(mascot.getAttribute("aria-label")).toContain("مرشدي");
    expect(mascot.getAttribute("data-status")).toBe("idle");
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");
  });

  it("renders all 5 official character layers from /brand/mascot/", () => {
    const { container } = render(<AnimatedMorshidiMascot status="listening" />);

    const images = Array.from(container.querySelectorAll("img"));
    const imageSources = images.map((img) => img.getAttribute("src"));

    expect(imageSources).toContain("/brand/mascot/arm-left.png");
    expect(imageSources).toContain("/brand/mascot/torso-closed.png");
    expect(imageSources).toContain("/brand/mascot/torso-half.png");
    expect(imageSources).toContain("/brand/mascot/torso-open.png");
    expect(imageSources).toContain("/brand/mascot/arm-right.png");
    expect(images.length).toBe(5);
  });

  it("keeps mouth closed during listening state even if background noise exists", () => {
    render(
      <AnimatedMorshidiMascot
        status="listening"
        assistantAudioLevel={0.45}
        micAudioLevel={0.8}
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

  it("synchronizes mouth to half-open on moderate assistant speech audio", () => {
    render(
      <AnimatedMorshidiMascot
        status="speaking"
        assistantAudioLevel={0.12}
      />
    );

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-mouth-state")).toBe("half");

    const closed = screen.getByTestId("torso-closed");
    const half = screen.getByTestId("torso-half");
    const open = screen.getByTestId("torso-open");

    expect(closed.style.opacity).toBe("0");
    expect(half.style.opacity).toBe("1");
    expect(open.style.opacity).toBe("0");
  });

  it("synchronizes mouth to full-open on peak assistant speech audio", () => {
    render(
      <AnimatedMorshidiMascot
        status="speaking"
        assistantAudioLevel={0.35}
      />
    );

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-mouth-state")).toBe("open");

    const closed = screen.getByTestId("torso-closed");
    const half = screen.getByTestId("torso-half");
    const open = screen.getByTestId("torso-open");

    expect(closed.style.opacity).toBe("0");
    expect(half.style.opacity).toBe("0");
    expect(open.style.opacity).toBe("1");
  });

  it("activates explanatory hand gestures only when speaking", () => {
    const { rerender } = render(<AnimatedMorshidiMascot status="listening" />);

    const armLeft = screen.getByTestId("arm-left-container");
    const armRight = screen.getByTestId("arm-right-container");

    expect(armLeft.classList.contains("animate-mascot-gesture-left")).toBe(false);
    expect(armRight.classList.contains("animate-mascot-gesture-right")).toBe(false);

    rerender(<AnimatedMorshidiMascot status="speaking" assistantAudioLevel={0.2} />);

    expect(armLeft.classList.contains("animate-mascot-gesture-left")).toBe(true);
    expect(armRight.classList.contains("animate-mascot-gesture-right")).toBe(true);
  });
});

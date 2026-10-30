import { render, screen, cleanup } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import type { ComponentProps } from "react";
import { AnimatedMorshidiMascot } from "./AnimatedMorshidiMascot";

vi.mock("next/image", () => ({
  __esModule: true,
  default: (props: ComponentProps<"img">) => <img {...props} />,
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
    expect(mascot.getAttribute("data-motion")).toBe("breathing");
    expect(mascot.getAttribute("data-mouth-state")).toBe("closed");
  });

  it("renders pristine official character artwork from /brand/mascot/morshidi-mascot.png as a unified silhouette", () => {
    const { container } = render(<AnimatedMorshidiMascot status="listening" />);

    const images = Array.from(container.querySelectorAll("img"));
    const imageSources = images.map((img) => img.getAttribute("src"));

    expect(imageSources).toContain("/brand/mascot/morshidi-mascot.png");
    // Seamless single character silhouette with zero facial distortion and zero detached limbs
    expect(screen.getByTestId("morshidi-mascot-unified")).toBeDefined();
  });

  it("switches from idle breathing to speaking cadence when assistant speaks", () => {
    const { rerender } = render(
      <AnimatedMorshidiMascot status="listening" assistantAudioLevel={0.0} />
    );

    const bodyContainer = screen.getByTestId("mascot-body-container");
    expect(bodyContainer.classList.contains("animate-mascot-breathe")).toBe(true);
    expect(bodyContainer.classList.contains("animate-mascot-speaking")).toBe(false);

    // Assistant starts speaking
    rerender(<AnimatedMorshidiMascot status="speaking" assistantAudioLevel={0.15} />);
    expect(bodyContainer.classList.contains("animate-mascot-speaking")).toBe(true);
    expect(bodyContainer.classList.contains("animate-mascot-breathe")).toBe(false);
    expect(screen.getByTestId("animated-morshidi-mascot").getAttribute("data-motion")).toBe("speaking");

    // Assistant returns to listening
    rerender(<AnimatedMorshidiMascot status="listening" assistantAudioLevel={0.0} />);
    expect(bodyContainer.classList.contains("animate-mascot-breathe")).toBe(true);
    expect(bodyContainer.classList.contains("animate-mascot-speaking")).toBe(false);
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

    const bodyContainer = screen.getByTestId("mascot-body-container");
    expect(bodyContainer.classList.contains("animate-mascot-speaking")).toBe(true);
  });

  it("isolates student microphone so student voice does not trigger speaking animation", () => {
    render(
      <AnimatedMorshidiMascot
        status="listening"
        micAudioLevel={0.85}
        assistantAudioLevel={0.0}
      />
    );

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-speaking")).toBe("false");

    const bodyContainer = screen.getByTestId("mascot-body-container");
    expect(bodyContainer.classList.contains("animate-mascot-breathe")).toBe(true);
    expect(bodyContainer.classList.contains("animate-mascot-speaking")).toBe(false);
  });

  it("keeps mascot attentive and not speaking during academic delegation", () => {
    render(
      <AnimatedMorshidiMascot
        status="delegating"
        assistantAudioLevel={0.1}
      />
    );

    const mascot = screen.getByTestId("animated-morshidi-mascot");
    expect(mascot.getAttribute("data-speaking")).toBe("false");

    const bodyContainer = screen.getByTestId("mascot-body-container");
    expect(bodyContainer.classList.contains("animate-mascot-breathe")).toBe(true);
  });

  it("renders dynamic atmospheric aura that scales with audio activity", () => {
    const { container } = render(
      <AnimatedMorshidiMascot
        status="speaking"
        assistantAudioLevel={0.3}
      />
    );

    const aura = container.querySelector(".filter.blur-2xl");
    expect(aura).toBeDefined();
    expect((aura as HTMLElement)?.style.backgroundColor).toContain("rgba(255, 194, 26");
  });
});

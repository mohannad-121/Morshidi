import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Emoji, emojiToUnified, renderEmoji } from "./Emoji";

describe("Emoji", () => {
  it("normalizes variation selectors and ZWJ sequences to Apple asset filenames", () => {
    expect(emojiToUnified("🗓️")).toBe("1f5d3-fe0f");
    expect(emojiToUnified("🗓")).toBe("1f5d3-fe0f");
    expect(emojiToUnified("🧑‍🎓")).toBe("1f9d1-200d-1f393");

    const { container } = render(<>{renderEmoji("مرشدي 🧑‍🎓", { decorative: true })}</>);
    const image = container.querySelector("img");
    expect(image?.getAttribute("src")).toBe("/emoji/1f9d1-200d-1f393.png");
    expect(image?.getAttribute("aria-hidden")).toBe("true");
  });

  it("falls back to the native character when an image cannot load", () => {
    render(<Emoji emoji="🫠" />);
    fireEvent.error(screen.getByRole("img", { name: "🫠" }));
    expect(screen.queryByRole("img", { name: "🫠" })).toBeNull();
    expect(screen.getByText("🫠")).toBeDefined();
  });
});

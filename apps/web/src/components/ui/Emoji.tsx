"use client";

import { Fragment, useState, type ReactNode } from "react";

const segmenter = new Intl.Segmenter(undefined, { granularity: "grapheme" });
const emojiGrapheme = /\p{Extended_Pictographic}|\p{Emoji_Presentation}|\ufe0f|\u200d|\u20e3/u;
const textSymbols = new Set(["©", "®", "™", "↖", "↗"]);
const qualifiedAliases = new Map([
  ["1f3db", "1f3db-fe0f"],
  ["1f5d3", "1f5d3-fe0f"],
  ["1f5fa", "1f5fa-fe0f"],
]);

export function emojiToUnified(value: string): string {
  const unified = [...value.normalize("NFC")]
    .filter((character) => character.codePointAt(0) !== 0xfe0e)
    .map((character) => character.codePointAt(0)?.toString(16).toLowerCase().padStart(4, "0"))
    .join("-");
  return qualifiedAliases.get(unified) ?? unified;
}

type EmojiProps = {
  emoji: string;
  decorative?: boolean;
  className?: string;
};

export function Emoji({ emoji, decorative = false, className = "" }: EmojiProps) {
  const [failedEmoji, setFailedEmoji] = useState<string | null>(null);
  const failed = failedEmoji === emoji;

  if (failed) {
    return decorative ? <span aria-hidden="true">{emoji}</span> : <>{emoji}</>;
  }

  return (
    // The product explicitly uses local Apple emoji PNGs instead of optimized content images.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`/emoji/${emojiToUnified(emoji)}.png`}
      alt={emoji}
      aria-hidden={decorative || undefined}
      width="1.1em"
      height="1.1em"
      className={`emoji-image inline-block shrink-0 object-contain ${className}`.trim()}
      style={{ width: "1.1em", height: "1.1em", verticalAlign: "-0.15em" }}
      draggable={false}
      loading="lazy"
      onError={() => setFailedEmoji(emoji)}
    />
  );
}

export function renderEmoji(text: string, options: { decorative?: boolean } = {}): ReactNode[] {
  return [...segmenter.segment(text)].map(({ segment, index }) =>
    emojiGrapheme.test(segment) && !textSymbols.has(segment) ? (
      <Emoji key={`${index}-${emojiToUnified(segment)}`} emoji={segment} decorative={options.decorative} />
    ) : (
      <Fragment key={index}>{segment}</Fragment>
    ),
  );
}

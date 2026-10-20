import { cp, mkdir, readdir, readFile, rm, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const packageRoot = path.join(webRoot, "node_modules", "emoji-datasource-apple");
const sourceImageRoot = path.join(packageRoot, "img", "apple", "64");
const destinationRoot = path.join(webRoot, "public", "emoji");
const scanTargets = [
  path.join(webRoot, "src", "app", "(student)"),
  path.join(webRoot, "src", "components", "navigation", "AppShell.tsx"),
  path.join(webRoot, "src", "components", "ui"),
];

const segmenter = new Intl.Segmenter(undefined, { granularity: "grapheme" });
const emojiPresentation = /\p{Extended_Pictographic}|\p{Emoji_Presentation}|\ufe0f|\u200d|\u20e3/u;
const textSymbols = new Set(["©", "®", "™", "↖", "↗"]);

function toUnified(value) {
  return [...value]
    .map((character) => character.codePointAt(0).toString(16).toUpperCase().padStart(4, "0"))
    .join("-");
}

async function collectSourceFiles(target) {
  const stats = await stat(target);
  if (stats.isFile()) return target.endsWith(".tsx") && !target.endsWith(".test.tsx") ? [target] : [];

  const files = [];
  for (const entry of await readdir(target, { withFileTypes: true })) {
    const absolutePath = path.join(target, entry.name);
    if (entry.isDirectory()) files.push(...await collectSourceFiles(absolutePath));
    if (entry.isFile() && entry.name.endsWith(".tsx") && !entry.name.endsWith(".test.tsx")) files.push(absolutePath);
  }
  return files;
}

const emojiData = JSON.parse(await readFile(path.join(packageRoot, "emoji.json"), "utf8"));
const entriesBySequence = new Map();

for (const entry of emojiData) {
  entriesBySequence.set(entry.unified.toUpperCase(), entry);
  if (entry.non_qualified) entriesBySequence.set(entry.non_qualified.toUpperCase(), entry);
  for (const variation of Object.keys(entry.skin_variations ?? {})) {
    entriesBySequence.set(variation.toUpperCase(), { ...entry, unified: variation });
  }
}

const sourceFiles = (await Promise.all(scanTargets.map(collectSourceFiles))).flat();
const usedEntries = new Map();
const unmatched = new Set();

for (const sourceFile of sourceFiles) {
  const source = await readFile(sourceFile, "utf8");
  for (const { segment } of segmenter.segment(source)) {
    if (!emojiPresentation.test(segment) || textSymbols.has(segment)) continue;
    const sequence = toUnified(segment);
    const entry = entriesBySequence.get(sequence);
    if (!entry) {
      unmatched.add(`${segment} (${sequence}) in ${path.relative(webRoot, sourceFile)}`);
      continue;
    }
    usedEntries.set(entry.unified.toLowerCase(), entry);
  }
}

if (unmatched.size > 0) {
  throw new Error(`Unmatched emoji-like graphemes:\n${[...unmatched].sort().join("\n")}`);
}

await mkdir(destinationRoot, { recursive: true });
const expectedFiles = new Set([...usedEntries.keys()].map((unified) => `${unified}.png`));

for (const filename of await readdir(destinationRoot)) {
  if (filename.endsWith(".png") && !expectedFiles.has(filename)) {
    await rm(path.join(destinationRoot, filename));
  }
}

for (const filename of [...expectedFiles].sort()) {
  await cp(path.join(sourceImageRoot, filename), path.join(destinationRoot, filename));
}

console.log(`Copied ${expectedFiles.size} Apple emoji PNGs to ${path.relative(webRoot, destinationRoot)}.`);

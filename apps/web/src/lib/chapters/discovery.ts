import fs from "node:fs";
import path from "node:path";

export type SupportedExtension = ".pdf" | ".ppt" | ".pptx" | ".doc" | ".docx";
export type ChapterFileType = "PDF" | "PowerPoint" | "Word";

export interface ChapterFile {
  filename: string;
  displayName: string;
  extension: SupportedExtension;
  fileType: ChapterFileType;
  downloadUrl: string;
}

export interface DiscoveredCourse {
  slug: string;
  name: string;
  files: ChapterFile[];
}

const SUPPORTED_EXTENSIONS: ReadonlySet<string> = new Set([
  ".pdf",
  ".ppt",
  ".pptx",
  ".doc",
  ".docx",
]);

const EXTENSION_TYPE_MAP: Record<SupportedExtension, ChapterFileType> = {
  ".pdf": "PDF",
  ".ppt": "PowerPoint",
  ".pptx": "PowerPoint",
  ".doc": "Word",
  ".docx": "Word",
};

/**
 * Resolves the absolute directory where chapter files reside.
 * Strictly constrained to apps/web/public/chapters or local public/chapters.
 */
export function resolveChaptersDir(overrideBaseDir?: string): string {
  if (overrideBaseDir) {
    return path.resolve(overrideBaseDir);
  }
  const inCwd = path.join(process.cwd(), "public", "chapters");
  if (fs.existsSync(inCwd)) {
    return inCwd;
  }
  const inAppsWeb = path.join(process.cwd(), "apps", "web", "public", "chapters");
  if (fs.existsSync(inAppsWeb)) {
    return inAppsWeb;
  }
  return inCwd;
}

/**
 * Validates that a folder or filename does not contain path traversal characters.
 */
export function isSafePathComponent(component: string): boolean {
  if (!component || typeof component !== "string") return false;
  if (component.includes("..") || component.includes("/") || component.includes("\\") || component.includes("\0")) {
    return false;
  }
  if (component.startsWith(".")) {
    return false;
  }
  return true;
}

/**
 * Determines whether a file is a temporary, hidden, or ignored file.
 */
export function isIgnoredFile(filename: string): boolean {
  if (!filename || filename.startsWith(".") || filename.startsWith("~$")) {
    return true;
  }
  const lower = filename.toLowerCase();
  if (lower === "course.json" || lower === "thumbs.db" || lower === ".ds_store") {
    return true;
  }
  if (lower.endsWith(".tmp") || lower.endsWith(".swp") || lower.endsWith(".bak")) {
    return true;
  }
  return false;
}

/**
 * Formats a raw filename into a user-friendly display name.
 * Examples:
 * - chapter-01.pdf => Chapter 01
 * - machine-learning-lecture-04.pdf => Lecture 04
 * - machine-learning-lecture-02-03.pdf => Lecture 02-03
 * - الفصل-01.pdf => الفصل 01
 */
export function formatChapterLabel(filename: string, courseSlug?: string): string {
  // 1. Remove file extension
  let name = filename.replace(/\.[^/.]+$/, "");

  // 2. Decode URI components if URL-encoded
  try {
    name = decodeURIComponent(name);
  } catch {
    // keep raw if decoding fails
  }

  // 3. Remove course slug prefix if present
  if (courseSlug) {
    const slugRegex = new RegExp(`^${courseSlug.replace(/[-_]+/g, "[-_\\s]+")}[-_\\s]+`, "i");
    name = name.replace(slugRegex, "");

    const normalizedSlug = courseSlug.replace(/[-_]+/g, " ").toLowerCase();
    if (name.toLowerCase().startsWith(normalizedSlug)) {
      name = name.slice(normalizedSlug.length);
    }
  }

  // 4. Strip leading/trailing separators
  name = name.replace(/^[-_\s]+/, "").replace(/[-_\s]+$/, "");

  // 5. Preserve hyphens between numbers (e.g. 02-03 or 1-2)
  name = name.replace(/(\d+)[-_](\d+)/g, "$1\uE000$2");

  // 6. Replace remaining hyphens and underscores with spaces
  name = name.replace(/[-_]+/g, " ");

  // 7. Restore hyphens between numbers
  name = name.replace(/\uE000/g, "-");

  // 8. Capitalize English words cleanly while preserving Arabic & symbols
  name = name
    .split(" ")
    .filter(Boolean)
    .map((word) => {
      if (word.includes("-")) {
        return word
          .split("-")
          .map((part) =>
            part.match(/^[a-z]/i)
              ? part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()
              : part
          )
          .join("-");
      }
      if (word.match(/^[a-z]/i)) {
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
      }
      return word;
    })
    .join(" ");

  return name.trim() || filename;
}

/**
 * Humanizes a folder slug into a readable title fallback.
 * e.g. "computer-programming-2" => "Computer Programming 2"
 */
export function humanizeFolderSlug(slug: string): string {
  return slug
    .replace(/[-_]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Safely discovers courses and their chapters from the filesystem.
 * Scans only the designated chapters directory and never exposes absolute server paths.
 */
export async function getDiscoveredCourses(overrideBaseDir?: string): Promise<DiscoveredCourse[]> {
  const baseDir = resolveChaptersDir(overrideBaseDir);

  if (!fs.existsSync(/*turbopackIgnore: true*/ baseDir)) {
    return [];
  }

  let entries: fs.Dirent[] = [];
  try {
    entries = await fs.promises.readdir(/*turbopackIgnore: true*/ baseDir, { withFileTypes: true });
  } catch {
    return [];
  }

  const courses: DiscoveredCourse[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const folderName = entry.name;

    if (!isSafePathComponent(folderName)) continue;

    const courseDir = path.join(/*turbopackIgnore: true*/ baseDir, folderName);

    // Read course.json safely
    let courseName = "";
    const courseJsonPath = path.join(courseDir, "course.json");
    if (fs.existsSync(/*turbopackIgnore: true*/ courseJsonPath)) {
      try {
        const raw = await fs.promises.readFile(/*turbopackIgnore: true*/ courseJsonPath, "utf-8");
        const parsed = JSON.parse(raw);
        if (typeof parsed?.name === "string" && parsed.name.trim()) {
          courseName = parsed.name.trim();
        }
      } catch {
        // Safe fallback if course.json is invalid JSON or unreadable
      }
    }

    if (!courseName) {
      courseName = humanizeFolderSlug(folderName);
    }

    // Discover chapter files
    let fileEntries: fs.Dirent[] = [];
    try {
      fileEntries = await fs.promises.readdir(/*turbopackIgnore: true*/ courseDir, { withFileTypes: true });
    } catch {
      fileEntries = [];
    }

    const files: ChapterFile[] = [];

    for (const fileEntry of fileEntries) {
      if (!fileEntry.isFile()) continue;
      const filename = fileEntry.name;

      if (!isSafePathComponent(filename) || isIgnoredFile(filename)) continue;

      const ext = path.extname(filename).toLowerCase();
      if (!SUPPORTED_EXTENSIONS.has(ext)) continue;

      const extension = ext as SupportedExtension;
      const fileType = EXTENSION_TYPE_MAP[extension];
      const displayName = formatChapterLabel(filename, folderName);

      // Safe public URL path for static Next.js public/ asset
      const downloadUrl = `/chapters/${encodeURIComponent(folderName)}/${encodeURIComponent(filename)}`;

      files.push({
        filename,
        displayName,
        extension,
        fileType,
        downloadUrl,
      });
    }

    // Sort files naturally (Chapter 01, Chapter 02, etc.)
    files.sort((a, b) =>
      a.displayName.localeCompare(b.displayName, undefined, { numeric: true, sensitivity: "base" })
    );

    courses.push({
      slug: folderName,
      name: courseName,
      files,
    });
  }

  // Sort courses by Arabic name
  courses.sort((a, b) => a.name.localeCompare(b.name, "ar", { sensitivity: "base" }));

  return courses;
}

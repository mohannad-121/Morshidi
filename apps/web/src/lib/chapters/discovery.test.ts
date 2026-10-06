import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  formatChapterLabel,
  getDiscoveredCourses,
  humanizeFolderSlug,
  isIgnoredFile,
  isSafePathComponent,
} from "./discovery";

describe("formatChapterLabel", () => {
  it("converts simple chapter filenames to clean labels", () => {
    expect(formatChapterLabel("chapter-01.pdf")).toBe("Chapter 01");
    expect(formatChapterLabel("chapter-02.pptx")).toBe("Chapter 02");
    expect(formatChapterLabel("chapter_03.docx")).toBe("Chapter 03");
  });

  it("strips course slug prefix and cleans lecture names", () => {
    expect(formatChapterLabel("machine-learning-lecture-04.pdf", "machine-learning")).toBe("Lecture 04");
    expect(formatChapterLabel("machine-learning-lecture-01.pdf", "machine-learning")).toBe("Lecture 01");
  });

  it("preserves number ranges such as lecture-02-03", () => {
    expect(formatChapterLabel("machine-learning-lecture-02-03.pdf", "machine-learning")).toBe("Lecture 02-03");
    expect(formatChapterLabel("chapter-04-05.pdf")).toBe("Chapter 04-05");
  });

  it("handles Arabic filenames and spaces cleanly without ugly text", () => {
    expect(formatChapterLabel("الفصل-الأول-مقدمة.pdf")).toBe("الفصل الأول مقدمة");
    expect(formatChapterLabel("ملخص_المادة_1.docx")).toBe("ملخص المادة 1");
    expect(formatChapterLabel("محاضرة 05.ppt")).toBe("محاضرة 05");
  });

  it("handles URL encoded characters safely", () => {
    expect(formatChapterLabel("Lecture%2001.pdf")).toBe("Lecture 01");
  });
});

describe("isSafePathComponent & isIgnoredFile", () => {
  it("rejects path traversal and unsafe path components", () => {
    expect(isSafePathComponent("..")).toBe(false);
    expect(isSafePathComponent("../etc/passwd")).toBe(false);
    expect(isSafePathComponent("..\\windows\\system32")).toBe(false);
    expect(isSafePathComponent(".hidden")).toBe(false);
    expect(isSafePathComponent("course/sub")).toBe(false);
    expect(isSafePathComponent("course\\sub")).toBe(false);
    expect(isSafePathComponent("normal-folder")).toBe(true);
  });

  it("identifies ignored and temporary files", () => {
    expect(isIgnoredFile("course.json")).toBe(true);
    expect(isIgnoredFile("COURSE.JSON")).toBe(true);
    expect(isIgnoredFile(".DS_Store")).toBe(true);
    expect(isIgnoredFile("Thumbs.db")).toBe(true);
    expect(isIgnoredFile("~$lecture-01.docx")).toBe(true);
    expect(isIgnoredFile("draft.tmp")).toBe(true);
    expect(isIgnoredFile("lecture-01.pdf")).toBe(false);
  });
});

describe("humanizeFolderSlug", () => {
  it("converts hyphenated and underscored slugs into capitalized words", () => {
    expect(humanizeFolderSlug("computer-programming-2")).toBe("Computer Programming 2");
    expect(humanizeFolderSlug("data_structures")).toBe("Data Structures");
  });
});

describe("getDiscoveredCourses against actual filesystem", () => {
  it("discovers existing course folders and files in public/chapters", async () => {
    const courses = await getDiscoveredCourses();
    expect(courses.length).toBeGreaterThanOrEqual(2);

    const ml = courses.find((c) => c.slug === "machine-learning");
    expect(ml).toBeDefined();
    expect(ml?.name).toBe("تعلم الآلة");
    expect(ml?.files.length).toBeGreaterThanOrEqual(5);

    const firstMlFile = ml?.files[0];
    expect(firstMlFile?.downloadUrl).toMatch(/^\/chapters\/machine-learning\/.*\.pdf$/);
    expect(firstMlFile?.fileType).toBe("PDF");

    const prog = courses.find((c) => c.slug === "computer-progarmming-2");
    expect(prog).toBeDefined();
    expect(prog?.name).toBe("برمجة الحاسوب 2");
    expect(prog?.files.length).toBeGreaterThanOrEqual(3);
    expect(prog?.files.some((f) => f.fileType === "PowerPoint")).toBe(true);
  });
});

describe("getDiscoveredCourses edge cases with isolated temp directory", () => {
  it("handles missing/invalid course.json and falls back safely to folder name", async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "morshidi-chapters-test-"));
    try {
      // Create course folder with corrupted course.json
      const course1Dir = path.join(tempDir, "intro-to-algorithms");
      fs.mkdirSync(course1Dir);
      fs.writeFileSync(path.join(course1Dir, "course.json"), "{ invalid json");
      fs.writeFileSync(path.join(course1Dir, "lecture-01.pdf"), "fake pdf content");

      // Create course folder with missing course.json
      const course2Dir = path.join(tempDir, "operating-systems");
      fs.mkdirSync(course2Dir);
      fs.writeFileSync(path.join(course2Dir, "chapter-01.pptx"), "fake pptx content");

      const courses = await getDiscoveredCourses(tempDir);
      expect(courses).toHaveLength(2);

      const alg = courses.find((c) => c.slug === "intro-to-algorithms");
      expect(alg?.name).toBe("Intro To Algorithms");
      expect(alg?.files).toHaveLength(1);
      expect(alg?.files[0].displayName).toBe("Lecture 01");
      expect(alg?.files[0].downloadUrl).toBe("/chapters/intro-to-algorithms/lecture-01.pdf");

      const osCourse = courses.find((c) => c.slug === "operating-systems");
      expect(osCourse?.name).toBe("Operating Systems");
      expect(osCourse?.files).toHaveLength(1);
      expect(osCourse?.files[0].fileType).toBe("PowerPoint");
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it("filters out unsupported files, temporary files, and course.json", async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "morshidi-chapters-filter-"));
    try {
      const courseDir = path.join(tempDir, "software-engineering");
      fs.mkdirSync(courseDir);
      fs.writeFileSync(path.join(courseDir, "course.json"), JSON.stringify({ name: "هندسة البرمجيات" }));
      fs.writeFileSync(path.join(courseDir, "lecture-01.pdf"), "pdf content");
      fs.writeFileSync(path.join(courseDir, "notes.txt"), "unsupported text file");
      fs.writeFileSync(path.join(courseDir, "archive.zip"), "unsupported zip file");
      fs.writeFileSync(path.join(courseDir, "image.png"), "unsupported png file");
      fs.writeFileSync(path.join(courseDir, ".DS_Store"), "hidden file");
      fs.writeFileSync(path.join(courseDir, "~$temp.docx"), "temporary docx file");
      fs.writeFileSync(path.join(courseDir, "draft.tmp"), "temporary file");

      const courses = await getDiscoveredCourses(tempDir);
      expect(courses).toHaveLength(1);
      expect(courses[0].files).toHaveLength(1);
      expect(courses[0].files[0].filename).toBe("lecture-01.pdf");
      expect(courses[0].files[0].displayName).toBe("Lecture 01");
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it("handles empty course folder safely", async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "morshidi-chapters-empty-"));
    try {
      const courseDir = path.join(tempDir, "empty-course");
      fs.mkdirSync(courseDir);
      fs.writeFileSync(path.join(courseDir, "course.json"), JSON.stringify({ name: "مادة فارغة" }));

      const courses = await getDiscoveredCourses(tempDir);
      expect(courses).toHaveLength(1);
      expect(courses[0].name).toBe("مادة فارغة");
      expect(courses[0].files).toHaveLength(0);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it("returns empty array if chapters directory does not exist", async () => {
    const nonExistent = path.join(os.tmpdir(), "non-existent-chapters-" + Date.now());
    const courses = await getDiscoveredCourses(nonExistent);
    expect(courses).toEqual([]);
  });
});

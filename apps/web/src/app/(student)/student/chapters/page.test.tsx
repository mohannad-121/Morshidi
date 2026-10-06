import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import ChaptersPage from "./page";
import { ChaptersClient } from "./ChaptersClient";
import type { DiscoveredCourse } from "@/lib/chapters/discovery";

const mockCourses: DiscoveredCourse[] = [
  {
    slug: "machine-learning",
    name: "تعلم الآلة",
    files: [
      {
        filename: "machine-learning-lecture-01.pdf",
        displayName: "Lecture 01",
        extension: ".pdf",
        fileType: "PDF",
        downloadUrl: "/chapters/machine-learning/machine-learning-lecture-01.pdf",
      },
      {
        filename: "machine-learning-lecture-02-03.pdf",
        displayName: "Lecture 02-03",
        extension: ".pdf",
        fileType: "PDF",
        downloadUrl: "/chapters/machine-learning/machine-learning-lecture-02-03.pdf",
      },
      {
        filename: "machine-learning-lecture-04.pptx",
        displayName: "Lecture 04",
        extension: ".pptx",
        fileType: "PowerPoint",
        downloadUrl: "/chapters/machine-learning/machine-learning-lecture-04.pptx",
      },
    ],
  },
  {
    slug: "computer-programming-2",
    name: "برمجة الحاسوب 2",
    files: [
      {
        filename: "chapter-01.pptx",
        displayName: "Chapter 01",
        extension: ".pptx",
        fileType: "PowerPoint",
        downloadUrl: "/chapters/computer-programming-2/chapter-01.pptx",
      },
    ],
  },
  {
    slug: "empty-course",
    name: "مادة خالية",
    files: [],
  },
];

describe("ChaptersPage (Server Component)", () => {
  it("renders page with automatically discovered courses from filesystem", async () => {
    const pageComponent = await ChaptersPage();
    render(pageComponent);

    expect(screen.getByRole("heading", { name: "شباتر المواد", level: 1 })).toBeDefined();
    expect(screen.getByText("تعلم الآلة")).toBeDefined();
    expect(screen.getByText("برمجة الحاسوب 2")).toBeDefined();
  });
});

describe("ChaptersClient Component", () => {
  it("renders courses without exposing course codes", () => {
    render(<ChaptersClient initialCourses={mockCourses} />);

    expect(screen.getByText("تعلم الآلة")).toBeDefined();
    expect(screen.getByText("برمجة الحاسوب 2")).toBeDefined();
    expect(screen.queryByText(/1501/)).toBeNull();
    expect(screen.queryByText(/CS\d+/)).toBeNull();
  });

  it("displays correct file counts for each course", () => {
    render(<ChaptersClient initialCourses={mockCourses} />);

    expect(screen.getByText("3 ملفات")).toBeDefined();
    expect(screen.getByText("ملف واحد")).toBeDefined();
    expect(screen.getByText("لا توجد ملفات")).toBeDefined();
  });

  it("opens modal on clicking 'عرض الشباتر' and displays clean file details and download links", async () => {
    const user = userEvent.setup();
    render(<ChaptersClient initialCourses={mockCourses} />);

    const mlButton = screen.getByRole("button", { name: "عرض الشباتر لمادة تعلم الآلة" });
    await user.click(mlButton);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeDefined();
    expect(dialog.getAttribute("aria-modal")).toBe("true");

    // Check clean labels
    expect(screen.getByText("Lecture 01")).toBeDefined();
    expect(screen.getByText("Lecture 02-03")).toBeDefined();
    expect(screen.getByText("Lecture 04")).toBeDefined();

    // Check file types
    expect(screen.getAllByText("PDF").length).toBe(2);
    expect(screen.getByText("PowerPoint")).toBeDefined();

    // Check download button href and download attribute
    const downloadLinks = screen.getAllByRole("link", { name: /^تحميل/ });
    expect(downloadLinks).toHaveLength(3);

    const firstLink = downloadLinks[0];
    expect(firstLink.getAttribute("href")).toBe(
      "/chapters/machine-learning/machine-learning-lecture-01.pdf"
    );
    expect(firstLink.getAttribute("download")).toBe("machine-learning-lecture-01.pdf");
    expect(firstLink.getAttribute("target")).toBeNull(); // direct download link, no popup or base64
  });

  it("closes modal on close button click and on Escape key press", async () => {
    const user = userEvent.setup();
    render(<ChaptersClient initialCourses={mockCourses} />);

    await user.click(screen.getByRole("button", { name: "عرض الشباتر لمادة برمجة الحاسوب 2" }));
    expect(screen.getByRole("dialog")).toBeDefined();

    // Close via close button
    const closeBtn = screen.getByRole("button", { name: "إغلاق تفاصيل المادة" });
    await user.click(closeBtn);
    expect(screen.queryByRole("dialog")).toBeNull();

    // Open again and close via Escape key
    await user.click(screen.getByRole("button", { name: "عرض الشباتر لمادة برمجة الحاسوب 2" }));
    expect(screen.getByRole("dialog")).toBeDefined();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
  });

  it("displays empty state when course has no files", async () => {
    const user = userEvent.setup();
    render(<ChaptersClient initialCourses={mockCourses} />);

    await user.click(screen.getByRole("button", { name: "عرض الشباتر لمادة مادة خالية" }));
    expect(screen.getByRole("dialog")).toBeDefined();
    expect(screen.getByText("لم تتم إضافة ملفات لهذه المادة بعد")).toBeDefined();
  });

  it("displays empty state when there are zero courses in system", () => {
    render(<ChaptersClient initialCourses={[]} />);
    expect(screen.getByText("لا توجد شباتر متاحة حالياً")).toBeDefined();
  });

  it("filters courses when searching", async () => {
    const user = userEvent.setup();
    render(<ChaptersClient initialCourses={mockCourses} />);

    const searchInput = screen.getByRole("searchbox", { name: "البحث عن مادة" });
    await user.type(searchInput, "برمجة");

    expect(screen.getByText("برمجة الحاسوب 2")).toBeDefined();
    expect(screen.queryByText("تعلم الآلة")).toBeNull();

    // Clear search
    await user.clear(searchInput);
    expect(screen.getByText("تعلم الآلة")).toBeDefined();
  });

  it("shows search empty state when no courses match", async () => {
    const user = userEvent.setup();
    render(<ChaptersClient initialCourses={mockCourses} />);

    const searchInput = screen.getByRole("searchbox", { name: "البحث عن مادة" });
    await user.type(searchInput, "غير موجود إطلاقاً");

    expect(screen.getByText("لا توجد مواد مطابقة لبحثك")).toBeDefined();
  });
});

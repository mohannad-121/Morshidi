import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChaptersClient } from "./ChaptersClient";
import type { LearningMaterialLibraryView } from "@/lib/api/learning-materials";

const request = vi.fn();
const authenticatedClient = { request };
vi.mock("@/lib/api/use-authenticated-api", () => ({
  useAuthenticatedApi: () => authenticatedClient,
}));

const library: LearningMaterialLibraryView = {
  coverage: "AUTHORIZED_ONLY",
  courses: [{
    course_id: "course-ml",
    course_code: "1505311",
    course_name_ar: "تعلم الآلة",
    course_name_en: "Machine Learning",
    materials: [{
      material_id: "material-1",
      title_ar: "المحاضرة 1",
      title_en: "Lecture 1",
      description_ar: null,
      description_en: null,
      material_type: "lecture",
      chapter_number: "1",
      display_order: 1,
      file_name: "lecture-01.pdf",
      mime_type: "application/pdf",
      byte_size: 100,
      version_label: "plan-12-v1",
      download_path: "/api/v1/me/learning-materials/material-1/download",
    }],
  }, {
    course_id: "course-programming",
    course_code: "1501112",
    course_name_ar: "برمجة الحاسوب (2)",
    course_name_en: null,
    materials: [{
      material_id: "material-2",
      title_ar: "الفصل 1",
      title_en: null,
      description_ar: null,
      description_en: null,
      material_type: "chapter",
      chapter_number: "1",
      display_order: 1,
      file_name: "chapter-01.pptx",
      mime_type: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      byte_size: 100,
      version_label: "plan-12-v1",
      download_path: "/api/v1/me/learning-materials/material-2/download",
    }],
  }],
};

describe("authorized chapters experience", () => {
  beforeEach(() => request.mockReset());

  it("renders only the supplied owner-authorized library with course names primary", () => {
    render(<ChaptersClient initialLibrary={library} />);
    expect(screen.getByText("تعلم الآلة")).toBeDefined();
    expect(screen.getByText("برمجة الحاسوب (2)")).toBeDefined();
    expect(screen.getByText("1505311")).toBeDefined();
    expect(screen.queryByText("تمريض صحة البالغين")).toBeNull();
  });

  it("shows the exact curriculum empty state for an authorized zero-chapter plan", () => {
    render(<ChaptersClient initialLibrary={{ coverage: "AUTHORIZED_ONLY", courses: [] }} />);
    expect(screen.getByText("لا تتوفر شبّاتِر لهذه الخطة الدراسية حالياً")).toBeDefined();
  });

  it("normalizes Arabic search and supports course-code search", async () => {
    const user = userEvent.setup();
    render(<ChaptersClient initialLibrary={library} />);
    const search = screen.getByRole("searchbox", { name: "البحث عن مادة" });
    await user.type(search, "تعلم الاله");
    expect(screen.getByText("تعلم الآلة")).toBeDefined();
    expect(screen.queryByText("برمجة الحاسوب (2)")).toBeNull();
    await user.clear(search);
    await user.type(search, "1501112");
    expect(screen.getByText("برمجة الحاسوب (2)")).toBeDefined();
  });

  it("opens an accessible dialog, moves focus to close, and closes on Escape", async () => {
    const user = userEvent.setup();
    render(<ChaptersClient initialLibrary={library} />);
    await user.click(screen.getAllByRole("button", { name: "عرض المواد" })[0]);
    expect(screen.getByRole("dialog").getAttribute("aria-modal")).toBe("true");
    expect(screen.getByRole("button", { name: "إغلاق" })).toBe(document.activeElement);
    expect(screen.getByText("المحاضرة 1")).toBeDefined();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("downloads only through the authenticated endpoint", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    request.mockResolvedValue(new Response(new Blob(["pdf"]), { status: 200 }));
    render(<ChaptersClient initialLibrary={library} />);
    await user.click(screen.getAllByRole("button", { name: "عرض المواد" })[0]);
    await user.click(screen.getByRole("button", { name: "تحميل المحاضرة 1" }));
    expect(request).toHaveBeenCalledWith(
      "/api/v1/me/learning-materials/material-1/download",
      { cache: "no-store" },
    );
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:test");
    createObjectURL.mockRestore(); revokeObjectURL.mockRestore(); click.mockRestore();
  });

  it("distinguishes provider failure from a verified empty library", async () => {
    request.mockResolvedValue(new Response(null, { status: 503 }));
    render(<ChaptersClient />);
    expect((await screen.findByRole("alert")).textContent).toContain("تعذّر تحميل المواد الآن");
    expect(screen.queryByText("لا تتوفر شبّاتِر لهذه الخطة الدراسية حالياً")).toBeNull();
  });
});

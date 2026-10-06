import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AcademicAnalysisProgress, ProgressStep } from "./AcademicAnalysisProgress";

describe("AcademicAnalysisProgress", () => {
  const sampleSteps: ProgressStep[] = [
    {
      id: "check_records",
      title: "التحقق من السجل الأكاديمي",
      description: "فحص الساعات المجتازة وحالة الطالب الحالية",
      status: "COMPLETE",
    },
    {
      id: "prerequisites",
      title: "فحص شروط المواد والمتطلبات",
      description: "التأكد من استيفاء المتطلبات السابقة لكل مادة",
      status: "ACTIVE",
    },
    {
      id: "optimization",
      title: "معالجة الخوارزمية الفصيلة",
      description: "توليد الحزم المتوازنة ومراعاة سقف الساعات",
      status: "WAITING",
    },
  ];

  it("renders with custom title, subtitle, and all steps", () => {
    render(
      <AcademicAnalysisProgress
        title="توليد الخطة الفصيلة"
        subtitle="جاري احتساب أفضل خيارات التسجيل"
        steps={sampleSteps}
      />
    );

    expect(screen.getByText("توليد الخطة الفصيلة")).toBeDefined();
    expect(screen.getByText("جاري احتساب أفضل خيارات التسجيل")).toBeDefined();
    expect(screen.getByText("التحقق من السجل الأكاديمي")).toBeDefined();
    expect(screen.getByText("فحص شروط المواد والمتطلبات")).toBeDefined();
    expect(screen.getByText("معالجة الخوارزمية الفصيلة")).toBeDefined();
  });

  it("calculates progress percentage correctly for completed steps", () => {
    render(<AcademicAnalysisProgress steps={sampleSteps} />);

    // 1 of 3 complete = 33%
    expect(screen.getByText("33%")).toBeDefined();
    const progressbar = screen.getByRole("progressbar");
    expect(progressbar.getAttribute("aria-valuenow")).toBe("33");
  });

  it("reflects distinct step status tags in Arabic", () => {
    render(<AcademicAnalysisProgress steps={sampleSteps} />);

    expect(screen.getByText("مكتمل")).toBeDefined();
    expect(screen.getByText("جاري المعالجة...")).toBeDefined();
    expect(screen.getByText("في الانتظار")).toBeDefined();
  });

  it("displays error status when a step fails", () => {
    const errorSteps: ProgressStep[] = [
      { id: "s1", title: "الخطوة الأولى", status: "COMPLETE" },
      { id: "s2", title: "الخطوة المتعثرة", status: "ERROR" },
      { id: "s3", title: "الخطوة اللاحقة", status: "WAITING" },
    ];

    render(<AcademicAnalysisProgress steps={errorSteps} />);

    expect(screen.getByText("تعثر التحليل")).toBeDefined();
    expect(screen.getByText("تعذر")).toBeDefined();
  });

  it("has accessible status and live region properties", () => {
    render(<AcademicAnalysisProgress steps={sampleSteps} />);

    const statusRegion = screen.getByRole("status");
    expect(statusRegion.getAttribute("aria-live")).toBe("polite");
    expect(statusRegion.getAttribute("dir")).toBe("rtl");
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CourseDifficulty } from "./CourseDifficulty";

const modeled = {
  course_code: "SYN101",
  general: { score: 68, level: "HARD", provenance: "MODEL_BASED", model_version: "GENERAL_DIFFICULTY_MODEL_V1" },
  personalized: { score: 55, level: "MODERATE", confidence: "LOW", provenance: "MODELED_STRUCTURAL_FALLBACK_NO_GRADE_MASTERY", model_version: "PERSONAL_DIFFICULTY_MODEL_V1", reason_codes: ["INSUFFICIENT_VERIFIED_GRADE_EVIDENCE"], contributing_skills: [], risk_factors: [] },
};

describe("modeled course difficulty", () => {
  it("shows five accessible difficulty dots and a subtle confidence hint", () => {
    const {container} = render(<CourseDifficulty course={modeled} />);
    expect(screen.getByRole('img', {name:'متوسطة'})).toBeTruthy();
    expect(container.querySelectorAll('.difficulty i')).toHaveLength(5);
    expect(container.querySelectorAll('.difficulty i.filled')).toHaveLength(3);
    expect(screen.getByTitle('تقدير أولي')).toBeTruthy();
    expect(container.textContent).not.toContain('MODEL');
  });

  it("shows English labels and an honest unavailable state", () => {
    const { rerender, container } = render(<CourseDifficulty course={modeled} locale="en" />);
    expect(screen.getByRole('img', {name:'Moderate'})).toBeTruthy();
    expect(screen.getByTitle('Initial estimate')).toBeTruthy();
    rerender(<CourseDifficulty course={undefined} locale="en" />);
    expect(container.childElementCount).toBe(0);
  });
});

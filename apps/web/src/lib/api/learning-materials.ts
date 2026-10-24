import type { AuthenticatedApiClient } from "./authenticated-client";

export interface LearningMaterialView {
  material_id: string;
  title_ar: string;
  title_en: string | null;
  description_ar: string | null;
  description_en: string | null;
  material_type: "chapter" | "lecture" | "worksheet" | "reference";
  chapter_number: string | null;
  display_order: number;
  file_name: string;
  mime_type: string;
  byte_size: number;
  version_label: string;
  download_path: `/api/v1/me/learning-materials/${string}/download`;
}

export interface LearningMaterialCourseView {
  course_id: string;
  course_code: string;
  course_name_ar: string | null;
  course_name_en: string | null;
  materials: LearningMaterialView[];
}

export interface LearningMaterialLibraryView {
  courses: LearningMaterialCourseView[];
  coverage: "AUTHORIZED_ONLY";
}

export class LearningMaterialsApi {
  constructor(private readonly client: AuthenticatedApiClient) {}

  async list(): Promise<LearningMaterialLibraryView> {
    const response = await this.client.request("/api/v1/me/learning-materials", {
      cache: "no-store",
    });
    if (!response.ok) throw new Error(`HTTP_${response.status}`);
    const body = (await response.json()) as LearningMaterialLibraryView;
    if (!body || body.coverage !== "AUTHORIZED_ONLY" || !Array.isArray(body.courses)) {
      throw new Error("INVALID_LEARNING_MATERIAL_LIBRARY");
    }
    return body;
  }

  async download(material: LearningMaterialView): Promise<void> {
    const response = await this.client.request(material.download_path, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP_${response.status}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    try {
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = material.file_name;
      anchor.rel = "noopener";
      anchor.click();
    } finally {
      URL.revokeObjectURL(url);
    }
  }
}

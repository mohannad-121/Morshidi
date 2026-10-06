import { describe, expect, it, vi } from "vitest";

import {
  downloadProfileAvatar,
  PROFILE_AVATAR_BUCKET,
  profileAvatarPath,
  uploadProfileAvatar,
  validateProfileAvatar,
  type ProfileAvatarStoragePort,
} from "@/lib/profile-avatar-storage";

function storagePort(overrides?: {
  download?: ReturnType<typeof vi.fn>;
  upload?: ReturnType<typeof vi.fn>;
}) {
  const download = overrides?.download ?? vi.fn().mockResolvedValue({ data: null, error: null });
  const upload = overrides?.upload ?? vi.fn().mockResolvedValue({ data: { path: "user-1/avatar" }, error: null });
  const from = vi.fn(() => ({ download, upload }));
  return { port: { from } as ProfileAvatarStoragePort, from, download, upload };
}

describe("profile avatar storage", () => {
  it("uses a deterministic owner folder and private avatar object name", () => {
    expect(profileAvatarPath("user-1")).toBe("user-1/avatar");
  });

  it("downloads the authenticated user's avatar from the configured bucket", async () => {
    const blob = new Blob(["image"], { type: "image/png" });
    const mock = storagePort({
      download: vi.fn().mockResolvedValue({ data: blob, error: null }),
    });

    await expect(downloadProfileAvatar("user-1", mock.port)).resolves.toBe(blob);
    expect(mock.from).toHaveBeenCalledWith(PROFILE_AVATAR_BUCKET);
    expect(mock.download).toHaveBeenCalledWith("user-1/avatar");
  });

  it("treats a missing avatar as an empty state", async () => {
    const mock = storagePort({
      download: vi.fn().mockResolvedValue({
        data: null,
        error: { message: "Object not found", statusCode: 404 },
      }),
    });

    await expect(downloadProfileAvatar("user-1", mock.port)).resolves.toBeNull();
  });

  it("uploads with owner-scoped path, content type, and replacement enabled", async () => {
    const mock = storagePort();
    const file = new File(["image"], "avatar.png", { type: "image/png" });

    await uploadProfileAvatar("user-1", file, mock.port);

    expect(mock.upload).toHaveBeenCalledWith("user-1/avatar", file, {
      cacheControl: "3600",
      contentType: "image/png",
      upsert: true,
    });
  });

  it("rejects unsupported formats and images larger than 5 MB", () => {
    expect(validateProfileAvatar(new File(["text"], "avatar.svg", { type: "image/svg+xml" }))).toContain("JPG");
    expect(validateProfileAvatar(new File([new Uint8Array(5 * 1024 * 1024 + 1)], "avatar.png", { type: "image/png" }))).toContain("5");
  });
});

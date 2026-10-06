import { createClient } from "@/lib/supabase/client";

export const PROFILE_AVATAR_BUCKET = "student-avatars";
export const PROFILE_AVATAR_MAX_BYTES = 5 * 1024 * 1024;
export const PROFILE_AVATAR_MIME_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
  "image/avif",
] as const;

type StorageErrorLike = {
  message: string;
  statusCode?: string | number;
};

type AvatarBucketPort = {
  download(path: string): Promise<{ data: Blob | null; error: StorageErrorLike | null }>;
  upload(
    path: string,
    file: File,
    options: { cacheControl: string; contentType: string; upsert: boolean },
  ): Promise<{ data: { path: string } | null; error: StorageErrorLike | null }>;
};

export type ProfileAvatarStoragePort = {
  from(bucket: string): AvatarBucketPort;
};

export function profileAvatarPath(userId: string): string {
  return `${userId}/avatar`;
}

export function validateProfileAvatar(file: File): string | null {
  if (!PROFILE_AVATAR_MIME_TYPES.includes(file.type as (typeof PROFILE_AVATAR_MIME_TYPES)[number])) {
    return "اختر صورة بصيغة JPG أو PNG أو WEBP أو GIF أو AVIF.";
  }
  if (file.size > PROFILE_AVATAR_MAX_BYTES) {
    return "يجب ألا يتجاوز حجم الصورة 5 ميغابايت.";
  }
  return null;
}

function storagePort(injected?: ProfileAvatarStoragePort): ProfileAvatarStoragePort {
  if (injected) return injected;
  return createClient().storage as unknown as ProfileAvatarStoragePort;
}

function isMissingObject(error: StorageErrorLike): boolean {
  const status = Number(error.statusCode);
  const message = error.message.toLowerCase();
  return status === 404 || message.includes("not found") || message.includes("does not exist");
}

export async function downloadProfileAvatar(
  userId: string,
  injected?: ProfileAvatarStoragePort,
): Promise<Blob | null> {
  const { data, error } = await storagePort(injected)
    .from(PROFILE_AVATAR_BUCKET)
    .download(profileAvatarPath(userId));

  if (error) {
    if (isMissingObject(error)) return null;
    throw new Error("PROFILE_AVATAR_DOWNLOAD_FAILED");
  }
  return data;
}

export async function uploadProfileAvatar(
  userId: string,
  file: File,
  injected?: ProfileAvatarStoragePort,
): Promise<void> {
  const validationError = validateProfileAvatar(file);
  if (validationError) throw new Error(validationError);

  const { error } = await storagePort(injected)
    .from(PROFILE_AVATAR_BUCKET)
    .upload(profileAvatarPath(userId), file, {
      cacheControl: "3600",
      contentType: file.type,
      upsert: true,
    });

  if (error) throw new Error("PROFILE_AVATAR_UPLOAD_FAILED");
}

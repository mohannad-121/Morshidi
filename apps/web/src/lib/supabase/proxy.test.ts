import { isProtectedStudentPath } from "@/lib/supabase/proxy";

test.each(["/student", "/student/profile", "/student/results/current"])(
  "protects student path %s",
  (path) => expect(isProtectedStudentPath(path)).toBe(true),
);

test.each(["/", "/login", "/advisor", "/students"])(
  "does not broaden the protected matcher to %s",
  (path) => expect(isProtectedStudentPath(path)).toBe(false),
);

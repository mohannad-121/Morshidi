"use client";

import { useCallback, useEffect, useRef } from "react";
import { useAuth } from "@/auth/auth-provider";

const HASH_TO_PLATE: Record<string, number> = {
  "#the-path": 6,
  "#the-plan": 3,
  "#insights": 4,
};

type SketchbookMessage = {
  type?: string;
};

export function MorshidiSketchbookLandingPage({
  className,
}: {
  className?: string;
}) {
  const auth = useAuth();
  const frameRef = useRef<HTMLIFrameElement>(null);
  const destination = auth.isAuthenticated ? "/student" : "/login";
  const source = `/landing-pages/morshidi-sketchbook.html?destination=${encodeURIComponent(destination)}`;

  const syncHash = useCallback(() => {
    const plate = HASH_TO_PLATE[window.location.hash];
    if (plate === undefined) return;
    frameRef.current?.contentWindow?.postMessage(
      { type: "morshidi:go-to", plate },
      window.location.origin,
    );
  }, []);

  useEffect(() => {
    const handleMessage = (event: MessageEvent<SketchbookMessage>) => {
      if (
        event.origin === window.location.origin &&
        event.data?.type === "morshidi:ready"
      ) {
        syncHash();
      }
    };

    window.addEventListener("hashchange", syncHash);
    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("hashchange", syncHash);
      window.removeEventListener("message", handleMessage);
    };
  }, [syncHash]);

  return (
    <iframe
      ref={frameRef}
      className={className}
      src={source}
      title="دفتر مرشدي الأكاديمي التفاعلي"
      onLoad={syncHash}
      sandbox="allow-scripts allow-same-origin allow-top-navigation-by-user-activation"
      referrerPolicy="same-origin"
    />
  );
}

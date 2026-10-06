import type { MetadataRoute } from "next";

// Metadata only. No service worker or offline cache of authenticated records.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "مرشدي | Morshidi Academic Intelligence",
    short_name: "مرشدي",
    description: "Arabic-first modeled academic planning and explanations",
    lang: "ar",
    dir: "rtl",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#FAFAF8",
    theme_color: "#A94721",
    icons: [{ src: "/brand/morshidi-favicon.png", sizes: "256x256", type: "image/png" }],
  };
}

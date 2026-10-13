import type { NextConfig } from "next";

export const contentSecurityPolicy = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' blob: data:",
  "font-src 'self' data:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "connect-src 'self' https://morshidi.onrender.com https://*.supabase.co http://127.0.0.1:* http://localhost:*",
].join("; ");

const sketchbookContentSecurityPolicy = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' blob: data:",
  "font-src 'self' data:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'self'",
  "connect-src 'self'",
].join("; ");

const nextConfig: NextConfig = {
  devIndicators: false,

  async headers() {
    return [
      {
        source: "/landing-pages/morshidi-sketchbook.html",
        headers: [
          {
            key: "Content-Security-Policy",
            value: sketchbookContentSecurityPolicy,
          },
        ],
      },
      {
        source: "/((?!landing-pages/morshidi-sketchbook\\.html).*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: contentSecurityPolicy,
          },
        ],
      },
    ];
  },
};

export default nextConfig;
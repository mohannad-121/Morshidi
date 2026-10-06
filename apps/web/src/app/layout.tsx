import type { Metadata, Viewport } from "next";
import { Alexandria, IBM_Plex_Sans_Arabic } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/auth/auth-provider";
import { GlobalNavbar } from "@/components/layout/GlobalNavbar";
import { GlobalFooter } from "@/components/layout/GlobalFooter";

const bodyFont = IBM_Plex_Sans_Arabic({
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
  subsets: ["arabic", "latin"],
  display: "swap",
});

const headingFont = Alexandria({
  variable: "--font-heading",
  subsets: ["arabic", "latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "مرشدي | Morshidi — نظام الذكاء الأكاديمي",
  description: "قرارات أكاديمية أوضح، تخطيط أذكى، ومسار دراسي يمكنك فهمه.",
  icons: {
    icon: [
      { url: "/brand/morshidi-favicon.png", type: "image/png", sizes: "256x256" },
    ],
    shortcut: "/brand/morshidi-favicon.png",
    apple: "/brand/morshidi-favicon.png",
  },
};

export const viewport: Viewport = { themeColor: "#fafaf8", width: "device-width", initialScale: 1 };

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="ar"
      dir="rtl"
      className={`${bodyFont.variable} ${headingFont.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <GlobalNavbar />
          <main className="flex-1">{children}</main>
          <GlobalFooter />
        </AuthProvider>
      </body>
    </html>
  );
}

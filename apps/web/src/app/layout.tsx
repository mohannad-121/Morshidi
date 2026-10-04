import type { Metadata, Viewport } from "next";
import { Reem_Kufi, Readex_Pro } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/auth/auth-provider";
import { GlobalNavbar } from "@/components/layout/GlobalNavbar";
import { GlobalFooter } from "@/components/layout/GlobalFooter";

const geistSans = Readex_Pro({
  variable: "--font-body",
  subsets: ["arabic", "latin"],
});

const geistMono = Reem_Kufi({
  variable: "--font-heading",
  subsets: ["arabic", "latin"],
});

export const metadata: Metadata = {
  title: "مرشدي | Morshidi — نظام الذكاء الأكاديمي",
  description: "قرارات أكاديمية أوضح، تخطيط أذكى، ومسار دراسي يمكنك فهمه.",
  icons: {
    icon: [
      { url: "/brand/mark.svg", type: "image/svg+xml" },
    ],
    shortcut: "/brand/mark.svg",
  },
};

export const viewport: Viewport = { themeColor: "#0B1210", width: "device-width", initialScale: 1 };

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="ar"
      dir="rtl"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
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

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/auth/auth-provider";
import { GlobalNavbar } from "@/components/layout/GlobalNavbar";
import { GlobalFooter } from "@/components/layout/GlobalFooter";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "مرشدي | Morshidi — نظام الذكاء الأكاديمي",
  description: "قرارات أكاديمية أوضح، تخطيط أذكى، ومسار دراسي يمكنك فهمه.",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    shortcut: "/favicon.ico",
    apple: "/brand/morshidi-guide.png",
  },
};

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
      <body className="min-h-full flex flex-col bg-[#FFFCF4] text-[#28241C]">
        <AuthProvider>
          <GlobalNavbar />
          <main className="flex-1">{children}</main>
          <GlobalFooter />
        </AuthProvider>
      </body>
    </html>
  );
}

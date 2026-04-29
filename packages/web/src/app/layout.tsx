import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { MobileNav } from "@/components/mobile-nav";

export const metadata: Metadata = {
  title: "Cadence - Voice-First Content Generation",
  description: "Generate authentic social media content in your unique voice",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="hidden lg:block">
          <Sidebar />
        </div>

        <MobileNav />

        <main className="min-h-screen bg-background pt-16 lg:ml-60 lg:pt-0">
          {children}
        </main>
      </body>
    </html>
  );
}

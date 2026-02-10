import type { Metadata } from "next";
import { AppSidebar } from "@/components/app-sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Twitter Account Finder",
  description:
    "Describe who you want to find. We'll search Twitter and rank the best matches.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body>
        <div className="flex h-screen overflow-hidden">
          <AppSidebar />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-[760px] px-4">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}

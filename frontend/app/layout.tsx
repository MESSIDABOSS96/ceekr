import type { Metadata } from "next";
import { Space_Mono } from "next/font/google";
import "./globals.css";

const spaceMono = Space_Mono({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-space-mono",
});

export const metadata: Metadata = {
  title: "Ceekr",
  description:
    "Describe who you want to find. We'll search Twitter and rank the best matches.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${spaceMono.variable}`}>
      <body>
        <div className="vignette" />
        <div className="relative z-10">
          <div className="flex min-h-screen justify-center">
            <main className="w-full">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Base Trading Agent — AI War Room",
  description: "Real-time AI agent dashboard for Base blockchain trading bot",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="scanlines">
        {children}
      </body>
    </html>
  );
}

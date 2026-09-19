import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import { AppShell } from "../components/app-shell";

export const metadata: Metadata = {
  title: "Supply Chain Autopilot",
  description: "Operational intelligence for resilient supply chains.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}

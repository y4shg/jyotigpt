import type { Metadata, Viewport } from "next";
import { Toaster } from "sonner";
import "./globals.css";
import { AppProvider } from "@/lib/store";
import { ServiceWorkerRegistration } from "@/components/ServiceWorkerRegistration";

export const metadata: Metadata = {
  title: "JyotiGPT",
  description:
    "JyotiGPT — a self-hosted AI chat companion for the Brahma Kumaris community.",
  manifest: "/manifest.json",
  icons: { icon: "/favicon.png" },
  appleWebApp: {
    capable: true,
    title: "JyotiGPT",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  themeColor: "#171717",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="h-dvh">
        <AppProvider>
          {children}
          <Toaster position="bottom-right" richColors />
          <ServiceWorkerRegistration />
        </AppProvider>
      </body>
    </html>
  );
}

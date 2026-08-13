import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Single-origin deploy: the web server is the one origin the browser talks
  // to, and /api/* is proxied to the FastAPI backend running on :8000 in the
  // same container. Skipped in local dev, where the frontend is configured to
  // call the dev API directly via NEXT_PUBLIC_API_BASE_URL.
  async rewrites() {
    if (process.env.NODE_ENV === "development") return [];
    return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }];
  },
  images: {
    unoptimized: true,
  },
};

export default nextConfig;

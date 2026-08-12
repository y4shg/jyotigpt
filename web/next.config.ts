import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The backend is a separate FastAPI app (see api/). In production the API is
  // reached through a reverse proxy / docker-compose networking; for a
  // single-origin deploy, uncomment the rewrites below to proxy /api.
  //
  // async rewrites() {
  //   return [{ source: "/api/:path*", destination: "http://api:8000/api/:path*" }];
  // },
  images: {
    unoptimized: true,
  },
};

export default nextConfig;

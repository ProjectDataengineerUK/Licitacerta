import type { NextConfig } from "next";

const API_TARGET =
  process.env.API_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api-proxy/:path*",
        destination: `${API_TARGET}/:path*`,
      },
    ];
  },
};

export default nextConfig;

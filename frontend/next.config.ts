import type { NextConfig } from "next";

// Where the FastAPI backend listens. Read when the Next.js server starts
// (dev) or builds (prod), never shipped to the browser.
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // The browser calls /api/... on the same origin; Next.js proxies it to the
  // backend. This avoids CORS configuration and keeps the backend URL private.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;

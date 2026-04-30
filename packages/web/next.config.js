const path = require("path");

const rootDir = path.join(__dirname, "../..");
const isStaticExport = process.env.NEXT_OUTPUT === "export";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: isStaticExport ? "export" : "standalone",
  outputFileTracingRoot: rootDir,
  turbopack: {
    root: rootDir,
  },
  ...(isStaticExport
    ? {}
    : {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: process.env.API_URL
                ? `${process.env.API_URL}/api/:path*`
                : "http://api:8000/api/:path*",
            },
          ];
        },
      }),
};

module.exports = nextConfig;

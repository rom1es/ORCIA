import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@orcia/ui", "@orcia/api-client"],
  reactStrictMode: true,
};

export default nextConfig;

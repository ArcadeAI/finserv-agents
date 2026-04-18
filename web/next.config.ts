import type { NextConfig } from "next";
import { config } from "dotenv";
import { resolve } from "path";

// Load .env from repo root so all config lives in one place
config({ path: resolve(__dirname, "../.env") });

const nextConfig: NextConfig = {
  turbopack: {
    root: resolve(__dirname, ".."),
  },
};

export default nextConfig;

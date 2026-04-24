import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const frontendRoot = path.resolve(fileURLToPath(new URL(".", import.meta.url)));

const nextConfig: NextConfig = {
  turbopack: {
    root: frontendRoot,
  },
};

export default nextConfig;

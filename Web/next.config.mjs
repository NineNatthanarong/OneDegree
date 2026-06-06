/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export: `next build` emits a self-contained site to ./out, which the
  // FastAPI backend serves. No Node runtime needed in the final container.
  output: "export",
  images: { unoptimized: true }
};

export default nextConfig;

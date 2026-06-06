/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export: `next build` emits a self-contained site to ./out, which the
  // FastAPI backend serves. No Node runtime needed in the final container.
  output: "export",
  // Emit each route as <route>/index.html so the FastAPI StaticFiles(html=True)
  // mount can serve nested routes like /timetable/ directly.
  trailingSlash: true,
  images: { unoptimized: true }
};

export default nextConfig;

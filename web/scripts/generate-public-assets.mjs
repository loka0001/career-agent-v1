import { mkdir, writeFile } from "node:fs/promises";

const origin = (
  process.env.PUBLIC_SITE_URL || "https://commerce-ai.example"
).replace(/\/$/, "");
const output = new URL("../public/", import.meta.url);
await mkdir(output, { recursive: true });

const files = {
  "robots.txt": `User-agent: *\nAllow: /\nDisallow: /app/\nSitemap: ${origin}/sitemap.xml\n`,
  "sitemap.xml": `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>${origin}/</loc></url>\n  <url><loc>${origin}/terms</loc></url>\n</urlset>\n`,
  "manifest.json": `${JSON.stringify(
    {
      name: "Commerce Revenue Autopilot",
      short_name: "Commerce AI",
      description: "AI-assisted commerce operations and revenue workflows.",
      start_url: "/",
      display: "standalone",
      background_color: "#f6f5f2",
      theme_color: "#704768",
      icons: [{ src: "/favicon.svg", sizes: "any", type: "image/svg+xml" }],
    },
    null,
    2,
  )}\n`,
  "favicon.svg": `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#704768"/><path d="M18 20h28l-3 25H21l-3-25Zm7-7a7 7 0 0 1 14 0v7h-5v-7a2 2 0 0 0-4 0v7h-5v-7Z" fill="#fff"/></svg>\n`,
};

await Promise.all(
  Object.entries(files).map(([name, contents]) =>
    writeFile(new URL(name, output), contents),
  ),
);

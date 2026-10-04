import { build } from "esbuild";
import { mkdir, readFile, writeFile, cp } from "node:fs/promises";
await mkdir("generated", { recursive: true });
const css = await readFile("ui/style.css", "utf8");
const js = await readFile("ui/app.js", "utf8");
const html = await readFile("ui/index.html", "utf8");
await writeFile(
  "generated/page.js",
  `export const html=${JSON.stringify(html.replace("/*APP_CSS*/", css))};\nexport const js=${JSON.stringify(js)};\n`,
);
await mkdir("dist/server", { recursive: true });
await build({
  entryPoints: ["worker/index.js"],
  outfile: "dist/server/index.js",
  bundle: true,
  format: "esm",
  platform: "neutral",
  target: "es2022",
  minify: true,
});
await cp(".openai", "dist/.openai", { recursive: true });
await cp("drizzle", "dist/drizzle", { recursive: true });
console.log("Enterprise Worker, console assets, and schema migrations built.");

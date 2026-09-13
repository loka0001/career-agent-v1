import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

const stylesRoot = new URL("../src/styles/", import.meta.url);
const forbidden =
  /(?:^|[;{\s])(?:(?:(?:margin|padding|border|inset)-(?:left|right)|left|right)\s*:|text-align\s*:\s*(?:left|right))/gim;
const failures = [];

for (const name of await readdir(stylesRoot)) {
  if (!name.endsWith(".css")) continue;
  const source = await readFile(new URL(name, stylesRoot), "utf8");
  for (const match of source.matchAll(forbidden)) {
    const line = source.slice(0, match.index).split("\n").length;
    failures.push(`${join("src", "styles", name)}:${line}`);
  }
}

if (failures.length) {
  console.error(
    `Use logical CSS properties for RTL/LTR support:\n${failures.join("\n")}`,
  );
  process.exit(1);
}

console.log("Logical CSS check passed.");

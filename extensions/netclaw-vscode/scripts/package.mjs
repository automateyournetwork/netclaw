import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
const cwd = fileURLToPath(new URL("../", import.meta.url)),
  root = path.resolve(cwd, "../..");
const require = createRequire(new URL("../package.json", import.meta.url));
const { createVSIX, listFiles } = require("@vscode/vsce");
const source = execFileSync("git", ["rev-parse", "HEAD"], {
  cwd: root,
  encoding: "utf8",
}).trim();
if (!/^[a-f\d]{40}$/.test(source))
  throw Error("A committed source reference is required.");
const dirty = execFileSync("git", ["status", "--porcelain"], {
  cwd: root,
  encoding: "utf8",
}).trim();
if (dirty)
  throw Error(
    "Commit the reviewed source before packaging so Marketplace links and provenance identify the actual files.",
  );
const manifest = JSON.parse(
  fs.readFileSync(path.join(cwd, "package.json"), "utf8"),
);
const packagePath = path.join(cwd, `netclaw-${manifest.version}.vsix`);
process.chdir(cwd);
await createVSIX({
  cwd,
  packagePath,
  dependencies: false,
  baseContentUrl: `https://github.com/automateyournetwork/netclaw/blob/${source}/extensions/netclaw-vscode`,
  baseImagesUrl: `https://raw.githubusercontent.com/automateyournetwork/netclaw/${source}/extensions/netclaw-vscode`,
});
const packaged = new Set(await listFiles({ cwd, dependencies: false }));
// Every emitted runtime bundle and its third-party notices must ship together.
// This catches allowlist omissions such as a working source topology view whose
// renderer was absent from the installable artifact.
for (const name of fs.readdirSync(path.join(cwd, "dist"))) {
  if (/\.(?:cjs|mjs|js|txt)$/.test(name) && !packaged.has("dist/" + name))
    throw Error(`Required runtime asset missing from VSIX: dist/${name}`);
}
// Setup metadata, assistant skill and deployment preset are loaded from disk in
// an installed extension. Source-mode tests alone cannot catch their omission.
for (const directory of ["setup", "skills", "preset"]) {
  for (const name of fs.readdirSync(path.join(cwd, "dist", directory), {
    recursive: true,
  })) {
    const relative = `dist/${directory}/${name.replaceAll(path.sep, "/")}`;
    if (fs.statSync(path.join(cwd, relative)).isFile() && !packaged.has(relative))
      throw Error(`Required setup asset missing from VSIX: ${relative}`);
  }
}
const bytes = fs.readFileSync(packagePath),
  sha256 = createHash("sha256").update(bytes).digest("hex");
fs.mkdirSync(path.join(cwd, "out"), { recursive: true });
fs.writeFileSync(
  path.join(cwd, "out/package.json"),
  JSON.stringify(
    {
      publisher: manifest.publisher,
      name: manifest.name,
      version: manifest.version,
      source,
      sha256,
      bytes: bytes.length,
      artifact: path.basename(packagePath),
      qualification:
        "Extension 1.5.0 / source 1.18.0 optional NetConverter setup (162-netconverterai); VS Code >=1.109. All 44 scoped tasks complete, including real approved synthetic conversions, protected IOS-XE rehearsal and native Border/member discovery. The final Mac Risk install used owner-requested simulated review inputs with real effects. Native Windows/WSL, Hermes NetConverter member and Junos appliance acceptance remain unqualified. See specs/162-netconverterai/verification.md and release-verification.md. Source and extension publication authorized on 2026-11-01. Existing runtime upgrades remain separate.",
    },
    null,
    2,
  ) + "\n",
);
console.log(
  JSON.stringify({
    artifact: packagePath,
    source,
    sha256,
    bytes: bytes.length,
  }),
);

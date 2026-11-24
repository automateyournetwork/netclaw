import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
const source = fs.readFileSync(path.join(root, "src/extension.ts"), "utf8");

test("connection rows offer inline and context Rename and Remove", () => {
  const menus = pkg.contributes.menus["view/item/context"];
  for (const command of ["netclaw.renameConnection", "netclaw.removeConnection"]) {
    const rows = menus.filter((m) => m.command === command);
    assert.ok(rows.some((m) => m.group.startsWith("inline")), command + " inline");
    assert.ok(rows.some((m) => m.group.startsWith("navigation")), command + " context");
    for (const m of rows) assert.match(m.when, /viewItem == netclaw\.connection/);
  }
  const icons = Object.fromEntries(pkg.contributes.commands.map((c) => [c.command, c.icon]));
  assert.equal(icons["netclaw.removeConnection"], "$(trash)");
  assert.equal(icons["netclaw.renameConnection"], "$(edit)");
});

test("removal asks for confirmation and states what it does not touch", () => {
  const block = source.slice(source.indexOf('register("removeConnection"'), source.indexOf("const openDomain"));
  assert.match(block, /showWarningMessage/);
  assert.match(block, /modal: true/);
  assert.match(block, /does not stop, change or delete/);
  assert.ok(block.indexOf("showWarningMessage") < block.indexOf("profiles.remove"), "confirm before removing");
  assert.match(block, /answer !== "Remove connection"\) return/);
});

test("both connection lists mark profile rows so the menus apply", () => {
  const rows = source.match(/contextValue: "netclaw\.connection"/g) || [];
  assert.equal(rows.length, 2);
  assert.equal((source.match(/profileId: p\.id/g) || []).length, 2);
});

#!/usr/bin/env node
/**
 * Build a read-only GitHub Pages edition of Character Lab from the SAME
 * discovered model inventory as the localhost server.
 *
 * Usage: node scripts/build-character-lab-pages.mjs <empty-output-directory>
 * Only the playable page, its client, the inventory JSON and referenced
 * images/GLBs are published. No secrets, git history, or generation scripts.
 */
import assert from "node:assert/strict";
import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { inventory } from "./serve-character-lab.mjs";

const repo = resolve(dirname(fileURLToPath(import.meta.url)), "..");
if (!process.argv[2]) throw new Error("Usage: node scripts/build-character-lab-pages.mjs <output-directory>");
const output = resolve(process.argv[2]);
if (output === repo || output.startsWith(repo + sep)) {
  throw new Error("Pages output must be an empty temporary directory outside the repository");
}
if (existsSync(output)) throw new Error("Refusing to overwrite existing Pages output: " + output);
mkdirSync(output, { recursive: true });

function publish(sourcePath, targetPath = sourcePath) {
  const input = resolve(repo, sourcePath);
  const target = resolve(output, targetPath);
  assert(!relative(repo, input).startsWith(".."), "Input outside repository");
  assert(!relative(output, target).startsWith(".."), "Output outside Pages bundle");
  assert(existsSync(input) && statSync(input).isFile(), "Missing Pages dependency: " + sourcePath);
  if (extname(input) === ".glb") {
    assert.equal(readFileSync(input).subarray(0, 4).toString("utf8"), "glTF",
      "Invalid GLB: " + sourcePath);
  }
  mkdirSync(dirname(target), { recursive: true });
  copyFileSync(input, target);
  return statSync(input).size;
}
function repositoryAssetPath(url) {
  assert(typeof url === "string", "An asset URL must be a string");
  const path = url.startsWith("/") ? url.slice(1) : url;
  assert(path.startsWith("assets/") && !path.split("/").includes("..") && !path.includes("\\"),
    "Unexpected non-asset URL: " + url);
  return path;
}

const catalog = inventory();
assert(catalog.characters.length > 0, "Cannot publish an empty Character Lab");
const assets = new Set([
  "assets/experiments/props/marches_hache/trellis-v1/axe.glb",
  "assets/experiments/props/marches_hache/trellis-v1/grip-plan.json",
]);
for (const character of catalog.characters) {
  assert(character.models.length > 0, "No models for " + character.id);
  for (const model of character.models) assets.add(repositoryAssetPath(model.url));
  for (const url of Object.values(character.views)) assets.add(repositoryAssetPath(url));
  if (character.original) assets.add(repositoryAssetPath(character.original));
}

let bytes = 0;
bytes += publish("character-lab.html", "index.html");
bytes += publish("character-lab.html");
bytes += publish("scripts/character-lab-client.js");
bytes += publish("scripts/weapon-grip-geometry.js");
for (const path of [...assets].sort()) bytes += publish(path);
const apiDir = join(output, "api");
mkdirSync(apiDir, { recursive: true });
writeFileSync(join(apiDir, "character-lab.json"), JSON.stringify(catalog, null, 2) + "\n");
const check = JSON.parse(readFileSync(join(apiDir, "character-lab.json"), "utf8"));
assert.equal(check.characters.length, catalog.characters.length);
console.log("Pages ready:", output, "| characters:", catalog.characters.length,
  "| assets:", assets.size, "| bytes:", bytes, "| no API keys or AI requests");

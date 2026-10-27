#!/usr/bin/env node
/**
 * WarConquer 3D sandbox: zero dependencies and strictly localhost-only.
 * Run: node scripts/serve-character-lab.mjs
 * Open: http://127.0.0.1:4173/character-lab.html
 *
 * Read-only. Discovers generated GLBs on each request; never invokes AI APIs.
 */
import { createServer } from "node:http";
import { createReadStream, existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PORT = Number(process.env.CHARACTER_LAB_PORT || 4173);
const HOST = "127.0.0.1";
const MESH_ROOT = join(REPO, "assets/experiments/rig-ready-3d");
const REFS_ROOT = join(REPO, "assets/experiments/rig-source-turnaround");
const SOURCE_CONCEPTS = { marches_hache: "/assets/concepts/marches/units/hache.png" };
const LABELS = { marches_hache: "Guerrier à la hache · Marches" };
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".glb": "model/gltf-binary",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
};

function dirs(root) {
  return existsSync(root) ? readdirSync(root, { withFileTypes: true })
    .filter(e => e.isDirectory()).map(e => e.name).sort() : [];
}
function publicPath(file) {
  return "/" + relative(REPO, file).split(sep).join("/");
}
function parseJson(file) {
  try { return JSON.parse(readFileSync(file, "utf8")); }
  catch { return null; }
}
function inventory() {
  const characters = [];
  for (const id of dirs(MESH_ROOT)) {
    for (const pose of dirs(join(MESH_ROOT, id))) {
      const base = join(MESH_ROOT, id, pose);
      const source = join(REFS_ROOT, id, pose);
      const models = [];
      const add = (file, name, kind, priority, motion = null) => {
        if (existsSync(file) && statSync(file).isFile()) {
          models.push({ id: id + "/" + pose + "/" + kind + "/" + models.length,
            name, kind, priority, motion, url: publicPath(file),
            bytes: statSync(file).size });
        }
      };
      add(join(base, "unrigged.glb"), "01 · Maillage Hunyuan", "mesh", 10);
      add(join(base, "rigged.glb"), "02 · Squelette Uthana", "rig", 20);
      for (const motionId of dirs(join(base, "motion"))) {
        const motionDir = join(base, "motion", motionId);
        const playable = join(motionDir, "warconquer-playable.glb");
        const animated = join(motionDir, "warconquer-animated.glb");
        add(animated, "03 · " + motionId, "animation", motionId.includes("walk") ? 40 : 30, motionId);
        add(playable, "04 · Jouable · " + motionId, "playable", 60, motionId);
      }
      models.sort((a,b) => b.priority - a.priority);
      const report = parseJson(join(base, "rig-report.json"));
      const mesh = parseJson(join(base, "mesh-report.json"));
      const refs = {};
      for (const view of ["front", "back", "left", "right"]) {
        const file = join(source, view + ".png");
        if (existsSync(file)) refs[view] = publicPath(file);
      }
      const original = SOURCE_CONCEPTS[id] || null;
      if (models.length) characters.push({
        id, pose, name: LABELS[id] || id.replaceAll("_", " "),
        original, views: refs, models,
        metrics: { joints: report?.glb?.joint_count ?? report?.joint_count ?? null,
                   faces: mesh?.geometry?.faces ?? 25000 },
      });
    }
  }
  return { schema: 1, characters, generatedAt: new Date().toISOString(),
    note: "The sandbox moves the 3D character with WASD. Walk cycles require a separately rigged walking clip." };
}

function send(res, code, body, type) {
  res.writeHead(code, { "Content-Type": type || "text/plain; charset=utf-8",
    "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
  res.end(body);
}

const server = createServer((req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") return send(res, 405, "Method not allowed");
  let pathname;
  try { pathname = new URL(req.url, "http://localhost").pathname; }
  catch { return send(res, 400, "Bad URL"); }
  if (pathname === "/api/character-lab") {
    return send(res, 200, JSON.stringify(inventory()), "application/json; charset=utf-8");
  }
  if (pathname === "/" || pathname === "/character-lab.html") {
    pathname = "/character-lab.html";
  } else if (!pathname.startsWith("/assets/")) {
    return send(res, 404, "Not found");
  }
  let absolute;
  try { absolute = resolve(REPO, "." + decodeURIComponent(pathname)); }
  catch { return send(res, 400, "Bad URL encoding"); }
  const rel = relative(REPO, absolute);
  if (rel.startsWith("..") || rel === "" || rel.startsWith(sep) || !existsSync(absolute)
      || !statSync(absolute).isFile()) return send(res, 404, "Not found");
  const type = MIME[extname(absolute).toLowerCase()];
  if (!type) return send(res, 415, "Unsupported file type");
  res.writeHead(200, { "Content-Type": type, "Content-Length": statSync(absolute).size,
    "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
  if (req.method === "HEAD") { res.end(); return; }
  const stream = createReadStream(absolute);
  stream.on("error", () => res.destroy());
  stream.pipe(res);
});

if (!Number.isInteger(PORT) || PORT < 1024 || PORT > 65535) {
  throw new Error("CHARACTER_LAB_PORT must be an unprivileged TCP port");
}
server.listen(PORT, HOST, () => {
  console.log("WarConquer Character Lab: http://" + HOST + ":" + PORT + "/character-lab.html");
  console.log("Read-only, loopback-only, no generative model calls");
});

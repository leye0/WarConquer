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
import { createHash } from "node:crypto";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PORT = Number(process.env.CHARACTER_LAB_PORT || 4173);
const HOST = "127.0.0.1";
const MESH_ROOT = join(REPO, "assets/experiments/rig-ready-3d");
const REFS_ROOT = join(REPO, "assets/experiments/rig-source-turnaround");
const PROPS_ROOT = join(REPO, "assets/experiments/props");
const UNIT_MANIFESTS_ROOT = join(REPO, "data/units");
function unitManifests(){
  const units=[];
  if(!existsSync(UNIT_MANIFESTS_ROOT))return units;
  for(const name of readdirSync(UNIT_MANIFESTS_ROOT).filter(n=>n.endsWith(".json") && /^[a-z][a-z0-9_]*$/.test(n.slice(0,-5)))){
    const doc=parseJson(join(UNIT_MANIFESTS_ROOT,name));
    if(doc?.schema===1 && doc.id===name.slice(0,-5) &&
       typeof doc.source?.character_image==="string" &&
       doc.source.character_image.startsWith("assets/concepts/") &&
       doc.source.character_image.endsWith(".png") &&
       !doc.source.character_image.includes("..") &&
       !doc.source.character_image.includes("\\") &&
       existsSync(join(REPO,doc.source.character_image)))units.push(doc);
  }
  return units;
}
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
// Discover per-unit grip plans, so adding the next weapon never needs a code
// change in the Character Lab renderer or the static Pages exporter.
function propPlans(unitId) {
  const folder = join(PROPS_ROOT, unitId);
  const result = [];
  for(const variant of dirs(folder)) {
    // One canonical plan per object. Git, not numbered files, owns revisions.
    const planFile=join(folder,variant,"grip-plan.json");
    const plan=parseJson(planFile);
    if(![2,3].includes(plan?.schema))continue;
    const glbUrl = plan.inputs?.object_glb;
    if(typeof glbUrl !== "string" || !/^assets\/experiments\/props\/[a-z0-9_/-]+\.glb$/.test(glbUrl))continue;
    const actual = resolve(REPO, glbUrl);
    if(!actual.startsWith(PROPS_ROOT + sep) || !existsSync(actual))continue;
    const prop = {id:unitId+"/"+variant, name:plan.specifications?.object_kind||"Objet",
      gripPlan:publicPath(planFile), gripReviewStatus:plan.visual_qa?.status||"baseline",
      model:publicPath(actual)};
    // Public only when the shipped grip plan already pins this exact vision
    // contract AND every named role was lifted onto the physical GLB.
    const provenance=plan.interaction_provenance;
    if(typeof provenance?.path==="string"&&
       /^assets\/experiments\/props\/[a-z0-9_/-]+\/interaction-contract\.json$/.test(provenance.path)){
      const contractFile=resolve(REPO,provenance.path);
      if(contractFile.startsWith(PROPS_ROOT+sep)&&existsSync(contractFile)){
        const fingerprint=createHash("sha256").update(readFileSync(contractFile)).digest("hex");
        const contract=parseJson(contractFile);
        if(fingerprint===provenance.sha256 &&
           fingerprint===plan.mesh_landmarks?.interaction_sha256 &&
           contract?.semantic_status==="confirmed" &&
           contract?.mixamo_pose_status==="pending_real_joint_validation")
          prop.interactionContract=publicPath(contractFile);
      }
    }
    // Physical size is an independent, approximate metric measurement; the
    // old semantic attachment file is never permitted to dictate it.
    const sizeFile = join(folder, variant, "physical-size.json");
    const physical = parseJson(sizeFile);
    if (physical?.schema === 1 && physical?.units === "cm" &&
        Number.isFinite(physical.estimated_length_cm) &&
        physical.estimated_length_cm >= 2 && physical.estimated_length_cm <= 1000) {
      prop.physicalSize = publicPath(sizeFile);
    }
    result.push(prop);
  }
  return result;
}

export function inventory() {
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
      add(join(base, "fal-textured.glb"), "05 · fal.ai · Texture UV (sans rig)", "mesh", 50);
      add(join(base, "motion/fal-mixamo-v1/fal-rigged.glb"), "05b · fal.ai · UV + Uthana · pose de base", "rig", 53, "fal-mixamo-v1");
      add(join(base, "motion/fal-mixamo-v1/warconquer-textured-playable.glb"), "06 · fal.ai · UV + Uthana + Mixamo", "playable", 70, "fal-mixamo-v1");
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
      const info=unitManifests().find(m=>m.id===id);
      const original=info?"/"+info.source.character_image:null;
      if (models.length) characters.push({
        id, pose, name: info?.title || LABELS[id] || id.replaceAll("_", " "),
        original, views: refs, models, props: propPlans(id),
        buildStatus:models.some(m=>m.kind==="playable"||m.kind==="animation")?"playable"
          :(models.some(m=>m.kind==="rig")?"rigged":"mesh_only"),
        pipeline:info?{manifest:"data/units/"+id+".json",unitId:id}:null,
        metrics: { joints: report?.glb_geometry?.joint_count ?? report?.glb?.joint_count ?? report?.joint_count ?? null,
                   faces: mesh?.glb_geometry?.faces ?? mesh?.geometry?.faces ?? 25000 },
      });
    }
  }
  // Each manifest appears in the unit selector, including units not yet
  // generated. A source-only unit must never inherit another unit's GLB.
  for(const doc of unitManifests()) {
    if(characters.some(c=>c.id===doc.id))continue;
    characters.push({
      id:doc.id,pose:"à construire",name:doc.title,
      original:"/"+doc.source.character_image,
      views:{},models:[],props:[],metrics:{joints:null,faces:null},
      buildStatus:"source_only",
      pipeline:{manifest:"data/units/"+doc.id+".json",
        unitId:doc.id,stage:"source",message:"Illustration prête · modèle 3D non produit"}
    });
  }
  const motion=parseJson(join(REPO,"data/motion-library.json"));
  const motionRoles=(motion?.schema===1 ? motion.clips : [])
    .filter(c=>c.included===true && typeof c.role==="string" &&
      typeof c.group_prefix==="string")
    .map(({role,group_prefix,equipment})=>({role,group_prefix,equipment}));
  return { schema: 1, characters, motionRoles, generatedAt: new Date().toISOString(),
    note: "Units have explicit source_only, mesh_only, rigged or playable build status. Genuine Mixamo animations are available only when present in each unit GLB." };
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
  if (pathname === "/api/character-lab" || pathname === "/api/character-lab.json") {
    return send(res, 200, JSON.stringify(inventory()), "application/json; charset=utf-8");
  }
  if (pathname === "/" || pathname === "/character-lab.html") {
    pathname = "/character-lab.html";
  } else if (!["/scripts/character-lab-client.js","/scripts/weapon-grip-geometry.js","/scripts/rig-contact-landmarks.js","/scripts/prop-motion-contact.js","/scripts/equipment-animation-policy.js","/scripts/arena-scene.js"].includes(pathname) && !pathname.startsWith("/assets/")) {
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
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  server.listen(PORT, HOST, () => {
    console.log("WarConquer Character Lab: http://" + HOST + ":" + PORT + "/character-lab.html");
    console.log("Read-only, loopback-only, no generative model calls");
  });
}

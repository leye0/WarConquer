#!/usr/bin/env node
/**
 * WarConquer 3D sandbox: zero dependencies and strictly localhost-only.
 * Run: node scripts/serve-character-lab.mjs
 * Open: http://127.0.0.1:4173/character-lab.html
 *
 * Read-only. Discovers generated GLBs on each request; never invokes AI APIs.
 */
import { createServer } from "node:http";
import { createHash } from "node:crypto";
import { createReadStream, existsSync, readdirSync, readFileSync, statSync } from "node:fs";
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
function fingerprint(file) {
  return createHash("sha256").update(readFileSync(file)).digest("hex");
}
function selectedGripPlan(folder, baseFile) {
  const base=parseJson(baseFile);
  if(![2,3].includes(base?.schema))return null;
  const objectPath=base.inputs?.object_image;
  const characterPath=base.inputs?.character_image;
  const modelPath=base.inputs?.object_glb;
  if(![objectPath,characterPath,modelPath].every(p=>typeof p==="string" &&
    p.startsWith("assets/") && !p.includes("..") && !p.includes("\\")))return null;
  const assetHashes=[objectPath,characterPath].map(p=>{
    const file=resolve(REPO,p);
    return file.startsWith(REPO+sep)&&existsSync(file)?fingerprint(file):null;
  });
  const mesh=resolve(REPO,modelPath);
  if(!mesh.startsWith(REPO+sep)||!existsSync(mesh)||
    base.input_hashes?.prop_glb_sha256!==fingerprint(mesh))return null;
  const candidates=readdirSync(folder).filter(name=>/^grip-plan-v\d+\.json$/.test(name))
    .sort((a,b)=>Number(b.match(/\d+/)[0])-Number(a.match(/\d+/)[0]));
  const validated=[];
  for(const name of candidates){
    const proposed=parseJson(join(folder,name));
    const review=proposed?.vision_review;
    const hashes=proposed?.input_hashes;
    const status=proposed?.visual_qa?.status;
    if(!["candidate","approved"].includes(status) ||
      proposed.inputs?.object_glb!==modelPath ||
      !Number.isFinite(proposed.derived_image_geometry?.grip_fraction_from_butt))continue;
    if(proposed.schema===4){
      if(review?.change_needed!==true || !Number.isFinite(review.confidence) ||
        review.confidence<.8 || hashes?.source_prop_sha256!==assetHashes[0] ||
        hashes?.source_character_sha256!==assetHashes[1] ||
        proposed.specifications?.head_direction!==review.head_direction ||
        proposed.specifications?.edge_direction!==review.edge_direction)continue;
    }else if(proposed.schema===3 && status==="approved"){
      if(hashes?.object_image_sha256!==assetHashes[0] ||
        hashes?.character_image_sha256!==assetHashes[1] ||
        hashes?.prop_glb_sha256!==fingerprint(mesh))continue;
    }else continue;
    validated.push({file:join(folder,name),plan:proposed,reviewStatus:status});
  }
  validated.sort((a,b)=>Number(b.reviewStatus==="approved")-
    Number(a.reviewStatus==="approved"));
  if(validated.length)return validated[0];
  return {file:baseFile,plan:base,reviewStatus:"baseline"};
}
// Discover per-unit grip plans, so adding the next weapon never needs a code
// change in the Character Lab renderer or the static Pages exporter.
function propPlans(unitId) {
  const folder = join(PROPS_ROOT, unitId);
  const result = [];
  for(const variant of dirs(folder)) {
    // Prefer an in-situ vision correction grounded in the real source images.
    // Candidates are deliberately exposed for the user's arena validation;
    // their status remains visible, never falsely promoted to "approved".
    const selected=selectedGripPlan(join(folder,variant),join(folder,variant,"grip-plan.json"));
    if(!selected)continue;
    const {file:planFile,plan,reviewStatus}=selected;
    const glbUrl = plan.inputs?.object_glb;
    if(typeof glbUrl !== "string" || !/^assets\/experiments\/props\/[a-z0-9_/-]+\.glb$/.test(glbUrl))continue;
    const actual = resolve(REPO, glbUrl);
    if(!actual.startsWith(PROPS_ROOT + sep) || !existsSync(actual))continue;
    const prop = {id:unitId+"/"+variant, name:plan.specifications?.object_kind||"Objet",
      gripPlan:publicPath(planFile), gripReviewStatus:reviewStatus, model:publicPath(actual)};
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
  return { schema: 1, characters, generatedAt: new Date().toISOString(),
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
  } else if (!["/scripts/character-lab-client.js","/scripts/weapon-grip-geometry.js","/scripts/equipment-animation-policy.js","/scripts/arena-scene.js"].includes(pathname) && !pathname.startsWith("/assets/")) {
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

/* WarConquer Character Lab — tiny, dependency-free frontend (Babylon runtime from CDN).
 * Model files and asset metadata stay in the repository; no generative API calls.
 */
(() => {
  "use strict";
  const byId = id => document.getElementById(id);
  // Resolve asset URLs under both localhost / and GitHub Pages /WarConquer/.
  const assetUrl = path => path?.startsWith("/assets/") ? "." + path : path;
  const FALLBACK = {
    schema: 1,
    characters: [{
      id: "marches_hache", pose: "tpose-v2", name: "Guerrier à la hache · Marches",
      original: "assets/concepts/marches/units/hache.png",
      props: [{gripPlan:"assets/experiments/props/marches_hache/trellis-v1/grip-plan.json"}],
      views: {
        front: "assets/experiments/rig-source-turnaround/marches_hache/tpose-v2/front.png",
        back: "assets/experiments/rig-source-turnaround/marches_hache/tpose-v2/back.png",
        left: "assets/experiments/rig-source-turnaround/marches_hache/tpose-v2/left.png",
        right: "assets/experiments/rig-source-turnaround/marches_hache/tpose-v2/right.png"
      },
      models: [
        { id: "axe", name: "03 · Attaque 3D — animée", kind: "animation", priority: 30,
          motion: "axe-chop-v1",
          url: "assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/axe-chop-v1/warconquer-animated.glb" },
        { id: "rig", name: "02 · Squelette riggé", kind: "rig", priority: 20,
          url: "assets/experiments/rig-ready-3d/marches_hache/tpose-v2/rigged.glb" },
        { id: "mesh", name: "01 · Maillage brut", kind: "mesh", priority: 10,
          url: "assets/experiments/rig-ready-3d/marches_hache/tpose-v2/unrigged.glb" }
      ],
      metrics: { joints: 52, faces: 25000 }
    }]
  };
  const state = {
    catalog: FALLBACK, selected: null, scene: null, camera: null,
    engine: null, character: null, imported: null, attack: null, walk: null, run: null, idle: null, currentMotion: null,
    animGroups: [], idleChoices: [], cast: null, loadedAsset: null, attacking: false, moving: false,
    sprintLatched: false, fireballs: [], castPending: null,
    returningPose: null, actionSerial: 0, poseReturns: 0,
    ready: false, input: new Set(), touch: new Set(), follow: true,
    speed: 2.7, scale: 1, facingBias: 0, pendingLoad: 0,
    importUrl: null, weaponImport: null, weaponAnchor: null
  };
  const viewLabels = { front: "Face", back: "Dos", left: "Profil gauche", right: "Profil droit" };

  function text(id, value) { const node = byId(id); if (node) node.textContent = value; }
  function setStatus(value, level) {
    text("statusText", value);
    byId("stateDot").dataset.level = level || "normal";
  }
  function setOverlay(message, visible) {
    text("loadingMessage", message);
    byId("loadingOverlay").hidden = !visible;
  }
  function urls() {
    const c = state.selected;
    return c ? c.models.slice().sort((a,b) => b.priority - a.priority) : [];
  }
  function renderSources() {
    const c = state.selected;
    const root = byId("sources");
    root.replaceChildren();
    if (!c) return;
    const items = [{ name: "Concept d'origine", path: c.original }]
      .concat(Object.entries(viewLabels).map(([key,name]) => ({ name, path: c.views[key] })));
    for (const item of items) {
      if (!item.path) continue;
      const card = document.createElement("figure");
      card.className = "source-card";
      const img = document.createElement("img");
      img.src = assetUrl(item.path); img.alt = item.name; img.loading = "lazy";
      const label = document.createElement("figcaption");
      label.textContent = item.name;
      card.append(img,label);
      root.append(card);
    }
  }
  function renderCatalog() {
    const characters = state.catalog.characters;
    const dropdown = byId("modelSelect");
    const saved = dropdown.value;
    dropdown.replaceChildren();
    if (!characters.length) {
      text("unitName", "Aucun GLB trouvé");
      setStatus("Ajoutez un maillage dans assets/experiments/rig-ready-3d", "warning");
      return;
    }
    state.selected = characters.find(x => x.id === state.selected?.id && x.pose === state.selected?.pose)
      || characters[0];
    for (const char of characters) {
      const group = document.createElement("optgroup");
      group.label = char.name + " / " + char.pose;
      for (const m of char.models.slice().sort((a,b) => b.priority - a.priority)) {
        const opt = document.createElement("option");
        opt.value = m.url;
        opt.textContent = char.name + " · " + m.name;
        group.append(opt);
      }
      dropdown.append(group);
    }
    if (saved && Array.from(dropdown.options).some(x => x.value === saved)) dropdown.value = saved;
    else dropdown.value = state.selected.models.slice().sort((a,b) => b.priority - a.priority)[0]?.url || "";
    selectByPath(dropdown.value);
  }
  function selectByPath(path) {
    for (const c of state.catalog.characters) {
      const model = c.models.find(m => m.url === path);
      if (model) {
        state.selected = c;
        state.loadedAsset = model;
        text("unitName", c.name);
        text("meshMetric", (c.metrics.faces || "—") + " triangles");
        text("jointMetric", model.kind === "mesh" ? "0 os · sans rig" : (c.metrics.joints || "—") + " os");
        renderSources();
        return;
      }
    }
  }

  async function fetchCatalog() {
    try {
      const response = await fetch("api/character-lab.json", { cache: "no-store" });
      if (!response.ok) throw new Error("No local catalog");
      const data = await response.json();
      if (!Array.isArray(data.characters)) throw new Error("Invalid catalog");
      state.catalog = data.characters.length ? data : FALLBACK;
      text("connectionState", "Catalogue du dépôt · actif");
    } catch {
      state.catalog = FALLBACK;
      text("connectionState", "Mode fichier · ouvrir avec le serveur local");
    }
    renderCatalog();
  }

  function createWorld() {
    if (!window.BABYLON) {
      setStatus("Babylon.js n'a pas chargé. Vérifiez la connexion Internet.", "error");
      setOverlay("Le moteur 3D n'a pas pu être chargé.", true);
      return false;
    }
    const B = BABYLON;
    const canvas = byId("world");
    const engine = new B.Engine(canvas, true, { preserveDrawingBuffer: true, stencil: true });
    const scene = new B.Scene(engine);
    scene.clearColor = B.Color4.FromHexString("#141b24ff");
    scene.ambientColor = new B.Color3(.43,.47,.53);
    const camera = new B.ArcRotateCamera("isometric", -Math.PI / 4, Math.PI / 3.25,
      13, new B.Vector3(0,.9,0), scene);
    camera.mode = B.Camera.ORTHOGRAPHIC_CAMERA;
    camera.lowerBetaLimit = .45; camera.upperBetaLimit = 1.37;
    camera.lowerRadiusLimit = 6; camera.upperRadiusLimit = 23;
    camera.wheelPrecision = 60;
    camera.panningSensibility = 0;
    camera.attachControl(canvas, true);
    scene.activeCamera = camera;
    const sun = new B.DirectionalLight("sun", new B.Vector3(-.6,-1,-.5), scene);
    sun.position = new B.Vector3(9,13,7); sun.intensity = 1.8;
    const sky = new B.HemisphericLight("ambient", new B.Vector3(0,1,0), scene);
    sky.intensity = .85;
    sky.groundColor = new B.Color3(.28,.31,.32);
    const ground = B.MeshBuilder.CreateGround("terrain", { width: 32, height: 32 }, scene);
    const groundMat = new B.StandardMaterial("groundMaterial", scene);
    groundMat.diffuseColor = new B.Color3(.23,.30,.27);
    groundMat.specularColor = B.Color3.Black();
    ground.material = groundMat;
    ground.receiveShadows = true;
    const lines = [];
    for (let i = -16; i <= 16; i++) {
      lines.push([new B.Vector3(-16,.009,i),new B.Vector3(16,.009,i)]);
      lines.push([new B.Vector3(i,.009,-16),new B.Vector3(i,.009,16)]);
    }
    const grid = B.MeshBuilder.CreateLineSystem("terrainGrid", { lines }, scene);
    grid.color = new B.Color3(.33,.41,.36);
    grid.alpha = .52;
    const shadow = new B.ShadowGenerator(1024,sun);
    shadow.useBlurExponentialShadowMap = true;
    shadow.blurKernel = 12;
    function decorateStone(x,z,r) {
      const stone = B.MeshBuilder.CreateSphere("stone", { diameter: 1, segments: 6 },scene);
      stone.position = new B.Vector3(x,r*.33,z);
      stone.scaling = new B.Vector3(r*1.2,r*.52,r*.8);
      const mat = new B.StandardMaterial("stoneGray",scene);
      mat.diffuseColor = new B.Color3(.36,.42,.40);
      mat.specularColor = B.Color3.Black();
      stone.material=mat;
      stone.receiveShadows = true;
    }
    [[-6,-4,.7],[6,4,.5],[-4,7,.8],[7,-6,.65],[-8,5,.5],[3,9,.45]]
      .forEach(p => decorateStone(...p));
    const markers = [
      [[-2.6,0,0],[-1.3,0,0]],[[1.3,0,0],[2.6,0,0]],
      [[0,0,-2.6],[0,0,-1.3]],[[0,0,1.3],[0,0,2.6]]
    ];
    const accent = B.MeshBuilder.CreateLineSystem("spawnMarks",{
      lines:markers.map(pair=>pair.map(v=>new B.Vector3(v[0],.022,v[2])))
    },scene);
    accent.color = new B.Color3(.83,.65,.35);
    state.scene=scene;state.engine=engine;state.camera=camera;
    state.sun=shadow;
    setIsometricCamera();
    engine.runRenderLoop(() => {
      update(engine.getDeltaTime()/1000);
      scene.render();
    });
    window.addEventListener("resize",()=>engine.resize());
    state.ready=true;
    return true;
  }

  function setIsometricCamera() {
    if (!state.camera || !state.engine) return;
    const camera=state.camera;
    const size=state.engine.getRenderWidth()/Math.max(1,state.engine.getRenderHeight());
    camera.alpha=-Math.PI/4;
    camera.beta=Math.PI/3.25;
    // A narrower screen needs more headroom above the character and its touch HUD.
    camera.radius=window.matchMedia('(max-width:520px)').matches?10.5:13;
    camera.orthoTop=2.7;
    camera.orthoBottom=-2.7;
    camera.orthoLeft=-2.7*size;
    camera.orthoRight=2.7*size;
    const p=state.character?.position;
    camera.setTarget(new BABYLON.Vector3(p?.x||0,.85,p?.z||0));
    state.follow=true;
    byId("cameraMode").textContent="ISO · SUIVI";
  }

  function renderIdleOptions() {
    const select=byId("idleSelect");
    const old=select.value;
    select.replaceChildren();
    const labels={Idle:"Repos debout",Idle_Relaxed:"Repos détendu",Idle_Wipe:"Essuie sa sueur",Idle_Magic:"Joue avec la magie"};
    for(const group of state.idleChoices) {
      const stem=group.name.split("_Mixamo")[0];
      const opt=document.createElement("option");
      opt.value=group.name;opt.textContent=labels[stem]||stem.replaceAll("_"," ");
      select.append(opt);
    }
    if(state.cast) {
      const opt=document.createElement("option");
      opt.value=state.cast.name;
      opt.textContent="✦ Lancer une boule de feu (une fois)";
      select.append(opt);
    }
    select.disabled=!state.idleChoices.length;
    const candidate=state.idleChoices.find(group=>group.name===old)
      ||state.idleChoices.find(group=>group.name.startsWith("Idle_Mixamo"))||state.idleChoices[0];
    state.idle=candidate||null;
    if(candidate) select.value=candidate.name;
  }

  function updateSprintButtons() {
    document.querySelectorAll('[data-command="sprint"]').forEach(btn=>{
      btn.setAttribute("aria-pressed",String(state.sprintLatched));
      btn.classList.toggle("active",state.sprintLatched);
    });
  }

  function lookForAnimations(groups) {
    state.animGroups=groups;
    const isToken=(name,terms)=>new RegExp("(?:^|[_ -])("+terms+")(?:$|[_ -])","i").test(name);
    state.walk=groups.find(x=>isToken(x.name,"walk|walking|marche"))||null;
    state.run=groups.find(x=>isToken(x.name,"run|running|course"))||null;
    state.idleChoices=groups.filter(x=>isToken(x.name,"idle|rest"));
    state.cast=groups.find(x=>/^Cast[_ -]/i.test(x.name))||null;
    state.attack=groups.find(x=>isToken(x.name,"attack|axe|chop|strike|melee|swing"))||null;
    renderIdleOptions();
    if(!state.attack && groups.length===1 && !state.walk && !state.run && !state.idle) state.attack=groups[0];
    for (const group of groups)group.stop();
    state.currentMotion=null;
    if(state.idle){
      // First evaluation must not blend in from the imported T-pose.
      state.idle.start(true,1,state.idle.from,state.idle.to);
      state.idle.goToFrame(state.idle.from);
      state.currentMotion=state.idle;
    } else if(state.attack)restPose();
    // From this fully initialized pose onward, blend naturally when a new
    // movement or gesture starts instead of snapping back to a rig rest pose.
    for(const group of groups)for(const track of group.targetedAnimations||[]){
      track.animation.enableBlending=true;
      track.animation.blendingSpeed=.15;
    }
    text("activeMotionMetric",state.currentMotion?.name||"Aucune animation");
    const gait=state.walk&&state.run?"Marche ET course réelles détectées":
      state.walk?"Marche réelle détectée":state.run?"Course réelle détectée":"Marche absente : déplacements seulement";
    text("walkMetric",gait);
    text("clipMetric",groups.map(x=>x.name).join(" · ")||"Aucune animation");
    byId("attackButton").disabled=!state.attack;
    byId("castButton").disabled=!state.cast;
    document.querySelectorAll('[data-command="cast"]').forEach(btn=>btn.disabled=!state.cast);
  }

  function restPose() {
    const group=state.attack;
    if (!group) return;
    group.stop();
    group.start(false,1,group.from,group.to);
    group.pause();
    group.goToFrame(group.from);
  }

  function clearWeapon() {
    if (state.weaponImport) {
      for (const item of [...(state.weaponImport.meshes||[]), ...(state.weaponImport.transformNodes||[])]) {
        if (!item.isDisposed()) item.dispose(false,true);
      }
    }
    if (state.weaponAnchor && !state.weaponAnchor.isDisposed()) state.weaponAnchor.dispose(false,true);
    state.weaponImport=null;
    state.weaponAnchor=null;
    text("weaponMetric","—");
    byId("world").dataset.weaponGrip="none";
    byId("world").dataset.weaponGripHeadRatio="";
    byId("world").dataset.weaponGripScale="";
    byId("world").dataset.weaponScaleOrigin="";
    byId("world").dataset.equipmentAction="";
    byId("world").dataset.equipmentReady="";
    byId("world").dataset.equipmentMissing="";
  }

  // Vision decides the whole pose/scale/hand specification offline; geometry fits GLB.
  // Recompute the shaft/head frame from Babylon's actual imported vertices;
  // GLB axes cannot be taken from the original picture or hard-coded.
  function importedPropPoints(meshes) {
    const B=BABYLON,points=[];
    for(const mesh of meshes) {
      if(!mesh.getTotalVertices?.())continue;
      const positions=mesh.getVerticesData(B.VertexBuffer.PositionKind);
      if(!positions)continue;
      const matrix=mesh.computeWorldMatrix(true);
      const stride=Math.max(1,Math.ceil(positions.length/3/24000));
      for(let i=0;i<positions.length;i+=3*stride) {
        const p=B.Vector3.TransformCoordinates(
          new B.Vector3(positions[i],positions[i+1],positions[i+2]),matrix);
        points.push([p.x,p.y,p.z]);
      }
    }
    return points;
  }

  function normalizedNodeName(node) {
    return (node?.name||"").toLowerCase().replace(/[^a-z0-9]/g,"");
  }

  function findGripAnatomy(imported, side) {
    const nodes=[...(imported.transformNodes||[]),...(imported.meshes||[])];
    const stem=side==="left"?"lefthand":"righthand";
    const hand=nodes.find(node=>normalizedNodeName(node).endsWith(stem));
    if(!hand)return null;
    const forearm=nodes.find(node=>normalizedNodeName(node).endsWith(side+"forearm")||
      normalizedNodeName(node).endsWith(side+"lowerarm"))||hand.parent;
    const middle=nodes.find(node=>normalizedNodeName(node).includes(stem+"middle1"))||
      nodes.find(node=>normalizedNodeName(node).includes(stem+"index1"));
    return {hand,forearm,middle};
  }

  function buildGripRotation(prop, wantedShaft, wantedBlade) {
    const B=BABYLON;
    const gram=(shaft,blade)=>{
      const y=shaft.normalize();
      const x=blade.subtract(y.scale(B.Vector3.Dot(y,blade))).normalize();
      const z=B.Vector3.Cross(x,y).normalize();
      return {x,y,z};
    };
    const source=gram(new B.Vector3(...prop.shaft),new B.Vector3(...prop.blade));
    const target=gram(wantedShaft,wantedBlade);
    const from=B.Matrix.Identity(),to=B.Matrix.Identity();
    B.Matrix.FromXYZAxesToRef(source.x,source.y,source.z,from);
    B.Matrix.FromXYZAxesToRef(target.x,target.y,target.z,to);
    const rotation=to.multiply(B.Matrix.Transpose(from));
    return B.Quaternion.FromRotationMatrix(rotation).normalize();
  }

  async function tryEquipProp(imported,token,planUrl) {
    const B=BABYLON;
    let prop,anchor;
    try {
      const response=await fetch(assetUrl(planUrl),{cache:"no-store"});
      if(!response.ok) {
        text("weaponMetric","Analyse visuelle de la prise en attente · pas de fixation arbitraire");
        return;
      }
      const vision=await response.json();
      const spec=vision?.specifications;
      const gripFraction=vision?.derived_image_geometry?.grip_fraction_from_butt;
      const side=spec?.dominant_hand==="left"?"left":"right";
      if(![2,3].includes(vision.schema)||spec?.grip_geometry!=="shaft"||
        spec.hold_mode==="unsupported")throw Error("Plan visuel non compatible avec une prise sur manche");
      if(!Number.isFinite(gripFraction)||gripFraction<=.03||gripFraction>=.65||
        !Number.isFinite(spec.length_relative_character_height)||
        spec.length_relative_character_height<.13||spec.length_relative_character_height>1.85||
        !Number.isFinite(spec.palm_from_wrist)||spec.palm_from_wrist<0||spec.palm_from_wrist>1)
        throw Error("Dimensions ou repères du plan vision invalides");
      // v3 carries the generation brief fingerprint and independent evidence
      // from the character source. Refuse incompatible/unreviewed scales.
      if(vision.schema===3) {
        const evidence=vision.scale_observation;
        const observed=evidence?.character_image_size_ratio;
        if(!vision.source_provenance?.generation_brief_sha256 ||
          evidence?.character_image_shows_full_object!==true ||
          !Number.isFinite(observed) ||
          Math.abs(observed-spec.length_relative_character_height)>.15 ||
          Math.abs(observed-spec.length_relative_character_height)/observed>.20)
          throw Error("Echelle sans preuve sur le concept original");
      }
      const propPath=vision.inputs?.object_glb;
      if(!/^assets\/experiments\/props\/[a-z0-9_/-]+\.glb$/.test(propPath||""))
        throw Error("Chemin de GLB non autorisé");
      const anatomy=findGripAnatomy(imported,side);
      if(!anatomy)throw Error("Main "+side+" introuvable dans le rig");
      if(!window.WCWeaponGrip?.fitGrip)throw Error("Analyseur géométrique manquant");
      prop=await B.SceneLoader.ImportMeshAsync(null,"",assetUrl(propPath),state.scene);
      if(token!==state.pendingLoad) {
        for(const node of [...prop.meshes,...prop.transformNodes])
          if(!node.isDisposed())node.dispose(false,true);
        return;
      }
      const points=importedPropPoints(prop.meshes||[]);
      const frame=window.WCWeaponGrip.fitGrip(points,gripFraction,
        spec.object_kind);
      const {hand,forearm,middle}=anatomy;
      hand.computeWorldMatrix(true);
      const handPosition=hand.getAbsolutePosition();
      const elbowPosition=forearm?.getAbsolutePosition?.()||handPosition.add(new B.Vector3(0,.3,0));
      const toElbow=elbowPosition.subtract(handPosition);
      const pivotForward=B.Vector3.TransformNormal(B.Axis.Z,
        state.character.getWorldMatrix()).normalize();
      const pivotRight=B.Vector3.TransformNormal(B.Axis.X,
        state.character.getWorldMatrix()).normalize();
      const up=B.Axis.Y;
      const headDirections={
        toward_elbow:toElbow, toward_fingers:toElbow.negate(),
        forward:pivotForward,backward:pivotForward.negate(),
        up,down:up.negate()
      };
      const strikeDirections={
        forward:pivotForward,backward:pivotForward.negate(),
        outward:side==="right"?pivotRight:pivotRight.negate(),
        inward:side==="right"?pivotRight.negate():pivotRight
      };
      const shaftWorld=headDirections[spec.head_direction]?.clone();
      if(!shaftWorld||shaftWorld.length()<.001)
        throw Error("Orientation de manche vision sans repère anatomique");
      shaftWorld.normalize();
      let bladeWorld=strikeDirections[spec.edge_direction]?.clone();
      if(!bladeWorld)throw Error("Orientation du tranchant vision absente");
      bladeWorld.subtractInPlace(shaftWorld.scale(B.Vector3.Dot(bladeWorld,shaftWorld)));
      if(bladeWorld.length()<.01) {
        // Reject near-collinear directions instead of inventing a new design.
        throw Error("Plan vision incompatible : tranchant parallèle au manche");
      }
      const worldRotation=buildGripRotation(frame,shaftWorld,bladeWorld);
      const parentScale=new B.Vector3(),parentRotation=new B.Quaternion();
      hand.getWorldMatrix().decompose(parentScale,parentRotation);
      const unitScale=(Math.abs(parentScale.x)+Math.abs(parentScale.y)+Math.abs(parentScale.z))/3;
      if(!Number.isFinite(unitScale)||unitScale<1e-7)throw Error("Échelle de main invalide");
      // Only the grip is parented to the animated hand. The weapon shaft
      // extends toward the forearm and the cutting edge toward the avatar's front.
      const desiredLength=1.9*spec.length_relative_character_height;
      anchor=new B.TransformNode("wc-auto-grip-"+side+"-hand",state.scene);
      anchor.parent=hand;
      let palmWorld=handPosition;
      if(middle) {
        const knuckle=middle.getAbsolutePosition();
        if(B.Vector3.Distance(handPosition,knuckle)<.25)
          palmWorld=B.Vector3.Lerp(handPosition,knuckle,spec.palm_from_wrist);
      }
      anchor.position.copyFrom(B.Vector3.TransformCoordinates(
        palmWorld,B.Matrix.Invert(hand.getWorldMatrix())));
      anchor.rotationQuaternion=B.Quaternion.Inverse(parentRotation).multiply(worldRotation);
      anchor.scaling.setAll(desiredLength/(frame.length*unitScale));
      const offset=new B.TransformNode("wc-weapon-local-grip-origin",state.scene);
      offset.parent=anchor;
      offset.position=new B.Vector3(...frame.grip).negate();
      const roots=[...prop.meshes,...prop.transformNodes].filter(node=>!node.parent);
      for(const node of roots)node.parent=offset;
      state.weaponImport=prop;
      state.weaponAnchor=anchor;
      text("weaponMetric","Prise auto · Gemini Vision + GLB · main "+side+
        (spec.hold_mode==="two_hands"?" (seconde main non pilotée)":"")+
        " · objet/hauteur "+spec.length_relative_character_height.toFixed(2));
      byId("world").dataset.weaponGrip="vision-plan-geometry";
      byId("world").dataset.weaponGripScale=spec.length_relative_character_height.toFixed(3);
      byId("world").dataset.weaponScaleOrigin=vision.schema===3
        ? "provenance-and-character-image" : "legacy-vision-only";
      byId("world").dataset.weaponGripHeadRatio=frame.headWidthRatio.toFixed(3);
      // Enforce genuine equipment-specific motions once the prop is fitted.
      // A bow must never inherit a generic axe animation by default.
      const policy=window.WCEquipmentActions?.resolve(spec,state.animGroups);
      if(policy){
        state.attack=policy.ready
          ? state.animGroups.find(group=>group.name===policy.motion)||null : null;
        byId("attackButton").disabled=!state.attack;
        document.querySelectorAll('[data-command="attack"]').forEach(btn=>
          btn.disabled=!state.attack);
        byId("world").dataset.equipmentAction=policy.action||"unknown";
        byId("world").dataset.equipmentReady=String(policy.ready);
        byId("world").dataset.equipmentMissing=policy.missing.join(",");
        if(!policy.ready){
          text("weaponMetric","Objet chargé ; geste indisponible : "+policy.missing.join(", "));
        }
      }
    }catch(err){
      if(prop)for(const node of [...prop.meshes,...prop.transformNodes])
        if(!node.isDisposed())node.dispose(false,true);
      if(anchor&&!anchor.isDisposed())anchor.dispose(false,true);
      text("weaponMetric","Prise refusée : "+String(err.message||err).slice(0,96));
      console.warn("Generic weapon grip analysis failed:",err);
    }
  }

  function removeImported() {
    state.actionSerial++;
    cancelPoseReturn();
    clearWeapon();
    if (!state.imported) return;
    for (const a of state.imported.animationGroups || []) { a.stop();a.dispose(); }
    if (state.character) state.character.dispose(false,true);
    for (const node of [...(state.imported.meshes||[]),...(state.imported.transformNodes||[])]) {
      if (!node.isDisposed()) node.dispose(false,true);
    }
    for (const sk of state.imported.skeletons || []) sk.dispose();
    state.imported=null;state.character=null;state.animGroups=[];state.walk=null;state.run=null;state.idle=null;state.idleChoices=[];state.attack=null;state.cast=null;state.currentMotion=null;
    state.attacking=false;state.castPending=null;state.poseReturns=0;
    byId("world").dataset.poseReturns="0";
    for(const fireball of state.fireballs){fireball.mesh.dispose();fireball.material.dispose();}
    state.fireballs=[];
  }

  async function loadModel(url,fileObject=null) {
    if (!state.ready) return;
    const token=++state.pendingLoad;
    setOverlay("Chargement du personnage 3D…", true);
    setStatus("Lecture du fichier GLB", "normal");
    try {
      let imported;
      if (fileObject) {
        const blobUrl=URL.createObjectURL(fileObject);
        try {
          imported=await BABYLON.SceneLoader.ImportMeshAsync(null,"",blobUrl,state.scene,null,".glb");
        } finally { URL.revokeObjectURL(blobUrl); }
      } else {
        imported=await BABYLON.SceneLoader.ImportMeshAsync(null,"",assetUrl(url),state.scene);
      }
      if (token!==state.pendingLoad) {
        imported.meshes.forEach(m=>m.dispose(false,true));
        return;
      }
      removeImported();
      const pivot=new BABYLON.TransformNode("wc-character-pivot",state.scene);
      pivot.setEnabled(false); // Never expose the imported T-pose during initialization.
      // Hunyuan / Uthana GLBs can have a 0.01-scale Armature rotated 90 degrees.
      // Normalizing raw local mesh bounds leaves the real on-screen model tiny.
      const content=new BABYLON.TransformNode("wc-character-content",state.scene);
      content.parent=pivot;
      const allNodes=[...(imported.meshes||[]),...(imported.transformNodes||[])];
      for (const node of allNodes) if (!node.parent) node.parent=content;
      const vertices=imported.meshes.filter(m=>m.getTotalVertices && m.getTotalVertices()>0);
      const bounds=()=>{
        const min=new BABYLON.Vector3(Infinity,Infinity,Infinity);
        const max=new BABYLON.Vector3(-Infinity,-Infinity,-Infinity);
        for (const m of vertices) {
          m.computeWorldMatrix(true);
          const box=m.getBoundingInfo().boundingBox;
          min.minimizeInPlace(box.minimumWorld);
          max.maximizeInPlace(box.maximumWorld);
        }
        return {min,max,size:max.subtract(min)};
      };
      if (vertices.length) {
        let b=bounds();
        // Recover a standing up-axis when the imported rig lies along ground Z.
        if(b.size.z>Math.max(.0001,b.size.y)*1.8 && b.size.y<Math.max(b.size.x,b.size.z)*.48) {
          content.rotation.x=-Math.PI/2;
        }
        b=bounds();
        const height=Math.max(.00001,b.size.y);
        const normalizer=Math.min(500,Math.max(.01,1.9/height));
        pivot.scaling.setAll(normalizer);
        pivot.position.y=-b.min.y*normalizer;
        for (const m of vertices) {
          if (state.sun && m.getTotalVertices()<60000) state.sun.addShadowCaster(m);
        }
        text("modelMetric",vertices.length+" mesh · échelle ×"+normalizer.toFixed(1));
      }
      pivot.position.x=0;pivot.position.z=0;
      pivot.rotation.y=0;
      state.character=pivot;
      state.imported=imported;
      lookForAnimations(imported.animationGroups||[]);
      pivot.setEnabled(true);
      const propPlan=state.selected?.props?.[0]?.gripPlan;
      if (url && propPlan && imported.skeletons?.length)
        void tryEquipProp(imported,token,propPlan);
      setIsometricCamera();
      text("modelMetric",vertices.length+" mesh · "+(imported.skeletons?.length||0)+" rig");
      setStatus("Prêt · WASD pour se déplacer", "success");
      setOverlay("",false);
      byId("world").focus();
    } catch(err) {
      setStatus("Échec de chargement GLB", "error");
      setOverlay("Impossible de lire le GLB. Utilise le serveur local ou importe un fichier.",true);
      console.error("WarConquer GLB import failed:",err);
      text("walkMetric","Chargement impossible : "+String(err.message||err).slice(0,120));
    }
  }

  // A gesture may end in a completely different stance from the one in which
  // it started. Remember the *actual* node-local pose, not a presumed T-pose or
  // a hard-coded idle frame. This works with any imported humanoid animation.
  function snapshotPose(group) {
    const props=new Map();
    const supported=new Set(["rotationQuaternion","position","scaling","rotation"]);
    for(const entry of group.targetedAnimations||[]) {
      const target=entry.target;
      const path=entry.animation?.targetProperty;
      if(!supported.has(path)||!target||!target[path]?.clone)continue;
      if(!props.has(target))props.set(target,new Map());
      props.get(target).set(path,target[path].clone());
    }
    return [...props].map(([target,values])=>({target,values}));
  }

  function cancelPoseReturn() {
    const transition=state.returningPose;
    if(!transition)return;
    state.returningPose=null;
    for(const a of transition.animatables)a.stop();
  }

  function returnToSavedPose(snapshot,actionToken) {
    if(actionToken!==state.actionSerial || !state.character)return;
    // A player already running should never be interrupted by pose restoration.
    if(state.moving || !snapshot.length)return;
    const B=BABYLON;
    const transition={animatables:[],remaining:0};
    const targets=[];
    for(const {target,values} of snapshot) {
      if(target.isDisposed?.())continue;
      const animations=[];
      for(const [path,desired] of values) {
        const current=target[path];
        if(!current?.clone)continue;
        const kind=path==="rotationQuaternion"?B.Animation.ANIMATIONTYPE_QUATERNION:B.Animation.ANIMATIONTYPE_VECTOR3;
        const animation=new B.Animation("wc-pose-return-"+path,path,30,kind,B.Animation.ANIMATIONLOOPMODE_CONSTANT);
        animation.setKeys([{frame:0,value:current.clone()},{frame:12,value:desired.clone()}]);
        const ease=new B.CubicEase();
        ease.setEasingMode(B.EasingFunction.EASINGMODE_EASEINOUT);
        animation.setEasingFunction(ease);
        animations.push(animation);
      }
      if(animations.length)targets.push({target,animations});
    }
    if(!targets.length)return;
    state.returningPose=transition;
    transition.remaining=targets.length;
    for(const {target,animations} of targets) {
      const a=state.scene.beginDirectAnimation(target,animations,0,12,false,1,()=>{
        if(state.returningPose!==transition)return;
        if(--transition.remaining!==0)return;
        state.returningPose=null;
        state.poseReturns++;
        byId("world").dataset.poseReturns=String(state.poseReturns);
        setStatus("Prêt · pose de départ retrouvée","success");
        // update() restarts the selected idle, blended from the recovered pose.
      });
      transition.animatables.push(a);
    }
  }

  function playAction(group,message) {
    if(!group||state.attacking)return false;
    cancelPoseReturn();
    const before=snapshotPose(group);
    const actionToken=++state.actionSerial;
    if(state.currentMotion)state.currentMotion.stop();
    state.currentMotion=null;state.attacking=true;
    group.stop();group.start(false,1,group.from,group.to);
    text("activeMotionMetric",group.name);
    group.onAnimationGroupEndObservable.addOnce(()=>{
      if(actionToken!==state.actionSerial)return;
      state.attacking=false;state.currentMotion=null;
      returnToSavedPose(before,actionToken);
    });
    setStatus(message,"normal");
    return true;
  }

  function attack(){playAction(state.attack,"Attaque du guerrier");}

  function castFireball(){
    if(playAction(state.cast,"Sort de feu · incantation")){
      state.castPending={time:0,launchAt:.55};
    }
  }

  function spawnFireball(){
    if(!state.character)return;
    const B=BABYLON;
    const mesh=B.MeshBuilder.CreateSphere("wc-fireball",{diameter:.27,segments:12},state.scene);
    const material=new B.StandardMaterial("wc-fireball-glow",state.scene);
    material.disableLighting=true;
    material.emissiveColor=new B.Color3(1,.36,.055);
    material.diffuseColor=new B.Color3(1,.26,.08);
    mesh.material=material;
    const angle=state.character.rotation.y;
    const direction=new B.Vector3(Math.sin(angle),.08,Math.cos(angle)).normalize();
    mesh.position.copyFrom(state.character.position);
    mesh.position.addInPlace(new B.Vector3(0,1.26,0));
    mesh.position.addInPlace(direction.scale(.45));
    state.fireballs.push({mesh,material,direction,age:0,duration:1.1});
  }

  function updateFireballs(dt){
    if(state.castPending){
      state.castPending.time+=dt;
      if(state.castPending.time>=state.castPending.launchAt){
        state.castPending=null;
        spawnFireball();
      }
    }
    for(let i=state.fireballs.length-1;i>=0;i--){
      const shot=state.fireballs[i];
      shot.age+=dt;
      shot.mesh.position.addInPlace(shot.direction.scale(5.2*dt));
      const fraction=Math.min(1,shot.age/shot.duration);
      shot.mesh.scaling.setAll(1+.6*fraction);
      shot.material.alpha=1-fraction;
      if(fraction>=1){
        shot.mesh.dispose();shot.material.dispose();state.fireballs.splice(i,1);
      }
    }
  }

  function update(delta) {
    const B=BABYLON;
    const dt=Math.min(.055,Math.max(0,delta||0));
    // An orthographic ArcRotateCamera changes radius on wheel; update the
    // orthographic extents so wheel zoom actually changes visible scale.
    if (state.camera && state.engine) {
      const half=2.7*state.camera.radius/13;
      const aspect=state.engine.getRenderWidth()/Math.max(1,state.engine.getRenderHeight());
      state.camera.orthoTop=half;
      state.camera.orthoBottom=-half;
      state.camera.orthoLeft=-half*aspect;
      state.camera.orthoRight=half*aspect;
    }
    const pressed=key=>state.input.has(key)||state.touch.has(key);
    updateFireballs(dt);
    const vertical=(pressed("w")||pressed("arrowup")?1:0)-(pressed("s")||pressed("arrowdown")?1:0);
    const horizontal=(pressed("d")||pressed("arrowright")?1:0)-(pressed("a")||pressed("arrowleft")?1:0);
    const moving=!!(vertical||horizontal);
    if(state.character) {
      if (moving) {
        const cam=state.camera;
        const forward=cam.getTarget().subtract(cam.position);forward.y=0;forward.normalize();
        const right=B.Vector3.Cross(forward,B.Axis.Y).normalize();
        const move=forward.scale(vertical).add(right.scale(horizontal)).normalize();
        const fast=(state.input.has("shift")||state.sprintLatched)?1.75:1;
        const speed=state.speed*fast;
        state.character.position.x=B.Scalar.Clamp(state.character.position.x+move.x*speed*dt,-14,14);
        state.character.position.z=B.Scalar.Clamp(state.character.position.z+move.z*speed*dt,-14,14);
        const angle=Math.atan2(move.x,move.z)+state.facingBias;
        let diff=((angle-state.character.rotation.y+Math.PI*3)%(Math.PI*2))-Math.PI;
        state.character.rotation.y+=diff*Math.min(1,dt*12);
        if(state.follow) {
          const target=state.camera.getTarget().clone();
          const dest=new B.Vector3(state.character.position.x,.85,state.character.position.z);
          state.camera.setTarget(B.Vector3.Lerp(target,dest,Math.min(1,dt*6)));
        }
      }
      // Motion input takes priority over returning to a captured action pose.
      if(moving && state.returningPose)cancelPoseReturn();
      if(!state.attacking && !state.returningPose) {
        const fast=state.input.has("shift")||state.sprintLatched;
        const next= moving ? (fast ? (state.run||state.walk) : (state.walk||state.run)) : state.idle;
        if(next!==state.currentMotion) {
          if(state.currentMotion) state.currentMotion.stop();
          if(next) next.start(true,1,next.from,next.to);
          else if(state.attack) restPose();
          state.currentMotion=next||null;
          text("activeMotionMetric",next?.name||"Aucune animation");
        }
      }
      if(moving!==state.moving) {
        state.moving=moving;
        text("movementMetric",moving?"EN DÉPLACEMENT":"IMMOBILE");
      }
      text("positionMetric","X "+state.character.position.x.toFixed(1)+" · Z "+state.character.position.z.toFixed(1));
    }
    text("fpsMetric",state.engine?Math.round(state.engine.getFps())+" FPS":"—");
  }

  function bindUI() {
    byId("modelSelect").addEventListener("change",event=>{
      selectByPath(event.target.value);
      loadModel(event.target.value);
    });
    byId("openFile").addEventListener("change",event=>{
      const f=event.target.files[0];
      if(f){text("unitName",f.name);loadModel(null,f);}
    });
    byId("attackButton").addEventListener("click",attack);
    byId("castButton").addEventListener("click",castFireball);
    byId("idleSelect").addEventListener("change",event=>{
      const selected=state.idleChoices.find(x=>x.name===event.target.value);
      if(selected){
        state.idle=selected;
        if(!state.moving&&!state.attacking){
          if(state.currentMotion)state.currentMotion.stop();
          state.idle.start(true,1,state.idle.from,state.idle.to);
          state.currentMotion=state.idle;
          text("activeMotionMetric",state.idle.name);
        }
      } else if(state.cast&&event.target.value===state.cast.name){
        castFireball();
        event.target.value=state.idle?.name||"";
      }
    });
    document.querySelectorAll("[data-command]").forEach(btn=>btn.addEventListener("click",()=>{
      if(btn.dataset.command==="sprint"){
        state.sprintLatched=!state.sprintLatched;updateSprintButtons();
      } else if(btn.dataset.command==="attack")attack();
      else if(btn.dataset.command==="cast")castFireball();
      else if(btn.dataset.command==="reset")byId("resetButton").click();
    }));
    byId("resetButton").addEventListener("click",()=>{
      state.actionSerial++;
      cancelPoseReturn();
      state.attacking=false;
      if(state.currentMotion)state.currentMotion.stop();
      for(const group of [state.attack,state.cast])group?.stop();
      if(state.character) {
        state.character.position.x=0;state.character.position.z=0;
        state.character.rotation.y=0;
        if(state.currentMotion)state.currentMotion.stop();
        state.currentMotion=null;
        if(state.idle){state.idle.start(true,1,state.idle.from,state.idle.to);state.currentMotion=state.idle;}
        else if(state.attack)restPose();
        text("activeMotionMetric",state.currentMotion?.name||"Aucune animation");
      }
      setIsometricCamera();
      byId("world").focus();
    });
    byId("cameraButton").addEventListener("click",setIsometricCamera);
    byId("turnButton").addEventListener("click",()=>{
      state.facingBias+=Math.PI/2;
      if(state.character)state.character.rotation.y+=Math.PI/2;
      byId("world").focus();
    });
    byId("followButton").addEventListener("click",()=>{
      state.follow=!state.follow;
      byId("cameraMode").textContent=state.follow?"ISO · SUIVI":"CAMÉRA LIBRE";
      byId("world").focus();
    });
    const down=(event)=>{
      if(/^(input|select|textarea)$/i.test(event.target.tagName))return;
      const k=event.key.toLowerCase();
      if("wasd".includes(k)&&k.length===1 || k.startsWith("arrow") || k==="shift") {
        state.input.add(k);event.preventDefault();
      } else if(k===" "){event.preventDefault();attack();}
      else if(k==="f"){event.preventDefault();castFireball();}
      else if(k==="r")byId("resetButton").click();
    };
    const up=event=>state.input.delete(event.key.toLowerCase());
    window.addEventListener("keydown",down);
    window.addEventListener("keyup",up);
    window.addEventListener("blur",()=>{state.input.clear();state.touch.clear();});
    document.querySelectorAll("[data-move]").forEach(btn=>{
      const k=btn.dataset.move;
      const release=event=>{state.touch.delete(k);btn.classList.remove("active");
        if(event&&btn.hasPointerCapture?.(event.pointerId))btn.releasePointerCapture(event.pointerId);};
      btn.addEventListener("pointerdown",event=>{
        event.preventDefault();btn.setPointerCapture(event.pointerId);
        state.touch.add(k);btn.classList.add("active");
      });
      for(const name of ["pointerup","pointercancel","lostpointercapture"])btn.addEventListener(name,release);
    });
    byId("world").addEventListener("dragover",event=>event.preventDefault());
    byId("world").addEventListener("drop",event=>{
      event.preventDefault();
      const file=Array.from(event.dataTransfer.files||[]).find(f=>f.name.toLowerCase().endsWith(".glb"));
      if(file){text("unitName",file.name);loadModel(null,file);}
    });
  }

  async function boot() {
    bindUI();
    await fetchCatalog();
    if (createWorld()) {
      const selected=byId("modelSelect").value;
      if(location.protocol==="file:") {
        setOverlay("Ouvre avec le serveur local pour charger les modèles automatiquement, ou choisis un GLB.",false);
        setStatus("Mode fichier : importer un GLB avec le bouton", "warning");
      } else if(selected) {
        await loadModel(selected);
      }
    }
  }
  window.addEventListener("DOMContentLoaded",boot);
})();

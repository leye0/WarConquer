/* WarConquer Character Lab — tiny, dependency-free frontend (Babylon runtime from CDN).
 * Model files and asset metadata stay in the repository; no generative API calls.
 */
(() => {
  "use strict";
  const byId = id => document.getElementById(id);
  const FALLBACK = {
    schema: 1,
    characters: [{
      id: "marches_hache", pose: "tpose-v2", name: "Guerrier à la hache · Marches",
      original: "assets/concepts/marches/units/hache.png",
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
    engine: null, character: null, imported: null, attack: null, walk: null,
    animGroups: [], loadedAsset: null, attacking: false, moving: false,
    ready: false, input: new Set(), touch: new Set(), follow: true,
    speed: 2.7, scale: 1, facingBias: 0, pendingLoad: 0,
    importUrl: null
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
      img.src = item.path; img.alt = item.name; img.loading = "lazy";
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
        text("jointMetric", (c.metrics.joints || "—") + " os");
        renderSources();
        return;
      }
    }
  }

  async function fetchCatalog() {
    try {
      const response = await fetch("/api/character-lab", { cache: "no-store" });
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
    camera.radius=13;
    camera.orthoTop=6.4;
    camera.orthoBottom=-6.4;
    camera.orthoLeft=-6.4*size;
    camera.orthoRight=6.4*size;
    const p=state.character?.position;
    camera.setTarget(new BABYLON.Vector3(p?.x||0,.85,p?.z||0));
    state.follow=true;
    byId("cameraMode").textContent="ISO · SUIVI";
  }

  function lookForAnimations(groups) {
    state.animGroups=groups;
    state.walk=groups.find(x=>/walk|marche|run/i.test(x.name)) || null;
    state.attack=groups.find(x=>/axe|attack|chop|swing|strike/i.test(x.name)) || null;
    if (!state.attack && groups.length===1 && !state.walk) state.attack=groups[0];
    for (const group of groups) group.stop();
    if (state.attack) restPose();
    const message=state.walk ? "Marche squelettique détectée" :
      "Marche non générée : déplacement spatial seulement";
    text("walkMetric",message);
    text("clipMetric",groups.map(x=>x.name).join(" · ") || "Aucune animation");
    byId("attackButton").disabled=!state.attack;
  }

  function restPose() {
    const group=state.attack;
    if (!group) return;
    group.stop();
    group.start(false,1,group.from,group.to);
    group.pause();
    group.goToFrame(group.from);
  }

  function removeImported() {
    if (!state.imported) return;
    for (const a of state.imported.animationGroups || []) { a.stop();a.dispose(); }
    if (state.character) state.character.dispose(false,true);
    for (const node of [...(state.imported.meshes||[]),...(state.imported.transformNodes||[])]) {
      if (!node.isDisposed()) node.dispose(false,true);
    }
    for (const sk of state.imported.skeletons || []) sk.dispose();
    state.imported=null;state.character=null;state.animGroups=[];state.walk=null;state.attack=null;
    state.attacking=false;
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
        imported=await BABYLON.SceneLoader.ImportMeshAsync(null,"",url,state.scene);
      }
      if (token!==state.pendingLoad) {
        imported.meshes.forEach(m=>m.dispose(false,true));
        return;
      }
      removeImported();
      const pivot=new BABYLON.TransformNode("wc-character-pivot",state.scene);
      const allNodes=[...(imported.meshes||[]),...(imported.transformNodes||[])];
      for (const node of allNodes) if (!node.parent) node.parent=pivot;
      const vertices=imported.meshes.filter(m=>m.getTotalVertices && m.getTotalVertices()>0);
      let bottom=0,top=2;
      if (vertices.length) {
        bottom=Infinity;top=-Infinity;
        for (const m of vertices) {
          const info=m.getBoundingInfo().boundingBox;
          bottom=Math.min(bottom,info.minimum.y);
          top=Math.max(top,info.maximum.y);
          if (state.sun && m.getTotalVertices()<60000) state.sun.addShadowCaster(m);
        }
      }
      const height=Math.max(.05,top-bottom);
      const normalizer=Math.min(10,Math.max(.08,1.9/height));
      pivot.scaling.setAll(normalizer);
      pivot.position.y=-bottom*normalizer;
      pivot.position.x=0;pivot.position.z=0;
      pivot.rotation.y=0;
      state.scale=normalizer;
      state.character=pivot;
      state.imported=imported;
      lookForAnimations(imported.animationGroups||[]);
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

  function attack() {
    if (!state.attack || state.attacking) return;
    if (state.walk) state.walk.stop();
    const group=state.attack;
    state.attacking=true;
    group.stop();
    group.start(false,1,group.from,group.to);
    group.onAnimationGroupEndObservable.addOnce(()=>{
      state.attacking=false;
      if (!state.moving) restPose();
    });
    setStatus("Attaque du guerrier", "normal");
  }

  function update(delta) {
    const B=BABYLON;
    const dt=Math.min(.055,Math.max(0,delta||0));
    const pressed=key=>state.input.has(key)||state.touch.has(key);
    const vertical=(pressed("w")||pressed("arrowup")?1:0)-(pressed("s")||pressed("arrowdown")?1:0);
    const horizontal=(pressed("d")||pressed("arrowright")?1:0)-(pressed("a")||pressed("arrowleft")?1:0);
    const moving=!!(vertical||horizontal);
    if(state.character) {
      if (moving) {
        const cam=state.camera;
        const forward=cam.getTarget().subtract(cam.position);forward.y=0;forward.normalize();
        const right=B.Vector3.Cross(forward,B.Axis.Y).normalize();
        const move=forward.scale(vertical).add(right.scale(horizontal)).normalize();
        const fast=state.input.has("shift")?1.75:1;
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
      if(moving!==state.moving) {
        if(state.walk&&!state.attacking) {
          if(moving)state.walk.start(true,1,state.walk.from,state.walk.to);
          else {state.walk.stop();if(state.attack)restPose();}
        }
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
    byId("resetButton").addEventListener("click",()=>{
      if(state.character) {
        state.character.position.x=0;state.character.position.z=0;
        state.character.rotation.y=0;
        if(state.attack)restPose();
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

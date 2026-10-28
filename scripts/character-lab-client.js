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
  let originalUnitCaption="";

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
  function renderModelVersions(preferredUrl=null) {
    const dropdown=byId("modelSelect");
    const char=state.selected;
    dropdown.replaceChildren();
    for(const model of char.models.slice().sort((a,b)=>b.priority-a.priority)){
      const opt=document.createElement("option");
      opt.value=model.url;
      opt.textContent=model.name;
      dropdown.append(opt);
    }
    dropdown.disabled=char.models.length===0;
    if(preferredUrl&&char.models.some(m=>m.url===preferredUrl))dropdown.value=preferredUrl;
    else if(char.models.length)dropdown.value=char.models.slice().sort((a,b)=>b.priority-a.priority)[0].url;
  }

  function showSourceOnly(char) {
    // Never reuse the previous character's imported mesh on unit changes.
    state.pendingLoad++;
    removeImported();
    state.selected=char;
    text("unitName",char.name);
    text("unitCaption","Concept d’origine prêt. Le pipeline indique les étapes manquantes : quatre vues, corps 3D, squelette, arc et gestes de tir.");
    text("attackShortcutLabel","Arc non disponible");
    text("sceneUnitLabel",char.name+" · concept initial");
    document.querySelectorAll('[data-command="attack"]').forEach(btn=>
      btn.textContent=btn.id==="runButton"?"Courir":"🏹 Arc indisponible");
    text("meshMetric","3D non produit");
    text("jointMetric","—");
    text("modelMetric","Concept 2D");
    text("clipMetric","—");
    text("activeMotionMetric","—");
    text("weaponMetric","Arc 3D à générer");
    text("walkMetric","Fiche source prête ; génération 3D non commencée.");
    byId("idleSelect").disabled=true;
    byId("idleSelect").replaceChildren(new Option("Animations non produites",""));
    byId("attackButton").disabled=true;
    byId("castButton").disabled=true;
    document.querySelectorAll('[data-command="attack"],[data-command="cast"]')
      .forEach(button=>button.disabled=true);
    byId("conceptImage").src=assetUrl(char.original);
    byId("conceptImage").alt="Concept 2D original : "+char.name;
    byId("conceptPreview").hidden=false;
    byId("world").dataset.unitId=char.id;
    byId("world").dataset.unitBuildStatus="source_only";
    byId("world").closest(".playbox").dataset.unitState="source-only";
    text("unitBuildStatus","Illustration prête · 3D, rig et animations manquants");
    renderSources();
    setOverlay("",false);
    setStatus("Unité 2D sélectionnée · construction 3D à faire","warning");
  }

  function renderCatalog() {
    const chars=state.catalog.characters;
    const unitSelect=byId("unitSelect");
    unitSelect.replaceChildren();
    if(!chars.length){
      text("unitName","Aucune unité trouvée");
      setStatus("Ajoutez une fiche dans data/units","warning");
      return;
    }
    const names=new Map();
    for(const c of chars)if(!names.has(c.id))names.set(c.id,c);
    for(const c of names.values()){
      const option=document.createElement("option");
      option.value=c.id;
      option.textContent=c.name+(c.models.some(m=>m.kind==="playable")?" · 3D animé":(c.models.length?" · maillage 3D":" · concept 2D"));
      unitSelect.append(option);
    }
    // A URL can select a specific unit for mobile testing or sharing.
    const requested=new URLSearchParams(location.search).get("unit");
    const existing=state.selected?.id;
    const id=[existing,requested,"marches_hache"].find(id=>names.has(id))
      || chars[0].id;
    state.selected=chars.find(c=>c.id===id&&c.models.length)||names.get(id);
    unitSelect.value=id;
    renderModelVersions();
    if(state.selected.models.length){
      selectByPath(byId("modelSelect").value);
    } else {
      showSourceOnly(state.selected);
    }
  }

  function selectByPath(path) {
    for (const c of state.catalog.characters) {
      const model = c.models.find(m => m.url === path);
      if (model) {
        state.selected = c;
        state.loadedAsset = model;
        byId("unitSelect").value=c.id;
        byId("conceptPreview").hidden=true;
        byId("world").closest(".playbox").dataset.unitState="ready";
        byId("world").dataset.unitId=c.id;
        byId("world").dataset.unitBuildStatus=c.buildStatus||"mesh_only";
        text("unitBuildStatus",model.kind==="mesh"
          ? "Maillage 3D disponible · squelette et animations à produire"
          : "Modèle 3D disponible · prêt à tester");
        text("unitName", c.name);
        text("unitCaption",c.id==="couronne_archer"
          ? (model.kind==="mesh"
            ? "Voici le véritable corps 3D généré depuis la fiche originale de l’archer. Le rig, le modèle de l’arc et les animations de tir sont encore à produire."
            : "Archer de la Couronne : modèle 3D généré depuis sa propre fiche.")
          : originalUnitCaption);
        text("attackShortcutLabel",c.id==="couronne_archer"?"Tir à l’arc (en préparation)":"Hache");
        text("sceneUnitLabel",c.name+" · camp d’essai");
        document.querySelectorAll('[data-command="attack"]').forEach(btn=>
          btn.textContent=btn.classList.contains("touch-action")
            ? (c.id==="couronne_archer"?"🏹 Arc":"⚔ Hache") : "Espace");
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
    if (!window.BABYLON || !window.WCArena) {
      setStatus("Le moteur Babylon.js ou l'arène commune n'a pas chargé.", "error");
      setOverlay("Le moteur 3D n'a pas pu être chargé.", true);
      return false;
    }
    const {engine,scene,camera,shadow}=WCArena.create(byId("world"),BABYLON);
    state.scene=scene;state.engine=engine;state.camera=camera;state.sun=shadow;
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
    const p=state.character?.position;
    WCArena.fitCamera(state.camera,state.engine,BABYLON,p,
      window.matchMedia("(max-width:520px)").matches);
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
    byId("world").dataset.weaponLengthCm="";
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

  // Locate vision-annotated GLB vertices in Babylon's *imported* buffers. We
  // intentionally do NOT apply glTF coordinate-system guesses, axis flips,
  // hand-specific offsets, or model-specific Euler rotations. Babylon owns
  // that transform, so source local points are lifted through its matrix.
  function importedPropLandmarks(meshes,plan) {
    const landmarks=plan?.mesh_landmarks;
    if(landmarks?.schema!==1 ||
       landmarks.glb_sha256!==plan?.input_hashes?.prop_glb_sha256)
      throw Error("Repères 3D de l'objet absents ou périmés : lancer object_landmarks");
    const records=landmarks.points;
    const mapped={};
    const candidates=[];
    for(const mesh of meshes){
      const positions=mesh.getVerticesData?.(BABYLON.VertexBuffer.PositionKind);
      if(!positions?.length)continue;
      mesh.computeWorldMatrix(true);
      candidates.push({mesh,positions});
    }
    if(!candidates.length)throw Error("Maillage de l'objet introuvable");
    for(const name of ["handle_butt","grip_center","working_head","functional_edge"]){
      const reference=records?.[name]?.local;
      if(!Array.isArray(reference)||reference.length!==3 ||
         reference.some(v=>!Number.isFinite(v)))throw Error("Repère 3D invalide : "+name);
      let best=null;
      for(const candidate of candidates){
        const p=candidate.positions;
        for(let i=0;i<p.length;i+=3){
          const distance=(p[i]-reference[0])**2+(p[i+1]-reference[1])**2+
            (p[i+2]-reference[2])**2;
          if(!best||distance<best.distance)best={candidate,i,distance};
        }
      }
      const bounds=best.candidate.mesh.getBoundingInfo().boundingBox;
      const span=bounds.maximum.subtract(bounds.minimum).length();
      if(Math.sqrt(best.distance)>span*.025)
        throw Error("Repère "+name+" non retrouvé dans les sommets du GLB");
      const {positions,mesh}=best.candidate;
      const point=BABYLON.Vector3.TransformCoordinates(
        new BABYLON.Vector3(positions[best.i],positions[best.i+1],positions[best.i+2]),
        mesh.getWorldMatrix());
      mapped[name]=point.asArray();
    }
    return mapped;
  }

  function normalizedNodeName(node) {
    return (node?.name||"").toLowerCase().replace(/[^a-z0-9]/g,"");
  }

  function findGripAnatomy(imported, side) {
    const nodes=[...(imported.transformNodes||[]),...(imported.meshes||[])];
    const find=name=>nodes.find(node=>normalizedNodeName(node).endsWith(name));
    const stem=side==="left"?"lefthand":"righthand";
    const hand=find(stem);
    if(!hand)return null;
    const forearm=find(side+"forearm")||find(side+"lowerarm")||hand.parent;
    const joints={};
    const trunk={Hips:find("hips"),Chest:find("spine2")||find("spine1")||find("spine"),
      Neck:find("neck"),LeftShoulder:find("leftshoulder"),
      RightShoulder:find("rightshoulder")};
    for(const [part,node] of Object.entries(trunk)){
      if(!node)continue;
      node.computeWorldMatrix(true);
      const p=node.getAbsolutePosition();
      joints[part]=[p.x,p.y,p.z];
    }
    for(const handSide of ["left","right"]){
      const prefix=handSide+"hand";
      const related={
        Wrist:find(prefix),Elbow:find(handSide+"forearm")||find(handSide+"lowerarm"),
        Index:find(prefix+"index1"),Middle:find(prefix+"middle1"),
        Pinky:find(prefix+"pinky1"),Foot:find(handSide+"foot"),
        Toe:find(handSide+"toebase")
      };
      for(const [part,node] of Object.entries(related)){
        if(!node)continue;
        node.computeWorldMatrix(true);
        const p=node.getAbsolutePosition();
        joints[handSide+part]=[p.x,p.y,p.z];
      }
    }
    return {hand,forearm,joints};
  }

  function buildGripRotation(prop, wantedShaft, wantedBlade) {
    const B=BABYLON;
    const r=window.WCWeaponGrip.rotationBetweenFrames(
      prop.shaft,prop.blade,wantedShaft.asArray(),wantedBlade.asArray());
    const rotation=B.Matrix.FromValues(
      r[0],r[1],r[2],0,
      r[3],r[4],r[5],0,
      r[6],r[7],r[8],0,
      0,0,0,1);
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
      // A cheap LLM estimates approximate real-world length in centimetres
      // from the original design. The rigging plan still decides grip/orientation,
      // but its old relative-height guess does not override physical dimensions.
      const physicalSizePath=state.selected?.props?.find(p=>p.gripPlan===planUrl)?.physicalSize;
      let estimatedLengthCm=null;
      if(physicalSizePath) {
        const sizeResponse=await fetch(assetUrl(physicalSizePath),{cache:"no-store"});
        if(!sizeResponse.ok)throw Error("Fiche de dimensions indisponible");
        const size=await sizeResponse.json();
        if(size.schema!==1 || size.units!=="cm" ||
          !Number.isFinite(size.estimated_length_cm) ||
          size.estimated_length_cm<2 || size.estimated_length_cm>1000)
          throw Error("Estimation physique invalide");
        estimatedLengthCm=size.estimated_length_cm;
      }
      const spec=vision?.specifications;
      const gripFraction=vision?.derived_image_geometry?.grip_fraction_from_butt;
      const side=spec?.dominant_hand==="left"?"left":"right";
      if(![2,3].includes(vision.schema)||!["shaft","frame","flat_handle","body"].includes(spec?.grip_geometry)||
        spec.hold_mode==="unsupported")throw Error("Plan de prise géométrique non résolu");
      if(!Number.isFinite(gripFraction)||gripFraction<=.02||gripFraction>=.96||
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
      if(!window.WCWeaponGrip?.frameFromLandmarks)throw Error("Analyseur géométrique manquant");
      prop=await B.SceneLoader.ImportMeshAsync(null,"",assetUrl(propPath),state.scene);
      if(token!==state.pendingLoad) {
        for(const node of [...prop.meshes,...prop.transformNodes])
          if(!node.isDisposed())node.dispose(false,true);
        return;
      }
      const points=importedPropPoints(prop.meshes||[]);
      const meshPoints=importedPropLandmarks(prop.meshes||[],vision);
      const frame=window.WCWeaponGrip.frameFromLandmarks(meshPoints,points);
      const {hand,joints}=anatomy;
      hand.computeWorldMatrix(true);
      if(!window.WCRigContact?.contactFrame)
        throw Error("Repères articulaires génériques indisponibles");
      const gravityCarry=!!frame.carryShaft;
      const contact=window.WCRigContact.contactFrame(joints,{
        hand:side,palm_fraction:spec.palm_from_wrist,
        shaft_direction:gravityCarry?"gravity":spec.head_direction,
        working_face:spec.edge_direction
      });
      const desiredLength=estimatedLengthCm===null
        ? 1.9*spec.length_relative_character_height : estimatedLengthCm/100;
      let carryFit=null;
      let bodyCapsules=[];
      let outwardWorld=null;
      if(gravityCarry && joints.Hips && joints.Chest &&
          joints.LeftShoulder && joints.RightShoulder){
        const v=window.WCWeaponGrip;
        const center=v.add(v.mul(joints.Hips,.45),v.mul(joints.Chest,.55));
        const away=v.sub(contact.grip,center);
        outwardWorld=away;
        const shoulderSpan=v.norm(v.sub(joints.LeftShoulder,joints.RightShoulder));
        const torsoRadius=Math.max(.17,shoulderSpan*.46);
        bodyCapsules=[
            {a:joints.Hips,b:joints.Chest,radius:torsoRadius},
            {a:joints.Chest,b:joints.Neck||joints.Chest,radius:torsoRadius*.75}
          ];
        carryFit=v.chooseNonCollidingCarry(points,frame,contact.grip,
          contact.blade,away,desiredLength,bodyCapsules);
      }
      const shaftWorld=new B.Vector3(...(carryFit?.shaft||contact.shaft));
      const bladeWorld=new B.Vector3(...contact.blade);
      const worldRotation=buildGripRotation(
        gravityCarry?{...frame,shaft:frame.carryShaft}:frame,shaftWorld,bladeWorld);
      const parentScale=new B.Vector3(),parentRotation=new B.Quaternion();
      hand.getWorldMatrix().decompose(parentScale,parentRotation);
      const unitScale=(Math.abs(parentScale.x)+Math.abs(parentScale.y)+Math.abs(parentScale.z))/3;
      if(!Number.isFinite(unitScale)||unitScale<1e-7)throw Error("Échelle de main invalide");
      // Only the grip is parented to the animated hand. The weapon shaft
      // extends toward the forearm and the cutting edge toward the avatar's front.
      // Character Lab normalizes the warrior to 1.9 scene units; within
      // this scene we use 1 unit = 1 metre. A 115 cm axe is 1.15 units.
      anchor=new B.TransformNode("wc-auto-grip-"+side+"-hand",state.scene);
      anchor.parent=hand;
      anchor.position.copyFrom(B.Vector3.TransformCoordinates(
        new B.Vector3(...contact.grip),B.Matrix.Invert(hand.getWorldMatrix())));
      // Babylon composes child rotations as local * parent, so undoing the
      // hand's world rotation is desiredWorld * inverse(parentWorld).
      // Reversing this product produces a plausible but physically incorrect
      // orientation for any rotated humanoid hand.
      anchor.rotationQuaternion=worldRotation.multiply(B.Quaternion.Inverse(parentRotation));
      anchor.scaling.setAll(desiredLength/(frame.length*unitScale));
      const offset=new B.TransformNode("wc-weapon-local-grip-origin",state.scene);
      offset.parent=anchor;
      offset.position=new B.Vector3(...frame.grip).negate();
      const roots=[...prop.meshes,...prop.transformNodes].filter(node=>!node.parent);
      for(const node of roots)node.parent=offset;
      // A source-frame prediction is not necessarily identical to Babylon's
      // final parent/skin/model matrices. Resolve the physical fit using the
      // actual mounted mesh and the *same* generic anatomical constraints.
      const gripFrame=gravityCarry?{...frame,shaft:frame.carryShaft}:frame;
      let actualClearance=NaN;
      let actualBalanceY=NaN;
      let actualGripError=NaN;
      let actualWorkingFace=NaN;
      if(bodyCapsules.length&&outwardWorld){
        const v=window.WCWeaponGrip;
        const margin=bodyCapsules[0].radius*.8;
        const candidates=v.gravityCarryCandidates(contact.blade,outwardWorld);
        let best=null;
        for(const candidate of candidates){
          const q=buildGripRotation(gripFrame,
            new B.Vector3(...candidate.shaft),bladeWorld);
          anchor.rotationQuaternion=q.multiply(B.Quaternion.Inverse(parentRotation));
          anchor.computeWorldMatrix(true);
          offset.computeWorldMatrix(true);
          const mounted=importedPropPoints(prop.meshes||[]);
          const landmarks=importedPropLandmarks(prop.meshes||[],vision);
          const actual=v.capsuleClearance(mounted,bodyCapsules);
          const mass=v.mul(mounted.reduce(v.add,[0,0,0]),1/mounted.length);
          const balance=v.sub(mass,landmarks.grip_center);
          const gripError=v.norm(v.sub(contact.grip,landmarks.grip_center));
          const edge=v.unit(v.sub(landmarks.functional_edge,landmarks.working_head));
          const face=v.dot(edge,contact.blade);
          const deficit=Math.max(0,margin-actual);
          const wrongGravity=Math.max(0,balance[1]+desiredLength*.08);
          const wrongFace=Math.max(0,.6-face);
          const score=deficit*deficit*100+wrongGravity**2*80+
            wrongFace**2*3+gripError**2*150+candidate.tilt*.012;
          if(!best||score<best.score)best={...candidate,actual,score,
            balanceY:balance[1],gripError,face};
        }
        if(best){
          actualClearance=best.actual;
          actualBalanceY=best.balanceY;
          actualGripError=best.gripError;
          actualWorkingFace=best.face;
          carryFit={...carryFit,shaft:best.shaft,tilt:best.tilt};
          const q=buildGripRotation(gripFrame,new B.Vector3(...best.shaft),bladeWorld);
          anchor.rotationQuaternion=q.multiply(B.Quaternion.Inverse(parentRotation));
          anchor.computeWorldMatrix(true);
          offset.computeWorldMatrix(true);
        }
      }
      state.weaponImport=prop;
      state.weaponAnchor=anchor;
      text("weaponMetric","Prise anatomique auto · vision sur GLB · main "+side+
        (spec.hold_mode==="two_hands"?" (seconde main non pilotée)":"")+
        (estimatedLengthCm===null
          ? " · ancienne échelle "+spec.length_relative_character_height.toFixed(2)
          : " · longueur estimée "+estimatedLengthCm.toFixed(0)+" cm"));
      byId("world").dataset.weaponGrip="vision-glb-anatomical-landmarks";
      byId("world").dataset.weaponCarry=gravityCarry?"mass-below-hand":"annotated-shaft";
      byId("world").dataset.weaponCarryTilt=carryFit?.tilt?.toFixed(3)||"0";
      byId("world").dataset.weaponCarryClearance=Number.isFinite(carryFit?.nearest)
        ? carryFit.nearest.toFixed(3):"";
      byId("world").dataset.weaponActualClearance=Number.isFinite(actualClearance)
        ? actualClearance.toFixed(3):"";
      byId("world").dataset.weaponBodyRadius=bodyCapsules[0]?.radius?.toFixed(3)||"";
      byId("world").dataset.weaponBalanceY=Number.isFinite(actualBalanceY)
        ? actualBalanceY.toFixed(3):"";
      byId("world").dataset.weaponGripError=Number.isFinite(actualGripError)
        ? actualGripError.toFixed(3):"";
      byId("world").dataset.weaponWorkingFace=Number.isFinite(actualWorkingFace)
        ? actualWorkingFace.toFixed(3):"";
      byId("world").dataset.weaponGripScale=(desiredLength/1.9).toFixed(3);
      byId("world").dataset.weaponLengthCm=estimatedLengthCm===null
        ? "" : estimatedLengthCm.toFixed(1);
      byId("world").dataset.weaponScaleOrigin=estimatedLengthCm!==null
        ? "source-design-physical-centimetres"
        : (vision.schema===3 ? "provenance-and-character-image" : "legacy-vision-only");
      byId("world").dataset.weaponGripHeadRatio=Number.isFinite(frame.headWidthRatio)
        ? frame.headWidthRatio.toFixed(3):"";
      // Enforce genuine equipment-specific motions once the prop is fitted.
      // A bow must never inherit a generic axe animation by default.
      const policy=window.WCEquipmentActions?.resolve(
        {...spec,mesh_contact_ready:true},state.animGroups);
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
      // Selection is data-driven. A unit may own several independently
      // grabbable props; the rig solver itself does not know their identities.
      const requestedProp=new URLSearchParams(location.search).get("prop");
      const propEntry=state.selected?.props?.find(p=>p.id===requestedProp)
        ||state.selected?.props?.[0];
      const propPlan=propEntry?.gripPlan;
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
    if (state.camera && state.engine)
      WCArena.refreshCameraScale(state.camera,state.engine);
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
    byId("unitSelect").addEventListener("change",event=>{
      const char=state.catalog.characters.find(c=>c.id===event.target.value&&c.models.length)
        ||state.catalog.characters.find(c=>c.id===event.target.value);
      if(!char)return;
      state.selected=char;
      state.input.clear();state.touch.clear();
      renderModelVersions();
      if(!char.models.length){
        showSourceOnly(char);
      } else {
        const url=byId("modelSelect").value;
        selectByPath(url);
        loadModel(url);
      }
    });
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
    originalUnitCaption=byId("unitCaption")?.textContent||"";
    bindUI();
    await fetchCatalog();
    const hasWorld=createWorld();
    const path=byId("modelSelect").value;
    if(state.selected && state.selected.models.length===0) {
      // Intentionally source-only: keep the image unobscured even when WebGL
      // or the external Babylon CDN is unavailable.
      showSourceOnly(state.selected);
    } else if(hasWorld && location.protocol==="file:") {
      setOverlay("Ouvre avec le serveur local pour charger les modèles automatiquement, ou choisis un GLB.",false);
      setStatus("Mode fichier : importer un GLB avec le bouton","warning");
    } else if(hasWorld && path) {
      await loadModel(path);
    }
  }
  window.addEventListener("DOMContentLoaded",boot);
})();

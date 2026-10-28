/* WarConquer Perception Lab: editable world -> bounded perception -> motion intent.
 * The Babylon model and animation library are optional; navigation never depends on them.
 */
(() => {
  "use strict";
  const $=id=>document.getElementById(id);
  const B=window.BABYLON;
  if(!B||!window.WCArena||!window.WCPerception||!window.WCResources||
      !window.WCGait||!window.WCCombat){
    $("status").textContent="Babylon.js, l'arène ou le module de perception n'a pas chargé.";
    $("engineBadge").textContent="Moteur indisponible";
    return;
  }
  let arena;
  try { arena=WCArena.create($("world"),B); }
  catch(error) {
    $("engineBadge").textContent="WebGL indisponible";
    $("status").textContent="Impossible de créer la scène 3D : "+error.message;
    return;
  }
  const {scene,engine,camera}=arena;
  const Brain=WCPerception.Brain;
  const colors={unitBlue:"#55c4d4",unitRed:"#d96c5f",resource:"#efc267",obstacle:"#aeb6ba"};
  const state={items:[],seq:0,clock:0,paused:false,tool:null,pending:null,
    selected:null,order:{type:"hold"},decision:null,animation:{},currentClip:null,
    actionRunning:false,actor:null,brain:null,loadedModel:false,acc:0,
    simPose:{x:0,z:0,yaw:0},prevPose:{x:0,z:0,yaw:0},
    currentMotionMode:null,modelOptions:[],modelToken:0,
    imported:null,avatarContent:null,gait:{walk:1.4,run:3.55},gaitScale:1,
    pendingHit:null,attackCount:0,
    inventory:WCResources.inventory(),events:[],actionSerial:0,lastStatus:null};
  const point=(x,z)=>({x,z});
  const range=(x,min,max)=>Math.max(min,Math.min(max,x));
  const color=hex=>B.Color3.FromHexString(hex);
  function message(value){$("status").textContent=value;}
  function createMaterial(name,hex){
    const mat=new B.StandardMaterial(name,scene);
    mat.diffuseColor=color(hex);mat.specularColor=B.Color3.Black();
    return mat;
  }
  const player=new B.TransformNode("scout-root",scene);
  const placeholder=B.MeshBuilder.CreateCapsule("scout-placeholder",
    {height:1.75,radius:.34,tessellation:12},scene);
  placeholder.parent=player;placeholder.position.y=.9;
  placeholder.material=createMaterial("scout-color",colors.unitBlue);
  const nose=B.MeshBuilder.CreateBox("scout-nose",{width:.16,height:.16,depth:.3},scene);
  nose.parent=player;nose.position=new B.Vector3(0,1.4,.34);
  nose.material=createMaterial("scout-heading","#f5e5bb");
  player.position.x=0;player.position.z=0;
  state.actor=player;
  const sight=B.MeshBuilder.CreateLines("vision-ring",{
    points:Array.from({length:65},(_,i)=>new B.Vector3(
      Math.cos(i*Math.PI/32)*7,.045,Math.sin(i*Math.PI/32)*7))
  },scene);
  sight.color=color("#6bc6ba");sight.alpha=.6;sight.isPickable=false;
  let routeMesh=null;
  function itemPalette(item){
    return item.kind==="unit"?(item.team==="red"?colors.unitRed:colors.unitBlue):
      colors[item.kind]||colors.obstacle;
  }
  function renderItem(item) {
    if(item.static) {
      item.mesh.material.diffuseColor=color(itemPalette(item));
      return;
    }
    if(item.mesh)item.mesh.dispose(false,true);
    let mesh;
    if(item.kind==="resource"){
      mesh=B.MeshBuilder.CreatePolyhedron(item.id,{type:1,size:.8},scene);
      mesh.position.y=.7;
    }else if(item.kind==="obstacle"){
      mesh=B.MeshBuilder.CreateBox(item.id,{size:1.2},scene);
      mesh.scaling=new B.Vector3(1,1.15,1);
      mesh.position.y=.7;
    }else{
      mesh=B.MeshBuilder.CreateCapsule(item.id,{height:1.6,radius:.33,tessellation:10},scene);
      mesh.position.y=.8;
    }
    mesh.position.x=item.x;mesh.position.z=item.z;
    mesh.material=createMaterial("mat-"+item.id,itemPalette(item));
    mesh.metadata={objectId:item.id};
    item.mesh=mesh;
  }
  function addItem(kind,x,z,options={}){
    const id="item-"+(++state.seq);
    const item={id,name:options.name||({unit:"Unité",resource:"Ressource",obstacle:"Obstacle"}[kind]||kind)+" "+state.seq,
      kind,team:options.team||(kind==="unit"?"red":"neutral"),
      x,z,radius:options.radius??(kind==="obstacle"?.65:.4),
      resourceType:options.resourceType||"wood",quantity:options.quantity??1,
      health:options.health??(kind==="unit"?100:0),
      threat:options.threat??(kind==="unit"?1:0),
      blocking:options.blocking??(kind==="obstacle"||kind==="unit"),
      opaque:options.opaque??(kind==="obstacle"),mesh:null,static:false};
    state.items.push(item);renderItem(item);return item;
  }
  function clearItems(){
    for(const item of state.items)if(!item.static)item.mesh?.dispose(false,true);
    state.items=[];
  }
  function resetDemo(){
    clearItems();
    for(const rock of arena.obstacles){
      const mesh=scene.getMeshByName(rock.id);
      if(!mesh)continue;
      const item={id:rock.id,name:"Rocher",kind:"obstacle",team:"neutral",
        x:rock.x,z:rock.z,radius:rock.radius,resourceType:"ore",quantity:1,threat:0,
        blocking:true,opaque:true,mesh,static:true};
      state.items.push(item);renderItem(item);
    }
    addItem("unit",4,-2,{name:"Éclaireur adverse",team:"red",threat:1,blocking:true});
    addItem("resource",-3,3,{name:"Gisement de minerai",resourceType:"ore"});
    addItem("unit",-2,-5,{name:"Soldat allié",team:"blue",threat:0});
    player.position.x=0;player.position.z=0;player.rotation.y=0;
    state.simPose={x:0,z:0,yaw:0};state.prevPose={...state.simPose};
    state.acc=0;
    state.brain=new Brain({id:"scout",team:"blue",x:0,z:0,
      visionRange:Number($("visionRange").value),memoryTtlMs:20000});
    state.clock=0;state.order={type:"hold"};state.decision=null;
    state.inventory=WCResources.inventory();state.events=[];state.lastStatus=null;
    state.actionSerial++;state.actionRunning=false;state.pendingHit=null;
    state.attackCount=0;
    for(const clip of state.animation.groups||[])clip.stop();
    state.currentClip=null;state.currentMotionMode=null;motion("idle");
    state.tool=null;state.pending=null;
    state.paused=false;$("playPause").textContent="Pause";
    selectItem(null);syncMode();
    message("Exemple chargé. Choisissez « Trouver ◆ » ou ajoutez un ennemi puis approchez-vous.");
  }
  function makeWorld(){
    const grid=[],occlusion=[];
    for(let z=0;z<32;z++){
      let row="",oc="";
      for(let x=0;x<32;x++){
        const p={x:x-15.5,z:z-15.5};
        const objectsHere=state.items.filter(o=>{
          // Grid cell square intersects the object circle (not a centre-only guess).
          const dx=Math.max(0,Math.abs(p.x-o.x)-.5);
          const dz=Math.max(0,Math.abs(p.z-o.z)-.5);
          return Math.hypot(dx,dz)<o.radius;
        });
        row+=objectsHere.some(o=>o.blocking)?"#":".";
        oc+=objectsHere.some(o=>o.opaque)?"#":".";
      }
      grid.push(row);occlusion.push(oc);
    }
    return {originX:-16,originZ:-16,grid,occlusion,objects:state.items.map(o=>({
      id:o.id,x:o.x,z:o.z,kind:o.kind,team:o.team,
      blocking:o.blocking,opaque:o.opaque,radius:o.radius,threat:o.threat,
      health:o.health
    }))};
  }
  function drawPath(result){
    if(routeMesh){routeMesh.dispose();routeMesh=null;}
    const path=[{x:state.simPose.x,z:state.simPose.z},...(result.path||[])];
    if(path.length<2)return;
    routeMesh=B.MeshBuilder.CreateLines("planned-route",{
      points:path.map(p=>new B.Vector3(p.x,.075,p.z))},scene);
    routeMesh.color=color("#f2c47b");routeMesh.alpha=.9;routeMesh.isPickable=false;
  }
  function groupFor(name){
    const groups=state.animation.groups||[];
    const patterns={
      idle:/(^|[_ -])(idle|rest)([_ -]|$)/i,
      walk:/(^|[_ -])(walk|walking)([_ -]|$)/i,
      run:/(^|[_ -])(run|running)([_ -]|$)/i,
      attack:meleeClipPattern,
      collect:/(^|[_ -])(pick.?up|pickup|collect|gather)([_ -]|$)/i
    };
    return groups.find(g=>patterns[name].test(g.name))||null;
  }
  function updateGait(){
    const settings={height:1.9,scale:state.gaitScale};
    state.gait.walk=WCGait.nominalSpeed("walk",
      state.animation.walk||state.animation.run,settings)||1.4*state.gaitScale;
    state.gait.run=WCGait.nominalSpeed("run",
      state.animation.run||state.animation.walk,settings)||3.55*state.gaitScale;
    $("gaitInfo").textContent="Marche "+state.gait.walk.toFixed(2)+
      " m/s · Course "+state.gait.run.toFixed(2)+" m/s";
    $("gaitScaleLabel").textContent=Math.round(state.gaitScale*100)+" %";
  }
  function motion(name,speed=0){
    if(state.actionRunning)return;
    if(state.paused&&name!=="idle")name="idle";
    const clip=name==="walk"?(state.animation.walk||state.animation.run||state.animation.idle):
      name==="run"?(state.animation.run||state.animation.walk||state.animation.idle):
      (state.animation[name]||state.animation.idle)||null;
    // Link the number of actual world metres moved to the gait cycle rate.
    // Animation durations come from the imported GLB, not fixed timeouts.
    const ratio=(name==="walk"||name==="run")?
      WCGait.playbackRatio(name,clip,speed,{height:1.9,scale:state.gaitScale}):1;
    if(clip===state.currentClip){
      if(clip)clip.speedRatio=ratio;
      state.currentMotionMode=name;
      return;
    }
    state.currentClip?.stop();
    state.currentClip=clip;state.currentMotionMode=name;
    if(clip)clip.start(true,ratio,clip.from,clip.to);
    $("animationState").textContent=clip?.name||"Aucun clip";
  }
  function renderPose(alpha){
    const t=range(alpha,0,1),a=state.prevPose,b=state.simPose;
    player.position.x=a.x+(b.x-a.x)*t;
    player.position.z=a.z+(b.z-a.z)*t;
    const rotation=Math.atan2(Math.sin(b.yaw-a.yaw),Math.cos(b.yaw-a.yaw));
    player.rotation.y=a.yaw+rotation*t;
    sight.position.x=player.position.x;sight.position.z=player.position.z;
  }
  function recordEvent(value) {
    state.events.unshift(value);
    if(state.events.length>6)state.events.length=6;
    message(value);
  }
  function act(action) {
    if(state.actionRunning)return;
    if(action==="collect"){
      const id=state.order?.entityId;
      const resource=state.items.find(item=>item.id===id);
      const reach=Math.max(1.25,Number(state.order.distance)||0);
      const outcome=WCResources.collect({
        items:state.items,bag:state.inventory,entityId:id,
        actor:{x:state.simPose.x,z:state.simPose.z},reach
      });
      if(!outcome.ok){
        recordEvent("Ramassage refusé : "+outcome.reason);
        state.order={type:"hold"};
        return;
      }
      resource?.mesh?.dispose(false,true);
      state.brain.forgetEntity(id);
      if(state.selected===resource)selectItem(null);
      state.order={type:"hold"};
      recordEvent("Ramassé : "+outcome.amount+" "+outcome.type+
        " · inventaire total : "+outcome.total);
      // The inventory transaction is already committed. The animation is
      // cosmetic and may be absent or interrupted without undoing the pickup.
    }
    const group=state.animation[action];
    if(!group){
      if(action==="collect"){
        motion("idle");
        $("animationState").textContent="Collecte effectuée · sans clip Mixamo";
      }else{
        $("animationState").textContent="Attaque indisponible · clip Mixamo absent";
        recordEvent("Attaque impossible : le personnage sélectionné n'a aucun clip d'attaque.");
        state.order={type:"hold"};
      }
      return;
    }
    const serial=++state.actionSerial;
    state.actionRunning=true;
    state.currentClip?.stop();state.currentClip=null;
    state.currentMotionMode=null;
    group.stop();group.start(false,1,group.from,group.to);
    $("animationState").textContent=group.name;
    if(action==="attack"){
      const seconds=WCGait.duration(group)||1.4;
      state.pendingHit={serial,entityId:state.order.entityId,
        at:state.clock+Math.round(seconds*550)};
    }
    group.onAnimationGroupEndObservable.addOnce(()=>{
      if(serial!==state.actionSerial)return;
      state.actionRunning=false;
      state.pendingHit=null;
      motion("idle");
    });
  }
  function resolveAttackImpact(){
    const pending=state.pendingHit;
    if(!pending||pending.serial!==state.actionSerial||state.clock<pending.at)return;
    state.pendingHit=null;
    const outcome=WCCombat.hit({items:state.items,entityId:pending.entityId,
      actor:{x:state.simPose.x,z:state.simPose.z},
      team:state.brain.team,reach:1.6,damage:34});
    if(!outcome.ok){
      recordEvent("Coup manqué : "+outcome.reason);
      return;
    }
    state.attackCount++;
    recordEvent("Coup porté : "+outcome.damage+" dégâts · "+outcome.name+
      " · "+outcome.health+" PV");
    if(outcome.defeated){
      outcome.item.mesh?.dispose(false,true);
      state.brain.forgetEntity(outcome.id);
      if(state.selected===outcome.item)selectItem(null);
      state.order={type:"hold"};
      recordEvent(outcome.name+" vaincu.");
    }
  }
  function tick(){
    state.clock+=100;
    resolveAttackImpact();
    const world=makeWorld();
    state.brain.speed=state.order.type==="flee"?state.gait.run:state.gait.walk;
    const before=state.simPose,after={...before};
    state.brain.setPose({x:before.x,z:before.z});
    const decision=state.brain.step(world,state.order,100,state.clock);
    state.decision=decision;
    const attempted=decision.move;
    const wantsMove=Math.hypot(attempted.dx,attempted.dz)>.0001;
    let moved=false;
    if(wantsMove&&!state.actionRunning){
      const nx=before.x+attempted.dx,nz=before.z+attempted.dz;
      const blockedCell=WCPerception.firstBlockedCell(world,before,{x:nx,z:nz});
      const accepted=!blockedCell;
      state.brain.reportMoveResult({accepted,attempted,blockedCell,nowMs:state.clock});
      if(accepted){
        moved=true;after.x=nx;after.z=nz;
        const yaw=Math.atan2(attempted.dx,attempted.dz);
        after.yaw=before.yaw+Math.atan2(Math.sin(yaw-before.yaw),Math.cos(yaw-before.yaw));
        state.brain.heading=Math.atan2(attempted.dz,attempted.dx);
      }else{
        decision.status=state.brain.stallCount>=3?"stuck":"replanning";
        decision.reason="collision";
        decision.move={dx:0,dz:0};
      }
    }
    // Perception/collision at 10 Hz, GLB motion interpolated at render FPS.
    state.prevPose=before;state.simPose=after;
    if(decision.action)act(decision.action);
    else if(moved)motion(decision.status==="fleeing"?"run":"walk",
      Math.hypot(attempted.dx,attempted.dz)/.1);
    else motion("idle");
    if(decision.status==="stuck"&&state.lastStatus!=="stuck")
      recordEvent("Chemin bloqué après plusieurs essais : un nouvel ordre est nécessaire.");
    state.lastStatus=decision.status;
    sight.scaling.setAll(state.brain.range/7);
    drawPath(decision);
    updateHud();
  }
  function updateHud(){
    const d=state.decision,brain=state.brain;
    if(!brain)return;
    $("clock").textContent=(state.clock/1000).toFixed(1)+" s · 10 Hz";
    $("brainState").textContent=d?.status||"Repos";
    $("fear").textContent=Math.round(brain.fear*100)+" %";
    $("knownCells").textContent=brain.cells.size+" / 1024";
    $("seenCount").textContent=brain.visible.length+" / "+brain.entities.size;
    $("attackStatus").textContent=state.attackCount+" coup(s) confirmé(s)";
    $("inventoryText").textContent="Bois : "+state.inventory.wood+
      " · Minerai : "+state.inventory.ore+" · Nourriture : "+state.inventory.food;
    const history=$("eventList");history.replaceChildren();
    if(!state.events.length){
      const li=document.createElement("li");li.textContent="Aucune collecte";history.append(li);
    }
    for(const entry of state.events){
      const li=document.createElement("li");li.textContent=entry;history.append(li);
    }
    $("visionRangeLabel").textContent=brain.range+" m";
    const list=$("memoryList");list.replaceChildren();
    if(!brain.entities.size){
      const li=document.createElement("li");li.textContent="Aucune entité mémorisée";list.append(li);
    }
    for(const e of [...brain.entities.values()].sort((a,b)=>b.seenAt-a.seenAt)){
      const li=document.createElement("li");
      const live=brain.visible.some(v=>v.id===e.id);
      li.textContent=(live?"◉ Vu : ":"◌ Souvenir : ")+e.role+" · "+e.id+
        " ("+e.x.toFixed(1)+", "+e.z.toFixed(1)+")"+
        (live?"":" · "+((state.clock-e.seenAt)/1000).toFixed(1)+"s");
      list.append(li);
    }
    $("decision").textContent=JSON.stringify({
      order:state.order,status:d?.status,mode:d?.mode,action:d?.action,
      goal:d?.goal,move:d?.move,memory:d?.memory
    },null,2);
  }
  function syncMode(){
    document.querySelectorAll("[data-place]").forEach(btn=>
      btn.classList.toggle("active",state.tool===btn.dataset.place));
    $("selectMode").classList.toggle("active",state.tool===null&&!state.pending);
    document.querySelectorAll("[data-order]").forEach(btn=>
      btn.classList.toggle("active",state.pending===btn.dataset.order));
  }
  function selectItem(item){
    state.selected=item;
    $("inspector").hidden=!item;
    $("deleteObject").disabled=!!item?.static;
    $("selectionHint").textContent=item?"Identifiant : "+item.id:"Touchez une unité, une ressource ou un obstacle.";
    if(!item)return;
    $("objectName").value=item.name;
    $("objectKind").value=item.kind;
    $("objectTeam").value=item.team;
    $("resourceKind").value=item.resourceType;
    $("resourceQuantity").value=item.quantity||1;
    $("collectSelected").disabled=item.kind!=="resource";
    $("unitHealth").value=item.health??100;
    $("unitHealth").disabled=item.kind!=="unit";
    $("threatLevel").value=item.threat;
    $("blocking").checked=item.blocking;
    $("opaque").checked=item.opaque;
  }
  function placeFromMode(x,z){
    const t=state.tool;
    const item=addItem(t==="enemy"||t==="ally"?"unit":t,x,z,
      {team:t==="ally"?"blue":t==="enemy"?"red":"neutral"});
    selectItem(item);state.tool=null;syncMode();
    message("Objet ajouté : "+item.name+". Ses propriétés peuvent être modifiées à droite.");
  }
  function setOrder(type,dir){
    state.tool=null;
    if(["goto","attack","collect"].includes(type)){
      state.pending=type;
      message(type==="goto"?"Cliquez une destination.":"Cliquez sur "+(type==="attack"?"un ennemi.":"une ressource."));
    }else{
      state.pending=null;
      state.order=type==="relative"?{type,direction:dir,distance:4,id:++state.seq}:
        type==="find"?{type,kind:"resource",distance:1}:
        {type};
      message("Ordre transmis au cerveau : "+JSON.stringify(state.order));
    }
    syncMode();
  }
  function clickWorld(){
    const hit=scene.pick(scene.pointerX,scene.pointerY,mesh=>
      mesh===arena.ground||!!mesh.metadata?.objectId);
    if(!hit?.hit)return;
    const id=hit.pickedMesh?.metadata?.objectId;
    const obj=state.items.find(i=>i.id===id)||null;
    const p=hit.pickedPoint;
    if(state.pending){
      if(state.pending==="goto"){
        if(!p)return;
        state.order={type:"goto",x:range(p.x,-15.5,15.5),z:range(p.z,-15.5,15.5)};
      }else{
        if(!obj||!(state.pending==="attack"?obj.kind==="unit"&&obj.team==="red":obj.kind==="resource")){
          message("Sélectionnez "+(state.pending==="attack"?"une unité ennemie.":"une ressource."));return;
        }
        state.order={type:state.pending,entityId:obj.id,distance:state.pending==="attack"?1.35:Math.max(1.25,obj.radius+1)};
      }
      message("Ordre actif : "+state.order.type);
      state.pending=null;syncMode();
    }else if(state.tool&&p){
      placeFromMode(range(p.x,-15,15),range(p.z,-15,15));
    }else{
      selectItem(obj);
    }
  }
  function disposeAvatar(){
    for(const group of state.imported?.animationGroups||[]){group.stop();group.dispose();}
    state.avatarContent?.dispose(false,true);
    for(const skeleton of state.imported?.skeletons||[])skeleton.dispose();
    state.imported=null;state.avatarContent=null;
    state.animation={};state.currentClip=null;state.currentMotionMode=null;
    state.actionSerial++;state.actionRunning=false;state.pendingHit=null;
    state.loadedModel=false;
    placeholder.setEnabled(true);nose.setEnabled(true);
    $("attackNearest").disabled=true;
    document.querySelector('[data-order="attack"]').disabled=true;
    updateGait();
  }
  const meleeClipPattern=/(^|[_ -])(attack|axe|chop|melee|strike|swing)([_ -]|$)/i;
  function modelScore(model){
    const clips=(model.clips||[]).map(name=>name.toLowerCase());
    const has=pattern=>clips.some(c=>pattern.test(c));
    return (has(meleeClipPattern)?100:0)+
      (has(/walk|marche/)?10:0)+(has(/run|course/)?10:0)+
      (model.priority||0)/100;
  }
  async function loadSelectedAvatar(){
    const entry=state.modelOptions[Number($("avatarSelect").value)];
    if(!entry)return;
    const token=++state.modelToken;
    disposeAvatar();
    state.order={type:"hold"};
    $("engineBadge").textContent="Chargement du GLB…";
    $("animationState").textContent="Chargement…";
    $("avatarInfo").textContent=entry.character.name+" · "+entry.model.name;
    try {
      const url=entry.model.url.replace(/^\/assets\//,"assets/");
      const imported=await B.SceneLoader.ImportMeshAsync(null,"",url,scene);
      if(token!==state.modelToken){
        for(const group of imported.animationGroups||[])group.dispose();
        for(const mesh of imported.meshes||[])mesh.dispose(false,true);
        return;
      }
      const content=new B.TransformNode("scout-model-content",scene);
      content.parent=player;
      for(const node of [...imported.meshes,...imported.transformNodes])
        if(!node.parent)node.parent=content;
      const vertices=imported.meshes.filter(m=>m.getTotalVertices?.()>0);
      if(vertices.length){
        function bounds(){
          const min=new B.Vector3(Infinity,Infinity,Infinity);
          const max=new B.Vector3(-Infinity,-Infinity,-Infinity);
          for(const mesh of vertices){
            mesh.computeWorldMatrix(true);
            const bb=mesh.getBoundingInfo().boundingBox;
            min.minimizeInPlace(bb.minimumWorld);max.maximizeInPlace(bb.maximumWorld);
          }
          return {min,size:max.subtract(min)};
        }
        let bb=bounds();
        if(bb.size.z>Math.max(.0001,bb.size.y)*1.8&&
            bb.size.y<Math.max(bb.size.x,bb.size.z)*.48)
          content.rotation.x=-Math.PI/2;
        bb=bounds();
        const scale=range(1.9/Math.max(.00001,bb.size.y),.01,500);
        content.scaling.setAll(scale);
        content.position.y=-bb.min.y*scale;
      }
      state.avatarContent=content;state.imported=imported;
      placeholder.setEnabled(false);nose.setEnabled(false);
      state.animation.groups=imported.animationGroups||[];
      for(const group of state.animation.groups){
        group.stop();
        for(const track of group.targetedAnimations||[]){
          track.animation.enableBlending=true;
          track.animation.blendingSpeed=.15;
        }
      }
      for(const name of ["idle","walk","run","attack","collect"])
        state.animation[name]=groupFor(name);
      state.loadedModel=true;
      $("attackNearest").disabled=!state.animation.attack;
      document.querySelector('[data-order="attack"]').disabled=!state.animation.attack;
      $("engineBadge").textContent="GLB réel · "+state.animation.groups.length+" clips";
      $("avatarInfo").textContent=entry.character.name+" · "+state.animation.groups.map(g=>g.name).join(", ");
      updateGait();
      motion("idle");
      message(state.animation.attack?
        "Personnage animé chargé : attaque Mixamo disponible.":
        "Personnage animé chargé : aucune animation d'attaque pour cette unité.");
    }catch(err){
      if(token!==state.modelToken)return;
      disposeAvatar();
      $("engineBadge").textContent="Avatar de secours · 3D";
      $("animationState").textContent="GLB non chargé";
      message("Impossible de charger ce GLB : "+err.message);
    }
  }
  async function loadAvatar(){
    try{
      const res=await fetch("api/character-lab.json");
      if(!res.ok)throw Error("catalogue absent");
      const catalog=await res.json();
      state.modelOptions=(catalog.characters||[]).flatMap(character=>{
        const playable=(character.models||[]).filter(m=>m.kind==="playable")
          .sort((a,b)=>modelScore(b)-modelScore(a));
        return playable.length?[{character,model:playable[0]}]:[];
      });
      if(!state.modelOptions.length)throw Error("aucun GLB jouable");
      const select=$("avatarSelect");
      select.replaceChildren();
      for(let i=0;i<state.modelOptions.length;i++){
        const entry=state.modelOptions[i];
        const opt=document.createElement("option");
        opt.value=String(i);
        const attack=(entry.model.clips||[]).some(c=>meleeClipPattern.test(c));
        opt.textContent=entry.character.name+(attack?" · ⚔":" · sans attaque");
        select.append(opt);
      }
      const requested=new URLSearchParams(location.search).get("unit");
      const initial=requested?
        state.modelOptions.findIndex(e=>e.character.id===requested):
        state.modelOptions.findIndex(e=>modelScore(e.model)>=100);
      select.value=String(Math.max(0,initial));
      select.disabled=false;
      await loadSelectedAvatar();
    }catch(err){
      $("engineBadge").textContent="Avatar de secours · 3D";
      $("animationState").textContent="GLB non chargé";
      $("avatarInfo").textContent=err.message;
      message("Arène active avec avatar de secours : "+err.message);
    }
  }
  for(const b of document.querySelectorAll("[data-place]"))
    b.addEventListener("click",()=>{state.tool=b.dataset.place;state.pending=null;syncMode();
      message("Cliquez dans l'arène pour placer : "+state.tool);});
  for(const b of document.querySelectorAll("[data-order]"))
    b.addEventListener("click",()=>setOrder(b.dataset.order,b.dataset.dir));
  $("selectMode").addEventListener("click",()=>{state.pending=null;state.tool=null;syncMode();});
  $("playPause").addEventListener("click",()=>{
    state.paused=!state.paused;$("playPause").textContent=state.paused?"Reprendre":"Pause";
    state.acc=0;
    if(state.paused){renderPose(1);motion("idle");}
    else state.prevPose={...state.simPose};
  });
  $("singleStep").addEventListener("click",()=>{
    state.paused=true;$("playPause").textContent="Reprendre";
    state.acc=0;tick();renderPose(1);motion("idle");
  });
  $("resetDemo").addEventListener("click",resetDemo);
  $("avatarSelect").addEventListener("change",()=>void loadSelectedAvatar());
  $("gaitScale").addEventListener("input",event=>{
    state.gaitScale=range(Number(event.target.value)||1,.65,1.4);
    updateGait();
  });
  $("visionRange").addEventListener("input",e=>{state.brain.range=Number(e.target.value);updateHud();});
  $("attackNearest").addEventListener("click",()=>{
    if(!state.animation.attack){
      message("Ce modèle ne possède aucune animation d'attaque.");
      return;
    }
    const enemy=state.brain.chooseEntity(e=>e.role==="enemy");
    if(!enemy){
      message("Aucun ennemi repéré : approchez-vous pour le percevoir.");
      return;
    }
    state.order={type:"attack",entityId:enemy.id,distance:1.35};
    state.pending=null;state.tool=null;syncMode();
    message("Ordre d'attaque : "+enemy.id);
  });
  $("collectNearest").addEventListener("click",()=>{
    const entity=state.brain.chooseEntity(e=>e.kind==="resource");
    if(!entity){
      message("Aucune ressource connue : explorer avant de ramasser.");
      return;
    }
    state.order={type:"collect",entityId:entity.id,
      distance:Math.max(1.25,entity.radius+1)};
    state.pending=null;state.tool=null;syncMode();
    message("Ordre de collecte : "+entity.id);
  });
  $("collectSelected").addEventListener("click",()=>{
    if(state.selected?.kind!=="resource")return;
    state.order={type:"collect",entityId:state.selected.id,
      distance:Math.max(1.25,state.selected.radius+1)};
    state.pending=null;state.tool=null;syncMode();
    message("Ordre de collecte : "+state.selected.name);
  });
  $("deleteObject").addEventListener("click",()=>{
    if(!state.selected||state.selected.static)return;
    const item=state.selected;item.mesh?.dispose(false,true);
    state.items=state.items.filter(i=>i!==item);
    selectItem(null);message("Objet retiré : "+item.name);
  });
  const controls={
    objectName:["name",v=>String(v).slice(0,50)],
    objectKind:["kind",String],objectTeam:["team",String],resourceKind:["resourceType",String],
    resourceQuantity:["quantity",v=>Math.min(99,Math.max(1,Math.round(Number(v)||1)))],
    unitHealth:["health",v=>Math.min(200,Math.max(1,Math.round(Number(v)||100)))],
    threatLevel:["threat",v=>range(Number(v)||0,0,1)],
    blocking:["blocking",v=>!!v],opaque:["opaque",v=>!!v]
  };
  for(const [id,[field,convert]]of Object.entries(controls))
    $(id).addEventListener("change",event=>{
      if(!state.selected)return;
      state.selected[field]=convert(event.target.type==="checkbox"?event.target.checked:event.target.value);
      if(field==="kind"&&state.selected.kind==="unit"&&!(state.selected.health>0))
        state.selected.health=100;
      if(field==="kind"||field==="team"){renderItem(state.selected);selectItem(state.selected);}
      message(state.selected.name+" · propriété « "+field+" » modifiée");
    });
  scene.onPointerObservable.add(pointer=>{
    if(pointer.type===B.PointerEventTypes.POINTERPICK)clickWorld();
  });
  function fit(){
    WCArena.fitCamera(camera,engine,B,player.position,
      window.matchMedia("(max-width:520px)").matches);
    camera.lowerRadiusLimit=9;
    camera.upperRadiusLimit=27;
    camera.radius=window.innerWidth<820?15:17;
  }
  fit();
  window.addEventListener("resize",()=>{engine.resize();fit();});
  resetDemo();loadAvatar();
  engine.runRenderLoop(()=>{
    const dt=Math.min(.1,engine.getDeltaTime()/1000);
    WCArena.refreshCameraScale(camera,engine,6.2);
    if(!state.paused){
      state.acc+=dt;
      while(state.acc>=.1){tick();state.acc-=.1;}
      renderPose(state.acc/.1);
    }else renderPose(1);
    scene.render();
  });
})();

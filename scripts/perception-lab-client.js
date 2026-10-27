/* WarConquer Perception Lab: editable world -> bounded perception -> motion intent.
 * The Babylon model and animation library are optional; navigation never depends on them.
 */
(() => {
  "use strict";
  const $=id=>document.getElementById(id);
  const B=window.BABYLON;
  if(!B||!window.WCArena||!window.WCPerception||!window.WCResources){
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
    state.brain=new Brain({id:"scout",team:"blue",x:0,z:0,
      visionRange:Number($("visionRange").value),memoryTtlMs:20000});
    state.clock=0;state.order={type:"hold"};state.decision=null;
    state.inventory=WCResources.inventory();state.events=[];state.lastStatus=null;
    state.actionSerial++;state.actionRunning=false;
    for(const clip of state.animation.groups||[])clip.stop();
    state.currentClip=null;motion("idle");
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
      blocking:o.blocking,opaque:o.opaque,radius:o.radius,threat:o.threat
    }))};
  }
  function drawPath(result){
    if(routeMesh){routeMesh.dispose();routeMesh=null;}
    const path=[{x:player.position.x,z:player.position.z},...(result.path||[])];
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
      attack:/(^|[_ -])(attack|chop|strike|swing)([_ -]|$)/i,
      collect:/(^|[_ -])(pick.?up|pickup|collect|gather)([_ -]|$)/i
    };
    return groups.find(g=>patterns[name].test(g.name))||null;
  }
  function motion(name){
    if(state.actionRunning)return;
    const clip=state.animation[name]||state.animation.idle||null;
    if(clip===state.currentClip)return;
    state.currentClip?.stop();
    state.currentClip=clip;
    if(clip)clip.start(true,1,clip.from,clip.to);
    $("animationState").textContent=clip?.name||"Aucun clip";
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
        actor:{x:player.position.x,z:player.position.z},reach
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
        $("animationState").textContent="Attaque indisponible · clip manquant";
        state.order={type:"hold"};
      }
      return;
    }
    const serial=++state.actionSerial;
    state.actionRunning=true;
    state.currentClip?.stop();state.currentClip=null;
    group.stop();group.start(false,1,group.from,group.to);
    $("animationState").textContent=group.name;
    group.onAnimationGroupEndObservable.addOnce(()=>{
      if(serial!==state.actionSerial)return;
      state.actionRunning=false;
      motion("idle");
    });
  }
  function tick(){
    state.clock+=100;
    const world=makeWorld();
    state.brain.speed=state.order.type==="flee"?4.6:2.5;
    state.brain.setPose({x:player.position.x,z:player.position.z});
    const decision=state.brain.step(world,state.order,100,state.clock);
    state.decision=decision;
    const attempted=decision.move;
    const wantsMove=Math.hypot(attempted.dx,attempted.dz)>.0001;
    let moved=false;
    if(wantsMove&&!state.actionRunning){
      const nx=player.position.x+attempted.dx,nz=player.position.z+attempted.dz;
      const next=WCPerception.cell(world,nx,nz);
      const accepted=next.x>=0&&next.z>=0&&next.x<32&&next.z<32&&
        world.grid[next.z][next.x]!=="#";
      state.brain.reportMoveResult({accepted,attempted,blockedCell:accepted?null:next,nowMs:state.clock});
      if(accepted){
        moved=true;player.position.x=nx;player.position.z=nz;
        player.rotation.y=Math.atan2(attempted.dx,attempted.dz);
        state.brain.heading=Math.atan2(attempted.dz,attempted.dx);
      }else{
        decision.status=state.brain.stallCount>=3?"stuck":"replanning";
        decision.reason="collision";
        decision.move={dx:0,dz:0};
      }
    }
    if(decision.action)act(decision.action);
    else if(moved)motion(decision.status==="fleeing"?"run":"walk");
    else motion("idle");
    if(decision.status==="stuck"&&state.lastStatus!=="stuck")
      recordEvent("Chemin bloqué après plusieurs essais : un nouvel ordre est nécessaire.");
    state.lastStatus=decision.status;
    sight.position.x=player.position.x;sight.position.z=player.position.z;
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
  async function loadAvatar(){
    try{
      const res=await fetch("api/character-lab.json");
      if(!res.ok)throw Error("catalogue absent");
      const catalog=await res.json();
      const models=(catalog.characters||[]).flatMap(c=>c.models||[])
        .filter(m=>m.kind==="playable").sort((a,b)=>b.priority-a.priority);
      if(!models.length)throw Error("aucun GLB jouable");
      const url=models[0].url.replace(/^\/assets\//,"assets/");
      const imported=await B.SceneLoader.ImportMeshAsync(null,"",url,scene);
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
            const b=mesh.getBoundingInfo().boundingBox;
            min.minimizeInPlace(b.minimumWorld);max.maximizeInPlace(b.maximumWorld);
          }
          return {min,size:max.subtract(min)};
        }
        let bb=bounds();
        if(bb.size.z>Math.max(.0001,bb.size.y)*1.8&&bb.size.y<Math.max(bb.size.x,bb.size.z)*.48)
          content.rotation.x=-Math.PI/2;
        bb=bounds();
        const scale=range(1.9/Math.max(.00001,bb.size.y),.01,500);
        content.scaling.setAll(scale);
        content.position.y=-bb.min.y*scale;
      }
      placeholder.setEnabled(false);nose.setEnabled(false);
      state.animation.groups=imported.animationGroups||[];
      for(const group of state.animation.groups){
        group.stop();
        for(const entry of group.targetedAnimations||[]){
          entry.animation.enableBlending=true;
          entry.animation.blendingSpeed=.15;
        }
      }
      for(const name of ["idle","walk","run","attack","collect"])
        state.animation[name]=groupFor(name);
      state.loadedModel=true;
      $("engineBadge").textContent="GLB réel · "+state.animation.groups.length+" clips";
      motion("idle");
      message("Personnage 3D chargé. Marche/course/attaque selon les clips détectés.");
    }catch(err){
      state.loadedModel=false;
      $("engineBadge").textContent="Avatar de secours · 3D";
      $("animationState").textContent="GLB non chargé";
      message("Arène active avec avatar de repérage. Le GLB réel nécessite le catalogue du serveur ou de Pages : "+err.message);
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
  });
  $("singleStep").addEventListener("click",()=>{state.paused=true;$("playPause").textContent="Reprendre";tick();});
  $("resetDemo").addEventListener("click",resetDemo);
  $("visionRange").addEventListener("input",e=>{state.brain.range=Number(e.target.value);updateHud();});
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
    threatLevel:["threat",v=>range(Number(v)||0,0,1)],
    blocking:["blocking",v=>!!v],opaque:["opaque",v=>!!v]
  };
  for(const [id,[field,convert]]of Object.entries(controls))
    $(id).addEventListener("change",event=>{
      if(!state.selected)return;
      state.selected[field]=convert(event.target.type==="checkbox"?event.target.checked:event.target.value);
      if(field==="kind"||field==="team")renderItem(state.selected);
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
    }
    scene.render();
  });
})();

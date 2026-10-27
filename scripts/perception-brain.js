/* WarConquer Perception Lab brain v0.1: deterministic, dependency-free, no API calls.
 * x/z are world metres; grid cells are 1 metre; heading 0 faces +x, PI/2 faces +z.
 * The brain is only allowed to PLAN against its observed cells, never unseen terrain.
 */
(function(root,factory) {
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  else root.WCPerception=api;
})(typeof globalThis==="object"?globalThis:this,function() {
  "use strict";
  const TAU=2*Math.PI;
  const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
  const dist=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z);
  const key=(x,z)=>x+","+z;
  const number=n=>typeof n==="number"&&Number.isFinite(n);
  function cell(world,x,z) {
    return {x:Math.floor(x-(world.originX||0)),z:Math.floor(z-(world.originZ||0))};
  }
  function center(world,c) {
    return {x:(world.originX||0)+c.x+.5,z:(world.originZ||0)+c.z+.5};
  }
  function inside(world,c) {
    return c.x>=0&&c.z>=0&&c.x<world.grid[0].length&&c.z<world.grid.length;
  }
  function wall(world,c) {
    return !inside(world,c)||world.grid[c.z][c.x]==="#";
  }
  function opaqueWall(world,c) {
    return !inside(world,c)||(world.occlusion||world.grid)[c.z][c.x]==="#";
  }
  function lineOfSight(world,a,b,showEndWall) {
    // Integer Bresenham: only the wall at the endpoint itself may be seen.
    const from=cell(world,a.x,a.z),to=cell(world,b.x,b.z);
    let x=from.x,z=from.z;
    const dx=Math.abs(to.x-x),dz=Math.abs(to.z-z);
    const sx=x<to.x?1:-1,sz=z<to.z?1:-1;
    let err=dx-dz;
    while(true) {
      if((x!==from.x||z!==from.z)&&opaqueWall(world,{x,z}))
        return showEndWall&&x===to.x&&z===to.z;
      if(x===to.x&&z===to.z)return true;
      const twice=2*err;
      if(twice>-dz){err-=dz;x+=sx;}
      if(twice<dx){err+=dx;z+=sz;}
    }
  }
  class Heap {
    constructor(){this.items=[];}
    push(v) {
      const a=this.items;let i=a.length;a.push(v);
      while(i>0){const p=(i-1)>>1;if(a[p].score<=v.score)break;a[i]=a[p];i=p;}
      a[i]=v;
    }
    pop() {
      const a=this.items;const top=a[0],v=a.pop();
      if(a.length){let i=0;while(i*2+1<a.length){let c=i*2+1;
        if(c+1<a.length&&a[c+1].score<a[c].score)c++;
        if(a[c].score>=v.score)break;a[i]=a[c];i=c;}
        a[i]=v;
      }
      return top;
    }
    get size(){return this.items.length;}
  }
  class Brain {
    constructor(options={}) {
      if(!options.id)throw new Error("Brain requires a stable unit id");
      this.id=String(options.id);
      this.team=options.team||"blue";
      this.x=options.x??.5;this.z=options.z??.5;
      this.heading=options.heading??0;
      this.speed=options.speed??2.5;
      this.range=options.visionRange??7;
      this.fov=options.fov??TAU;
      this.memoryTtlMs=options.memoryTtlMs??15000;
      this.maxCells=options.maxCells??1024;
      this.maxEntities=options.maxEntities??80;
      this.bravery=options.bravery??.5;
      this.fear=0;this.fleeing=false;
      this.cells=new Map();this.entities=new Map();this.visible=[];
      this.route=null;this.relativeAnchor=null;this.exploreTarget=null;
      this.fleeTarget=null;this.lastTick=0;
    }
    setPose({x,z,heading}) {
      if(number(x))this.x=x;
      if(number(z))this.z=z;
      if(number(heading))this.heading=heading;
    }
    facing(p) {
      const angle=Math.atan2(p.z-this.z,p.x-this.x);
      const delta=Math.atan2(Math.sin(angle-this.heading),Math.cos(angle-this.heading));
      return Math.abs(delta)<=this.fov/2+1e-9;
    }
    canSee(world,p,endpointWall=false) {
      return dist(this,p)<=this.range+1e-9&&this.facing(p)&&
        lineOfSight(world,{x:this.x,z:this.z},p,endpointWall);
    }
    remember(map,id,value,limit) {
      if(map.has(id))map.delete(id);
      map.set(id,value);
      while(map.size>limit)map.delete(map.keys().next().value);
    }
    perceive(world,nowMs) {
      if(!world||!Array.isArray(world.grid)||!world.grid.length)
        throw new Error("World requires a nonempty grid");
      const origin=cell(world,this.x,this.z),extent=Math.ceil(this.range)+1;
      for(let z=Math.max(0,origin.z-extent);z<=Math.min(world.grid.length-1,origin.z+extent);z++){
        for(let x=Math.max(0,origin.x-extent);x<=Math.min(world.grid[0].length-1,origin.x+extent);x++){
          const p=center(world,{x,z});
          if(!this.canSee(world,p,true))continue;
          this.remember(this.cells,key(x,z),{x,z,blocked:wall(world,{x,z}),seenAt:nowMs},this.maxCells);
        }
      }
      this.visible=[];
      for(const obj of world.objects||[]) {
        if(obj.id===this.id||!number(obj.x)||!number(obj.z))continue;
        if(!this.canSee(world,obj))continue;
        const kind=obj.kind||"object";
        const record={id:String(obj.id),kind,team:obj.team||null,
          role:kind==="unit"?(obj.team===this.team?"ally":"enemy"):kind,
          x:obj.x,z:obj.z,blocking:!!obj.blocking,opaque:!!obj.opaque,
          radius:obj.radius||.4,threat:obj.threat??1,seenAt:nowMs};
        this.visible.push(record);
        this.remember(this.entities,record.id,record,this.maxEntities);
      }
      for(const [id,entity]of this.entities)
        if(nowMs-entity.seenAt>this.memoryTtlMs)this.entities.delete(id);
      return this.visible.slice();
    }
    knownBlocked(world,c,nowMs) {
      if(!inside(world,c))return true;
      if(this.cells.get(key(c.x,c.z))?.blocked)return true;
      for(const entity of this.entities.values()) {
        if(!entity.blocking||entity.id===this.id||nowMs-entity.seenAt>1500)continue;
        if(dist(center(world,c),entity)<=Math.max(.45,entity.radius))return true;
      }
      return false;
    }
    path(world,goal,nowMs) {
      const start=cell(world,this.x,this.z),end=cell(world,goal.x,goal.z);
      if(!inside(world,start)||!inside(world,end)||this.knownBlocked(world,end,nowMs))return null;
      const open=new Heap(),g=new Map(),parent=new Map();
      const startKey=key(start.x,start.z),endKey=key(end.x,end.z);
      const heuristic=c=>Math.abs(c.x-end.x)+Math.abs(c.z-end.z);
      g.set(startKey,0);open.push({c:start,score:heuristic(start),cost:0});
      let expanded=0;
      while(open.size&&expanded++<2500) {
        const current=open.pop(),c=current.c,k=key(c.x,c.z);
        if(current.cost!==g.get(k))continue;
        if(k===endKey){
          const result=[c];let walk=k;
          while(walk!==startKey) {
            walk=parent.get(walk);
            if(!walk)return null;
            const [x,z]=walk.split(",").map(Number);result.unshift({x,z});
          }
          return result;
        }
        for(const [dx,dz] of [[1,0],[-1,0],[0,1],[0,-1]]) {
          const n={x:c.x+dx,z:c.z+dz},nk=key(n.x,n.z);
          if(this.knownBlocked(world,n,nowMs))continue;
          const cost=current.cost+(this.cells.has(nk)?1:2.5);
          if(cost>=(g.get(nk)??Infinity))continue;
          g.set(nk,cost);parent.set(nk,k);
          open.push({c:n,cost,score:cost+heuristic(n)});
        }
      }
      return null;
    }
    chooseEntity(filter) {
      return [...this.entities.values()].filter(filter).sort((a,b)=>
        dist(this,a)-dist(this,b)||a.id.localeCompare(b.id))[0]||null;
    }
    relative(order) {
      const signature=JSON.stringify(order);
      if(!this.relativeAnchor||this.relativeAnchor.signature!==signature){
        this.relativeAnchor={signature,x:this.x,z:this.z,heading:this.heading};
      }
      const a=this.relativeAnchor,angle=a.heading+
        ({forward:0,back:Math.PI,left:Math.PI/2,right:-Math.PI/2}[order.direction]??0);
      const d=clamp(Number(order.distance)||2,0,32);
      return {x:a.x+Math.cos(angle)*d,z:a.z+Math.sin(angle)*d};
    }
    frontier(world) {
      const found=[];
      for(const c of this.cells.values()) {
        if(c.blocked)continue;
        for(const [dx,dz]of[[1,0],[-1,0],[0,1],[0,-1]]){
          const n={x:c.x+dx,z:c.z+dz};
          if(inside(world,n)&&!this.cells.has(key(n.x,n.z)))
            found.push({goal:center(world,n),distance:dist(this,center(world,n))});
        }
      }
      found.sort((a,b)=>a.distance-b.distance);
      return found.slice(0,15).find(p=>this.path(world,p.goal,this.lastTick))?.goal||null;
    }
    escape(world,threats,nowMs) {
      if(!threats.length)return null;
      if(this.fleeTarget&&dist(this,this.fleeTarget)>.45&&
          this.path(world,this.fleeTarget,nowMs))return this.fleeTarget;
      let choice=null,best=-Infinity;
      const here=cell(world,this.x,this.z);
      for(let dz=-7;dz<=7;dz++)for(let dx=-7;dx<=7;dx++){
        const c={x:here.x+dx,z:here.z+dz};
        if(this.knownBlocked(world,c,nowMs)||!this.cells.has(key(c.x,c.z)))continue;
        const p=center(world,c),route=this.path(world,p,nowMs);
        if(!route)continue;
        const safety=Math.min(...threats.map(t=>dist(p,t)));
        const score=safety-.12*route.length;
        if(score>best){best=score;choice=p;}
      }
      this.fleeTarget=choice;
      return choice;
    }
    step(world,order={type:"hold"},dtMs=100,nowMs=0) {
      this.lastTick=nowMs;
      const seen=this.perceive(world,nowMs),dt=clamp(dtMs,0,1000)/1000;
      const threats=seen.filter(e=>e.role==="enemy");
      const pressure=threats.reduce((n,e)=>n+Math.max(0,1-dist(this,e)/this.range)*(e.threat??1),0);
      this.fear=clamp(this.fear+dt*(pressure*(1.35-this.bravery)-.18),0,1);
      if(this.fear>=.65)this.fleeing=true;
      if(this.fear<=.25)this.fleeing=false;
      const cmd=order||{type:"hold"};
      if(cmd.type!=="relative")this.relativeAnchor=null;
      const response={id:this.id,status:"holding",action:null,mode:this.fleeing?"fear":"manual",
        fear:this.fear,visible:seen.map(e=>e.id),goal:null,
        move:{dx:0,dz:0},path:[],memory:{cells:this.cells.size,entities:this.entities.size}};
      let target=null,arrival=.25;
      if((this.fleeing||cmd.type==="flee")&&threats.length){
        target=this.escape(world,threats,nowMs);
        response.status="fleeing";arrival=.35;
      }else{
        this.fleeTarget=null;
        switch(cmd.type){
          case "goto":
            if(number(cmd.x)&&number(cmd.z))target={x:cmd.x,z:cmd.z};
            break;
          case "relative":
            target=this.relative(cmd);
            break;
          case "approach":
          case "attack":
          case "collect": {
            const entity=this.entities.get(String(cmd.entityId));
            if(entity){
              arrival=Math.max(.35,Number(cmd.distance)||1.2);
              if(cmd.type==="attack"&&entity.role!=="enemy")break;
              if(cmd.type==="collect"&&entity.kind!=="resource")break;
              const dx=this.x-entity.x,dz=this.z-entity.z;
              const length=Math.max(.0001,Math.hypot(dx,dz));
              target={x:entity.x+dx/length*arrival*.9,
                z:entity.z+dz/length*arrival*.9};
            }
            break;
          }
          case "find": {
            const found=this.chooseEntity(e=>e.kind===cmd.kind&&
              (!cmd.team||e.team===cmd.team));
            if(found){target={x:found.x,z:found.z};arrival=Math.max(.4,Number(cmd.distance)||1);}
            else {
              if(!this.exploreTarget||this.cells.has(key(
                cell(world,this.exploreTarget.x,this.exploreTarget.z).x,
                cell(world,this.exploreTarget.x,this.exploreTarget.z).z)))
                this.exploreTarget=this.frontier(world);
              target=this.exploreTarget;
              response.status=target?"searching":"not_found";
            }
            break;
          }
          case "flee":response.status="no_threat";break;
          case "hold":break;
          default:response.status="invalid_order";
        }
      }
      if(!target)return response;
      response.goal=target;
      if(dist(this,target)<=arrival){
        response.status=response.status==="searching"?"searching":"arrived";
        if(cmd.type==="attack"||cmd.type==="collect") {
          if(seen.some(e=>e.id===String(cmd.entityId)))response.action=cmd.type;
          else response.status="target_not_visible";
        }
        return response;
      }
      const end=cell(world,target.x,target.z),routeKey=key(end.x,end.z);
      if(!this.route||this.route.key!==routeKey||
          this.route.cells.some(c=>this.knownBlocked(world,c,nowMs))) {
        const cells=this.path(world,target,nowMs);
        this.route=cells?{key:routeKey,cells}:null;
      }
      if(!this.route){response.status="blocked";return response;}
      while(this.route.cells.length&&
        (this.route.cells[0].x===cell(world,this.x,this.z).x&&
         this.route.cells[0].z===cell(world,this.x,this.z).z))
        this.route.cells.shift();
      const waypoint=this.route.cells.length?center(world,this.route.cells[0]):target;
      const delta=dist(this,waypoint);
      if(delta<1e-8){response.status="arrived";return response;}
      const step=Math.min(delta,dt*this.speed);
      response.move={dx:(waypoint.x-this.x)/delta*step,dz:(waypoint.z-this.z)/delta*step};
      response.path=this.route.cells.map(c=>center(world,c));
      if(response.status!=="searching"&&response.status!=="fleeing")response.status="moving";
      return response;
    }
    snapshot() {
      return {id:this.id,team:this.team,pose:{x:this.x,z:this.z,heading:this.heading},
        emotions:{fear:this.fear,fleeing:this.fleeing},
        visible:this.visible.map(e=>({...e})),
        memory:{cells:[...this.cells.values()].map(c=>({...c})),
          entities:[...this.entities.values()].map(e=>({...e}))}};
    }
  }
  return {Brain,cell,center,lineOfSight};
});
